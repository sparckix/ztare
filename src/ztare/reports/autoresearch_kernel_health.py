"""Aggregate health surface for the autoresearch/RD workbench.

This report reuses the narrow validators and read-only audits. It is meant as
the first operator page: run it to see whether the kernel is ready, needs review,
or has a blocking integrity problem before launching more autoresearch.
"""
from __future__ import annotations

import argparse
import json
import shlex
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ztare.workspace.evidence_gaps import LOCAL_VERIFICATION_RECOVERY_KIND


REPO = Path(__file__).resolve().parents[3]

STATUS_RANK = {"ok": 0, "attention": 1, "needs_attention": 2}
CONTROL_OUTCOME_MIN_EVENTS = 10
CONTROL_OUTCOME_MIN_SUCCESS_RATE = 0.40
CONTROL_OUTCOME_MAX_NO_FOLLOWUP_RATE = 0.40
PACKET_ADMISSION_ATTENTION_STATUSES = {
    "missing_current_packet",
    "stale_current_packet",
    "unverified_missing_packet_path",
}


def _make_command(target: str, **vars_: Any) -> str:
    parts = ["make", target]
    for key, value in vars_.items():
        if value is None or value == "":
            continue
        parts.append(f"{key}={shlex.quote(str(value))}")
    return " ".join(parts)


def _dispatch_validate(repo: Path) -> dict[str, Any]:
    from scripts.public.validators.validate_autoresearch_llm_dispatch import validate

    return validate(repo=repo)


def _catalog_health(repo: Path):
    from ztare.research_director.primitive_catalog_taxonomy import catalog_health

    return catalog_health(
        catalog_path=repo / "analytics" / "public" / "index" / "architecture_index.jsonl",
        atlas_path=repo / "analytics" / "public" / "index" / "primitive_atlas_embeddings.json",
        rendered_index_path=repo / "src" / "ztare" / "architecture_index" / "INDEX.md",
    )


def _mechanism_consequences(
    *,
    repo: Path,
    project: str | None,
    workspace: str | Path | None,
) -> dict[str, Any]:
    from ztare.reports.mechanism_consequence_audit import audit_mechanism_consequences

    return audit_mechanism_consequences(repo=repo, project=project, workspace=workspace)


def _evidence_trace() -> dict[str, Any]:
    from ztare.reports.evidence_trace_health import build_evidence_trace_fixture

    return build_evidence_trace_fixture()


def _graph_capability(repo: Path) -> dict[str, Any]:
    from ztare.reports.graph_capability_audit import build_graph_capability_audit

    return build_graph_capability_audit(repo=repo)


def _forecast_capability(repo: Path) -> dict[str, Any]:
    from ztare.reports.forecast_capability_audit import build_forecast_capability_audit

    return build_forecast_capability_audit(repo=repo)


def _rubric_modes(*, repo: Path, rubric: str | Path | None) -> dict[str, Any]:
    from ztare.reports.rubric_mode_corpus_audit import audit_rubric_mode_corpus

    return audit_rubric_mode_corpus(repo=repo, rubric=rubric)


def _hill_climb(
    *,
    repo: Path,
    project: str | None,
    stagnation_threshold: int,
) -> dict[str, Any]:
    from ztare.reports.hill_climb_behavior_audit import build_hill_climb_behavior_audit

    return build_hill_climb_behavior_audit(
        repo=repo,
        project=project,
        stagnation_threshold=stagnation_threshold,
        limit=0,
    )


def _subscription_outcomes(*, repo: Path, project: str | None) -> dict[str, Any]:
    from ztare.reports.subscription_outcome_audit import audit_subscription_outcomes

    return audit_subscription_outcomes(repo=repo, project=project)


def _operations_intelligence(repo: Path) -> dict[str, Any]:
    from ztare.reports.operations_intelligence import build

    return build(repo=repo)


def _fixtures() -> dict[str, Any]:
    from scripts.public.validators.validate_inloop_mechanism_fixtures import run_fixtures

    return run_fixtures()


def _primitive_parent_utility() -> dict[str, Any]:
    from ztare.research_director.primitive_parent_utility import build_parent_utility_audit

    return asdict(build_parent_utility_audit())


def _primitive_miss_queue(repo: Path) -> dict[str, Any]:
    from ztare.research_director.primitive_amnesia import miss_queue_status

    return miss_queue_status(
        repo / "analytics" / "public" / "queries" / "primitive_amnesia_miss_queue.jsonl"
    )


def _source_preflight(*, repo: Path, project: str) -> dict[str, Any]:
    from ztare.scaffold.source_check import check_source_project

    return check_source_project(project=project, repo=repo)


def _project_trace(
    *,
    repo: Path,
    project: str,
    rubric: str | Path | None,
    packet: str | Path | None = None,
) -> dict[str, Any]:
    from ztare.reports.autoresearch_trace import build_autoresearch_trace

    return build_autoresearch_trace(
        project=project,
        rubric=str(rubric) if rubric else None,
        packet=str(packet) if packet else None,
        repo=repo,
        full_health=False,
    )


def _component(
    *,
    component: str,
    status: str,
    summary: dict[str, Any],
    action: str,
    next_command: str,
) -> dict[str, Any]:
    return {
        "component": component,
        "status": status,
        "summary": summary,
        "action": action,
        "next_command": next_command,
    }


def _overall_status(components: list[dict[str, Any]]) -> str:
    rank = max((STATUS_RANK.get(str(row["status"]), 2) for row in components), default=0)
    for status, value in STATUS_RANK.items():
        if value == rank:
            return status
    return "needs_attention"


def _packet_admission_drift_issues(
    *,
    latest_run_project_packet: Any,
    latest_preflight_only: Any,
    latest_run_id: Any = None,
) -> list[dict[str, Any]]:
    packets = _latest_admission_packets(
        latest_run_project_packet=latest_run_project_packet,
        latest_preflight_only=latest_preflight_only,
        latest_run_id=latest_run_id,
    )

    issues: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for source, packet in packets:
        key = (
            str(packet.get("packet_path") or ""),
            str(packet.get("packet_sha256") or ""),
            str(packet.get("kernel_entry_sha256") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        status = str(packet.get("packet_hash_status") or "").strip()
        if status not in PACKET_ADMISSION_ATTENTION_STATUSES:
            continue
        issues.append(
            {
                "source": source,
                "packet_path": packet.get("packet_path"),
                "packet_hash_status": status,
                "packet_hash_verified": packet.get("packet_hash_verified"),
            }
        )
    return issues


def _latest_admission_packets(
    *,
    latest_run_project_packet: Any,
    latest_preflight_only: Any,
    latest_run_id: Any = None,
) -> list[tuple[str, dict[str, Any]]]:
    preflight_packet = None
    latest_preflight_run_id = None
    if isinstance(latest_preflight_only, dict):
        latest_preflight_run_id = latest_preflight_only.get("run_id")
        candidate = latest_preflight_only.get("packet")
        if isinstance(candidate, dict) and candidate:
            preflight_packet = candidate
    if isinstance(latest_run_project_packet, dict) and latest_run_project_packet:
        latest_run_id = latest_run_id or latest_run_project_packet.get("run_id")

    if latest_preflight_run_id is not None and latest_run_id is not None:
        if latest_preflight_run_id >= latest_run_id:
            return (
                [("latest_preflight_only", preflight_packet)]
                if isinstance(preflight_packet, dict)
                else []
            )
        return (
            [("latest_run", latest_run_project_packet)]
            if isinstance(latest_run_project_packet, dict)
            else []
        )

    packets: list[tuple[str, dict[str, Any]]] = []
    if isinstance(preflight_packet, dict):
        packets.append(("latest_preflight_only", preflight_packet))
    if isinstance(latest_run_project_packet, dict) and latest_run_project_packet:
        packets.append(("latest_run", latest_run_project_packet))
    return packets


def _kernel_entry_receipt_change_issues(
    *,
    latest_run_project_packet: Any,
    latest_preflight_only: Any,
    latest_run_id: Any = None,
) -> list[dict[str, Any]]:
    packets = _latest_admission_packets(
        latest_run_project_packet=latest_run_project_packet,
        latest_preflight_only=latest_preflight_only,
        latest_run_id=latest_run_id,
    )

    issues: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for source, packet in packets:
        key = (
            str(packet.get("packet_path") or ""),
            str(packet.get("packet_sha256") or ""),
            str(packet.get("kernel_entry_sha256") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        status = str(packet.get("kernel_entry_hash_status") or "").strip()
        if status != "current_kernel_entry_changed":
            continue
        issues.append(
            {
                "source": source,
                "packet_path": packet.get("packet_path"),
                "kernel_entry_hash_status": status,
                "kernel_entry_hash_verified": packet.get("kernel_entry_hash_verified"),
            }
        )
    return issues


def _evidence_readiness_summary(trace_surfaces: dict[str, Any]) -> dict[str, Any]:
    source_index = (
        trace_surfaces.get("source_index_freshness")
        if isinstance(trace_surfaces.get("source_index_freshness"), dict)
        else {}
    )
    compile_freshness = (
        trace_surfaces.get("evidence_compile_freshness")
        if isinstance(trace_surfaces.get("evidence_compile_freshness"), dict)
        else {}
    )
    output_binding = (
        trace_surfaces.get("evidence_output_binding")
        if isinstance(trace_surfaces.get("evidence_output_binding"), dict)
        else {}
    )
    replay = (
        trace_surfaces.get("evidence_replay")
        if isinstance(trace_surfaces.get("evidence_replay"), dict)
        else {}
    )
    replay_required = bool(replay.get("required"))
    raw_replay_status = str(replay.get("status") or "")
    replay_status = (
        raw_replay_status
        if replay_required or raw_replay_status not in {"missing_manifest", ""}
        else "not_required"
    )
    replay_ok = bool(replay.get("ok")) if replay_required else True
    status = "fresh"
    if str(source_index.get("status") or "") not in {"", "fresh"}:
        status = "blocked"
    if str(compile_freshness.get("status") or "") not in {"", "fresh"}:
        status = "blocked"
    if str(output_binding.get("status") or "") not in {"", "fresh"}:
        status = "blocked"
    if replay_required and not replay_ok:
        status = "blocked"
    return {
        "status": status,
        "source_index_status": source_index.get("status"),
        "compile_provenance_status": compile_freshness.get("status"),
        "output_binding_status": output_binding.get("status"),
        "output_stale_artifacts": list(output_binding.get("stale_artifacts") or []),
        "replay_required": replay_required,
        "replay_status": replay_status,
        "raw_replay_status": raw_replay_status,
        "replay_ok": replay_ok,
    }


def build_autoresearch_kernel_health(
    *,
    repo: Path = REPO,
    project: str | None = None,
    workspace: str | Path | None = None,
    rubric: str | Path | None = None,
    packet: str | Path | None = None,
    stagnation_threshold: int = 2,
) -> dict[str, Any]:
    repo = repo.resolve()
    components: list[dict[str, Any]] = []

    dispatch = _dispatch_validate(repo)
    dispatch_summary = dict(dispatch.get("summary") or {})
    direct_allowed = list(dispatch.get("direct_allowed") or [])
    dispatch_findings = int(dispatch_summary.get("findings") or 0)
    components.append(
        _component(
            component="dispatch",
            status="ok" if dispatch_findings == 0 else "needs_attention",
            summary={
                "findings": dispatch_findings,
                "dispatch_sites": dispatch_summary.get("dispatch_sites", 0),
                "wrapped_sites": dispatch_summary.get("wrapped_sites", 0),
                "direct_allowed_sites": dispatch_summary.get("direct_allowed_sites", 0),
                "direct_allowed": direct_allowed[:8],
            },
            action="fix dispatch findings before relying on subscription workers"
            if dispatch_findings
            else "no action",
            next_command=_make_command("autoresearch-dispatch-validate", JSON=1),
        )
    )

    catalog = _catalog_health(repo)
    parent_utility = _primitive_parent_utility()
    miss_queue = _primitive_miss_queue(repo)
    open_misses = int(miss_queue.get("open_count") or 0)
    malformed_misses = int(miss_queue.get("malformed_count") or 0)
    catalog_needs_attention = (
        not bool(catalog.ok)
        or not bool(parent_utility.get("ok"))
        or malformed_misses > 0
    )
    catalog_status = (
        "needs_attention"
        if catalog_needs_attention
        else "attention" if open_misses else "ok"
    )
    components.append(
        _component(
            component="primitive_catalog",
            status=catalog_status,
            summary={
                "ok": bool(catalog.ok),
                "row_count": catalog.row_count,
                "warnings": list(catalog.warnings),
                "stale_outputs": list(catalog.stale_outputs),
                "parent_utility": {
                    "ok": parent_utility.get("ok"),
                    "case_count": parent_utility.get("case_count", 0),
                    "passed": parent_utility.get("passed", 0),
                    "catalog_rank_recall": parent_utility.get("catalog_rank_recall"),
                    "worker_rank_recall": parent_utility.get("worker_rank_recall"),
                    "child_recall": parent_utility.get("child_recall"),
                },
                "miss_queue": {
                    "path": miss_queue.get("path"),
                    "row_count": miss_queue.get("row_count", 0),
                    "open_count": open_misses,
                    "malformed_count": malformed_misses,
                    "status_counts": miss_queue.get("status_counts", {}),
                    "promotion_review_counts": miss_queue.get("promotion_review_counts", {}),
                    "latest_open": miss_queue.get("latest_open", []),
                },
            },
            action=(
                "repair malformed primitive-amnesia miss-queue rows"
                if malformed_misses
                else "refresh/repair the catalog, atlas, or parent-node utility before adding new primitive machinery"
                if not catalog.ok or not bool(parent_utility.get("ok"))
                else "review and close primitive-amnesia miss-queue rows"
                if open_misses
                else "no action"
            ),
            next_command=_make_command("primitive-parent-utility", JSON=1)
            if not bool(parent_utility.get("ok"))
            else _make_command("primitive-amnesia-eval", RECORD_MISSES=1)
            if open_misses or malformed_misses
            else _make_command("primitive-catalog-health", JSON=1),
        )
    )

    mechanism = _mechanism_consequences(repo=repo, project=project, workspace=workspace)
    mechanism_summary = dict(mechanism.get("summary") or {})
    evidence_counts = dict(mechanism_summary.get("evidence_status_counts") or {})
    unobserved = int(evidence_counts.get("unobserved_in_scope") or 0)
    not_triggered = int(evidence_counts.get("not_triggered") or 0)
    placeholder_only = int(mechanism_summary.get("placeholder_only_count") or 0)
    decorative = int(mechanism_summary.get("intrinsic_decorative_count") or 0)
    components.append(
        _component(
            component="mechanism_consequences",
            status="ok" if unobserved == 0 and placeholder_only == 0 and decorative == 0 else "needs_attention",
            summary={
                "mechanism_count": mechanism_summary.get("mechanism_count", 0),
                "evidence_status_counts": evidence_counts,
                "evidence_quality_counts": mechanism_summary.get("evidence_quality_counts", {}),
                "not_triggered_count": not_triggered,
                "intrinsic_decorative_count": decorative,
                "placeholder_only_count": placeholder_only,
            },
            action="inspect unobserved, placeholder-only, or decorative mechanisms in the consequence audit"
            if unobserved or placeholder_only or decorative
            else "no action",
            next_command=_make_command(
                "autoresearch-consequence-audit",
                PROJECT=project,
                WORKSPACE=workspace,
                JSON=1,
            ),
        )
    )

    fixture_report = _fixtures()
    fixture_passed = bool(fixture_report.get("passed"))
    components.append(
        _component(
            component="inloop_fixtures",
            status="ok" if fixture_passed else "needs_attention",
            summary={
                "passed": fixture_passed,
                "num_passed": fixture_report.get("num_passed", 0),
                "num_fixtures": fixture_report.get("num_fixtures", 0),
                "by_status": ((fixture_report.get("mechanism_status") or {}).get("by_status") or {}),
            },
            action="repair failing in-loop mechanism fixtures before launch"
            if not fixture_passed
            else "no action",
            next_command=_make_command("inloop-fixture-validate", JSON=1),
        )
    )

    evidence_trace = _evidence_trace()
    evidence_trace_ok = bool(evidence_trace.get("all_passed"))
    components.append(
        _component(
            component="evidence_trace",
            status="ok" if evidence_trace_ok else "needs_attention",
            summary={
                "passed": evidence_trace_ok,
                "num_passed": evidence_trace.get("num_passed", 0),
                "num_cases": evidence_trace.get("num_cases", 0),
                "trace": evidence_trace.get("trace", {}),
            },
            action=(
                "repair raw/evidence/constraint/briefing/projection trace chain"
                if not evidence_trace_ok
                else "no action"
            ),
            next_command=_make_command("autoresearch-evidence-trace", JSON=1),
        )
    )

    graph_capability = _graph_capability(repo)
    graph_summary = dict(graph_capability.get("summary") or {})
    graph_missing = int(graph_summary.get("missing_count") or 0)
    graph_verdict = dict(graph_capability.get("verdict") or {})
    components.append(
        _component(
            component="graph_capability",
            status="ok" if graph_missing == 0 else "needs_attention",
            summary={
                "row_count": graph_summary.get("row_count", 0),
                "present_count": graph_summary.get("present_count", 0),
                "missing_count": graph_missing,
                "status_counts": graph_summary.get("status_counts", {}),
                "ready_receipt_paths": graph_summary.get("ready_receipt_paths", []),
                "missing_rows": graph_summary.get("missing_rows", []),
                "strongest_supported_claim": graph_verdict.get(
                    "strongest_supported_claim"
                ),
                "release_boundary": graph_verdict.get("release_boundary"),
            },
            action=(
                "repair missing graph carrier or audit markers"
                if graph_missing
                else "no action"
            ),
            next_command=_make_command("graph-capability-audit", JSON=1),
        )
    )

    forecast_capability = _forecast_capability(repo)
    forecast_summary = dict(forecast_capability.get("summary") or {})
    forecast_missing = int(forecast_summary.get("missing_count") or 0)
    forecast_verdict = dict(forecast_capability.get("verdict") or {})
    components.append(
        _component(
            component="forecast_capability",
            status="ok" if forecast_missing == 0 else "needs_attention",
            summary={
                "row_count": forecast_summary.get("row_count", 0),
                "present_count": forecast_summary.get("present_count", 0),
                "missing_count": forecast_missing,
                "status_counts": forecast_summary.get("status_counts", {}),
                "ready_receipt_paths": forecast_summary.get("ready_receipt_paths", []),
                "missing_rows": forecast_summary.get("missing_rows", []),
                "strongest_supported_claim": forecast_verdict.get(
                    "strongest_supported_claim"
                ),
                "release_boundary": forecast_verdict.get("release_boundary"),
                "needs_before_stronger_claim": forecast_verdict.get(
                    "needs_before_stronger_claim"
                ),
            },
            action=(
                "repair missing forecast lifecycle or decision-use audit markers"
                if forecast_missing
                else "no action"
            ),
            next_command=_make_command("forecast-capability-audit", JSON=1),
        )
    )

    if project:
        try:
            source_preflight = _source_preflight(repo=repo, project=project)
        except Exception as exc:  # noqa: BLE001
            source_preflight = {
                "ok": False,
                "status": "unavailable",
                "blocking": [f"{type(exc).__name__}: {exc}"],
                "warnings": [],
                "source_count": 0,
                "source_evidence_count": 0,
                "untyped_source_count": 0,
                "raw_dir": None,
                "source_type_map": None,
            }
        source_blocking = list(source_preflight.get("blocking") or [])
        source_warnings = list(source_preflight.get("warnings") or [])
        source_next_steps = list(source_preflight.get("next_steps") or [])
        source_next_commands = list(source_preflight.get("next_commands") or [])
        source_ok = bool(source_preflight.get("ok")) and not source_blocking
        components.append(
            _component(
                component="source_preflight",
                status="ok" if source_ok else "needs_attention",
                summary={
                    "ok": source_ok,
                    "status": source_preflight.get("status"),
                    "source_count": source_preflight.get("source_count", 0),
                    "source_evidence_count": source_preflight.get("source_evidence_count", 0),
                    "untyped_source_count": source_preflight.get("untyped_source_count", 0),
                    "unsupported_file_count": source_preflight.get("unsupported_file_count", 0),
                    "empty_file_count": source_preflight.get("empty_file_count", 0),
                    "blocking": source_blocking,
                    "warnings": source_warnings,
                    "next_steps": source_next_steps,
                    "next_commands": source_next_commands,
                    "raw_dir": source_preflight.get("raw_dir"),
                    "source_type_map": source_preflight.get("source_type_map"),
                },
                action=(
                    "fix raw source typing before workspace update or evidence compilation"
                    if not source_ok
                    else "no action"
                ),
                next_command=(
                    f"ztare project source-check --project {shlex.quote(str(project))} --json"
                    if not source_ok
                    else _make_command("evidence-prepare", PROJECT=project, MODEL="gemini")
                ),
            )
        )
        try:
            project_trace = _project_trace(
                repo=repo,
                project=project,
                rubric=rubric,
                packet=packet,
            )
        except Exception as exc:  # noqa: BLE001
            project_trace = {
                "status": "partial_trace",
                "readiness": "trace_unavailable",
                "blocking_missing": ["project_trace_unavailable"],
                "history_missing": [],
                "kernel_entry": {
                    "status": "blocked",
                    "can_enter_kernel": False,
                    "blockers": [
                        {
                            "id": "project_trace_unavailable",
                            "recovery_channel": "project_trace",
                            "next_command": (
                                "ztare autoresearch trace --project "
                                f"{shlex.quote(str(project))}"
                                + (
                                    f" --rubric {shlex.quote(str(rubric))}"
                                    if rubric
                                    else ""
                                )
                                + " --json"
                            ),
                        }
                    ],
                },
                "graph_carriers": [],
                "graph_rd_actions": [],
                "prediction_summary": {
                    "available": False,
                    "status": "trace_unavailable",
                    "issues": [
                        {
                            "code": "project_trace_unavailable",
                            "message": f"{type(exc).__name__}: {exc}",
                        }
                    ],
                },
                "surfaces": {},
            }
        kernel_entry = dict(project_trace.get("kernel_entry") or {})
        trace_blockers = list(kernel_entry.get("blockers") or [])
        trace_ready = bool(kernel_entry.get("can_enter_kernel"))
        trace_surfaces = dict(project_trace.get("surfaces") or {})
        evidence_readiness = _evidence_readiness_summary(trace_surfaces)
        prediction_summary = dict(project_trace.get("prediction_summary") or {})
        recent_loop = (
            project_trace.get("recent_loop")
            if isinstance(project_trace.get("recent_loop"), dict)
            else {}
        )
        latest_run_project_packet = recent_loop.get("latest_run_project_packet")
        latest_preflight_only = recent_loop.get("latest_preflight_only")
        provider_failure_signatures = list(
            recent_loop.get("recent_provider_failure_signatures") or []
        )
        latest_provider_failure_signature = recent_loop.get(
            "latest_provider_failure_signature"
        )
        packet_admission_drift = _packet_admission_drift_issues(
            latest_run_project_packet=latest_run_project_packet,
            latest_preflight_only=latest_preflight_only,
            latest_run_id=recent_loop.get("latest_run_id"),
        )
        kernel_entry_receipt_changes = _kernel_entry_receipt_change_issues(
            latest_run_project_packet=latest_run_project_packet,
            latest_preflight_only=latest_preflight_only,
            latest_run_id=recent_loop.get("latest_run_id"),
        )
        trace_summary = {
            "status": project_trace.get("status"),
            "readiness": project_trace.get("readiness"),
            "kernel_entry_status": kernel_entry.get("status"),
            "can_enter_kernel": trace_ready,
            "blocking_missing": list(project_trace.get("blocking_missing") or []),
            "history_missing": list(project_trace.get("history_missing") or []),
            "blockers": trace_blockers,
            "graph_carrier_count": len(project_trace.get("graph_carriers") or []),
            "graph_rd_action_count": len(project_trace.get("graph_rd_actions") or []),
            "in_loop_focus_receipt_count": len(
                kernel_entry.get("in_loop_focus_receipts") or []
            ),
            "withheld_in_loop_focus_receipt_count": len(
                kernel_entry.get("withheld_in_loop_focus_receipts") or []
            ),
            "evidence_readiness": evidence_readiness,
            "source_index_freshness_status": evidence_readiness.get("source_index_status"),
            "evidence_compile_freshness_status": (
                evidence_readiness.get("compile_provenance_status")
            ),
            "evidence_output_binding_status": evidence_readiness.get(
                "output_binding_status"
            ),
            "evidence_output_stale_artifacts": evidence_readiness.get(
                "output_stale_artifacts"
            ),
            "prediction_status": prediction_summary.get("status"),
            "prediction_issue_codes": [
                str(issue.get("code"))
                for issue in prediction_summary.get("issues", [])
                if isinstance(issue, dict) and issue.get("code")
            ],
            "packet_admission_drift_count": len(packet_admission_drift),
            "packet_admission_drift": packet_admission_drift,
            "kernel_entry_receipt_change_count": len(kernel_entry_receipt_changes),
            "kernel_entry_receipt_changes": kernel_entry_receipt_changes,
            "provider_failure_signature_count": len(provider_failure_signatures),
            "recent_provider_failure_signatures": provider_failure_signatures,
            "latest_provider_failure_signature": (
                latest_provider_failure_signature
                if isinstance(latest_provider_failure_signature, dict)
                else None
            ),
        }
        current_project_intake_admission = recent_loop.get(
            "current_project_intake_admission"
        )
        has_current_project_intake_admission = (
            isinstance(current_project_intake_admission, dict)
            and bool(current_project_intake_admission)
        )
        if not has_current_project_intake_admission:
            if isinstance(latest_run_project_packet, dict) and latest_run_project_packet:
                trace_summary["latest_run_project_packet"] = latest_run_project_packet
            latest_run_project_intake = recent_loop.get("latest_run_project_intake")
            if isinstance(latest_run_project_intake, dict) and latest_run_project_intake:
                trace_summary["latest_run_project_intake"] = latest_run_project_intake
        if (
            has_current_project_intake_admission
        ):
            trace_summary["current_project_intake_admission"] = (
                current_project_intake_admission
            )
            trace_summary["admission_history"] = {
                "latest_run_available": bool(latest_run_project_packet),
                "latest_preflight_available": bool(latest_preflight_only),
                "current_source": current_project_intake_admission.get("source"),
                "current_run_id": current_project_intake_admission.get("run_id"),
                "details": "run full autoresearch trace for historical receipts",
            }
        elif isinstance(latest_preflight_only, dict) and latest_preflight_only:
            trace_summary["latest_preflight_only"] = latest_preflight_only
        if evidence_readiness.get("status") == "fresh":
            for component in components:
                if component.get("component") != "source_preflight":
                    continue
                summary = component.get("summary")
                if not isinstance(summary, dict):
                    break
                if component.get("status") != "ok" or summary.get("blocking"):
                    break
                summary["next_steps"] = []
                summary["next_commands"] = []
                component["next_command"] = (
                    "ztare autoresearch trace --project "
                    f"{shlex.quote(str(project))}"
                    + (
                        f" --rubric {shlex.quote(str(rubric))}"
                        if rubric
                        else ""
                    )
                    + (
                        f" --intake {shlex.quote(str(packet))}"
                        if packet
                        else ""
                    )
                    + " --json"
                )
                break
        project_trace_status = (
            "needs_attention"
            if not trace_ready
            else (
                "attention"
                if (
                    packet_admission_drift
                    or kernel_entry_receipt_changes
                    or provider_failure_signatures
                )
                else "ok"
            )
        )
        components.append(
            _component(
                component="project_trace",
                status=project_trace_status,
                summary=trace_summary,
                action=(
                    "resolve project trace blockers before run readiness"
                    if not trace_ready
                    else "inspect packet admission drift before reusing prior run evidence"
                    if packet_admission_drift
                    else "refresh run-readiness receipt before reusing prior admission evidence"
                    if kernel_entry_receipt_changes
                    else "inspect provider timeout/retry failure before treating loop failure as research signal"
                    if provider_failure_signatures
                    else "no action"
                ),
                next_command=(
                    "ztare autoresearch trace --project "
                    f"{shlex.quote(str(project))}"
                    + (
                        f" --rubric {shlex.quote(str(rubric))}"
                        if rubric
                        else ""
                    )
                    + (
                        f" --intake {shlex.quote(str(packet))}"
                        if packet
                        else ""
                    )
                    + " --json"
                ),
            )
        )

    rubric_report = _rubric_modes(repo=repo, rubric=rubric)
    rubric_summary = dict(rubric_report.get("summary") or {})
    rubric_attention = int(rubric_summary.get("attention_count") or 0)
    legacy_unset = dict(rubric_summary.get("legacy_unset") or {})
    components.append(
        _component(
            component="rubric_modes",
            status="attention" if rubric_attention else "ok",
            summary={
                "attention_count": rubric_attention,
                "status_counts": rubric_summary.get("status_counts", {}),
                "mode_counts": rubric_summary.get("mode_counts", {}),
                "legacy_unset_count": legacy_unset.get("count", 0),
                "legacy_unset_with_project_count": legacy_unset.get("with_project_count", 0),
            },
            action="repair Newton/Kepler rubric attention before serious runs"
            if rubric_attention
            else "no action",
            next_command=_make_command(
                "autoresearch-rubric-mode-audit",
                RUBRIC=rubric,
                LIMIT=20,
            ),
        )
    )

    hill = _hill_climb(repo=repo, project=project, stagnation_threshold=stagnation_threshold)
    hill_status_counts = dict(hill.get("status_counts") or {})
    post_control_diagnostic_counts = dict(hill.get("post_control_diagnostic_counts") or {})
    post_control_diagnostic_samples = list(
        hill.get("post_control_diagnostic_samples") or []
    )
    control_episode_recovery_counts = dict(
        hill.get("control_episode_recovery_counts") or {}
    )
    control_episode_recovery_unresolved_counts = dict(
        hill.get("control_episode_recovery_unresolved_counts") or {}
    )
    control_episode_recovery_resolution_counts = dict(
        hill.get("control_episode_recovery_resolution_counts") or {}
    )
    control_episode_recovery_admission_packet_counts = dict(
        hill.get("control_episode_recovery_admission_packet_counts") or {}
    )
    control_episode_recovery_queue = list(
        hill.get("control_episode_recovery_queue") or []
    )
    control_due = int(hill_status_counts.get("control_due_without_breadth_evidence") or 0)
    control_followup_policy = dict(hill.get("control_followup_policy_totals") or {})
    post_control = dict(hill.get("post_control_outcome_totals") or {})
    post_control_health = dict(hill.get("post_control_episode_totals") or post_control)
    active_control_events = int(post_control.get("active_control_event_count") or 0)
    post_control_windows = int(post_control.get("post_control_window_count") or 0)
    post_control_no_followup = int(post_control.get("post_control_no_followup_count") or 0)
    post_control_observed_no_success = int(
        post_control.get("post_control_observed_no_success_count") or 0
    )
    post_control_success = int(post_control.get("post_control_success_count") or 0)
    post_control_success_rate = post_control.get("post_control_success_rate")
    control_episode_count = int(
        post_control_health.get("control_episode_count")
        or post_control_health.get("active_control_event_count")
        or 0
    )
    post_control_episode_windows = int(
        post_control_health.get("post_control_episode_window_count")
        or post_control_health.get("post_control_window_count")
        or 0
    )
    post_control_episode_no_followup = int(
        post_control_health.get("post_control_episode_no_followup_count")
        or post_control_health.get("post_control_no_followup_count")
        or 0
    )
    post_control_episode_observed_no_success = int(
        post_control_health.get("post_control_episode_observed_no_success_count")
        or post_control_health.get("post_control_observed_no_success_count")
        or 0
    )
    post_control_episode_success = int(
        post_control_health.get("post_control_episode_success_count")
        or post_control_health.get("post_control_success_count")
        or 0
    )
    post_control_episode_success_rate = (
        post_control_health.get("post_control_episode_success_rate")
        if "post_control_episode_success_rate" in post_control_health
        else post_control_health.get("post_control_success_rate")
    )
    post_control_episode_no_followup_rate = (
        post_control_episode_no_followup / control_episode_count
        if control_episode_count
        else None
    )
    post_control_episode_observed_no_success_rate = (
        post_control_episode_observed_no_success / post_control_episode_windows
        if post_control_episode_windows
        else None
    )
    post_control_no_followup_rate = (
        post_control_no_followup / active_control_events if active_control_events else None
    )
    post_control_observed_no_success_rate = (
        post_control_observed_no_success / post_control_windows
        if post_control_windows
        else None
    )
    components.append(
        _component(
            component="hill_climb_controls",
            status="needs_attention" if control_due else "ok",
            summary={
                "workspace_count": hill.get("workspace_count", 0),
                "stagnant_workspace_count": hill.get("stagnant_workspace_count", 0),
                "status_counts": hill_status_counts,
                "active_control_event_count": active_control_events,
                "post_control_window_count": post_control_windows,
                "post_control_no_followup_count": post_control_no_followup,
                "post_control_no_followup_rate": post_control_no_followup_rate,
                "post_control_observed_no_success_count": post_control_observed_no_success,
                "post_control_observed_no_success_rate": post_control_observed_no_success_rate,
                "post_control_success_count": post_control_success,
                "post_control_success_rate": post_control_success_rate,
                "control_episode_count": control_episode_count,
                "post_control_episode_window_count": post_control_episode_windows,
                "post_control_episode_no_followup_count": post_control_episode_no_followup,
                "post_control_episode_no_followup_rate": post_control_episode_no_followup_rate,
                "post_control_episode_observed_no_success_count": (
                    post_control_episode_observed_no_success
                ),
                "post_control_episode_observed_no_success_rate": (
                    post_control_episode_observed_no_success_rate
                ),
                "post_control_episode_success_count": post_control_episode_success,
                "post_control_episode_success_rate": post_control_episode_success_rate,
                "control_followup_policy_totals": control_followup_policy,
                "post_control_diagnostic_counts": post_control_diagnostic_counts,
                "post_control_diagnostic_samples": post_control_diagnostic_samples[:5],
                "control_episode_recovery_counts": control_episode_recovery_counts,
                "control_episode_recovery_unresolved_counts": (
                    control_episode_recovery_unresolved_counts
                ),
                "control_episode_recovery_resolution_counts": (
                    control_episode_recovery_resolution_counts
                ),
                "control_episode_recovery_admission_packet_counts": (
                    control_episode_recovery_admission_packet_counts
                ),
                "control_episode_recovery_queue": control_episode_recovery_queue[:5],
            },
            action="inspect workspaces where stagnation had no active breadth-control evidence"
            if control_due
            else "no action",
            next_command=_make_command(
                "autoresearch-hillclimb-audit",
                PROJECT=project,
                STAGNATION_THRESHOLD=stagnation_threshold if stagnation_threshold != 2 else "",
                RECOVERY_QUEUE=1,
                RECOVERY_LIMIT=20,
                JSON=1,
            ),
        )
    )

    operations = _operations_intelligence(repo)
    agentic_workbench = dict(operations.get("agentic_workbench") or {})
    subscription_outcomes = dict(agentic_workbench.get("subscription_outcomes") or {})
    subscription_summary = dict(subscription_outcomes.get("summary") or {})
    route_coverage = dict(agentic_workbench.get("route_row_coverage") or {})
    source_health = dict(operations.get("source_health_summary") or {})
    source_health_issues = int(source_health.get("issue_count") or 0)
    blocking_source_issues = int(source_health.get("blocking_count") or 0)
    warning_source_issues = int(source_health.get("warning_count") or 0)
    route_rows_needed = int(route_coverage.get("additional_route_rows_needed") or 0)
    unexplained_bypasses = int(
        agentic_workbench.get("ready_workbench_bypasses_without_reason") or 0
    )
    route_needs_attention = bool(route_coverage.get("needs_logging_attention"))
    operations_needs_attention = (
        route_needs_attention
        or blocking_source_issues > 0
        or unexplained_bypasses > 0
    )
    components.append(
        _component(
            component="operations_intelligence",
            status="needs_attention" if operations_needs_attention else "ok",
            summary={
                "agentic_workbench_rows": agentic_workbench.get("rows", 0),
                "route_row_coverage_status": route_coverage.get("status"),
                "route_rows": route_coverage.get("route_rows", 0),
                "recommended_min_route_rows": route_coverage.get("recommended_min_route_rows", 0),
                "additional_route_rows_needed": route_rows_needed,
                "ready_workbench_bypasses": agentic_workbench.get("ready_workbench_bypasses", 0),
                "ready_workbench_bypasses_without_reason": unexplained_bypasses,
                "missing_surface_preparations": agentic_workbench.get("missing_surface_preparations", 0),
                "source_health_issues": source_health_issues,
                "source_health_blockers": blocking_source_issues,
                "source_health_warnings": warning_source_issues,
                "source_health_issue_type_counts": source_health.get("issue_type_counts", {}),
                "source_health_issue_sample": list(source_health.get("issue_sample") or [])[:5],
                "subscription_outcome_status": subscription_outcomes.get("status"),
                "clean_matched_run_group_count": subscription_summary.get(
                    "clean_matched_run_group_count", 0
                ),
                "weak_matched_run_group_count": subscription_summary.get(
                    "weak_matched_run_group_count", 0
                ),
            },
            action="record routed RD decisions or repair blocking action-intelligence sources"
            if operations_needs_attention
            else "no action",
            next_command=_make_command("operations-intelligence"),
        )
    )

    component_status = _overall_status(components)
    subscription_outcomes = _subscription_outcomes(repo=repo, project=project)
    evidence_gaps: list[dict[str, Any]] = []
    coverage_opportunities: list[dict[str, Any]] = []
    low_control_success = (
        control_episode_count >= CONTROL_OUTCOME_MIN_EVENTS
        and post_control_episode_success_rate is not None
        and float(post_control_episode_success_rate) < CONTROL_OUTCOME_MIN_SUCCESS_RATE
    )
    high_control_no_followup = (
        control_episode_count >= CONTROL_OUTCOME_MIN_EVENTS
        and post_control_episode_no_followup_rate is not None
        and post_control_episode_no_followup_rate > CONTROL_OUTCOME_MAX_NO_FOLLOWUP_RATE
    )
    if low_control_success or high_control_no_followup:
        evidence_gaps.append(
            {
                "id": "hill_climb_control_outcomes",
                "status": "weak_post_control_evidence",
                "recovery_kind": LOCAL_VERIFICATION_RECOVERY_KIND,
                "recovery_channel": "kernel_health",
                "summary": {
                    "active_control_event_count": active_control_events,
                    "post_control_window_count": post_control_windows,
                    "post_control_no_followup_count": post_control_no_followup,
                    "post_control_no_followup_rate": post_control_no_followup_rate,
                    "post_control_observed_no_success_count": post_control_observed_no_success,
                    "post_control_observed_no_success_rate": post_control_observed_no_success_rate,
                    "post_control_success_count": post_control_success,
                    "post_control_success_rate": post_control_success_rate,
                    "control_episode_count": control_episode_count,
                    "post_control_episode_window_count": post_control_episode_windows,
                    "post_control_episode_no_followup_count": post_control_episode_no_followup,
                    "post_control_episode_no_followup_rate": post_control_episode_no_followup_rate,
                    "post_control_episode_observed_no_success_count": (
                        post_control_episode_observed_no_success
                    ),
                    "post_control_episode_observed_no_success_rate": (
                        post_control_episode_observed_no_success_rate
                    ),
                    "post_control_episode_success_count": post_control_episode_success,
                    "post_control_episode_success_rate": post_control_episode_success_rate,
                    "control_followup_policy_totals": control_followup_policy,
                    "post_control_diagnostic_counts": post_control_diagnostic_counts,
                    "post_control_diagnostic_samples": post_control_diagnostic_samples[:5],
                    "control_episode_recovery_counts": control_episode_recovery_counts,
                    "control_episode_recovery_unresolved_counts": (
                        control_episode_recovery_unresolved_counts
                    ),
                    "control_episode_recovery_resolution_counts": (
                        control_episode_recovery_resolution_counts
                    ),
                    "control_episode_recovery_admission_packet_counts": (
                        control_episode_recovery_admission_packet_counts
                    ),
                    "control_episode_recovery_queue": control_episode_recovery_queue[:5],
                    "min_success_rate": CONTROL_OUTCOME_MIN_SUCCESS_RATE,
                    "max_no_followup_rate": CONTROL_OUTCOME_MAX_NO_FOLLOWUP_RATE,
                },
                "action": (
                    "inspect whether pivots, blitzes, and primitive rotation "
                    "produce follow-up evidence rather than only activation rows"
                ),
                "next_command": _make_command(
                    "autoresearch-hillclimb-audit",
                    PROJECT=project,
                    STAGNATION_THRESHOLD=stagnation_threshold if stagnation_threshold != 2 else "",
                    RECOVERY_QUEUE=1,
                    RECOVERY_LIMIT=20,
                    JSON=1,
                ),
            }
        )
    if not_triggered:
        dormant_rows = [
            {
                "mechanism_id": row.get("mechanism_id"),
                "label": row.get("label"),
                "trigger": row.get("trigger"),
                "activation_hint": row.get("activation_hint"),
            }
            for row in list(mechanism.get("rows") or [])
            if row.get("evidence_status") == "not_triggered"
        ][:8]
        coverage_opportunities.append(
            {
                "id": "not_triggered_mechanisms",
                "status": "not_triggered",
                "recovery_kind": LOCAL_VERIFICATION_RECOVERY_KIND,
                "recovery_channel": "kernel_health",
                "summary": {
                    "count": not_triggered,
                    "examples": dormant_rows,
                },
                "action": (
                    "run a project or fixture that exercises these optional controls "
                    "before making a mechanism-coverage claim"
                ),
                "next_command": _make_command(
                    "autoresearch-consequence-audit",
                    PROJECT=project,
                    WORKSPACE=workspace,
                    JSON=1,
                ),
            }
        )
    if not bool(subscription_outcomes.get("ok")):
        matched_plan = list(subscription_outcomes.get("matched_run_plan") or [])
        first_candidate = matched_plan[0] if matched_plan else {}
        evidence_gaps.append(
            {
                "id": "subscription_outcomes",
                "status": subscription_outcomes.get("status"),
                "recovery_kind": LOCAL_VERIFICATION_RECOVERY_KIND,
                "recovery_channel": "kernel_health",
                "summary": {
                    **dict(subscription_outcomes.get("summary") or {}),
                    "suggested_matched_pair_command": first_candidate.get("matched_pair_command"),
                    "suggested_matched_pair_project": first_candidate.get("project"),
                    "suggested_matched_pair_rubric": first_candidate.get("rubric"),
                    "suggested_matched_pair_suitability": first_candidate.get("suitability_score"),
                },
                "action": subscription_outcomes.get("action"),
                "next_command": _make_command(
                    "autoresearch-subscription-outcome-audit",
                    PROJECT=project,
                    JSON=1,
                ),
            }
        )
    status = (
        "attention"
        if evidence_gaps and component_status == "ok"
        else component_status
    )
    return {
        "schema": "ztare-autoresearch-kernel-health-v1",
        "scope": {
            "repo": str(repo),
            "project": project,
            "workspace": str(workspace) if workspace else None,
            "rubric": str(rubric) if rubric else None,
            "intake": str(packet) if packet else None,
            "packet": str(packet) if packet else None,
            "stagnation_threshold": stagnation_threshold,
        },
        "summary": {
            "overall_status": status,
            "component_status": component_status,
            "component_counts": {
                state: sum(1 for row in components if row["status"] == state)
                for state in ("ok", "attention", "needs_attention")
            },
            "component_count": len(components),
            "evidence_gap_count": len(evidence_gaps),
            "coverage_opportunity_count": len(coverage_opportunities),
        },
        "components": components,
        "evidence_gaps": evidence_gaps,
        "coverage_opportunities": coverage_opportunities,
    }


def render_text(report: dict[str, Any]) -> str:
    summary = report["summary"]
    scope = report["scope"]
    lines = [
        "Autoresearch kernel health",
        f"status={summary['overall_status']} components={summary['component_count']}",
        "component_counts=" + json.dumps(summary["component_counts"], sort_keys=True),
        f"evidence_gaps={summary.get('evidence_gap_count', 0)}",
        f"coverage_opportunities={summary.get('coverage_opportunity_count', 0)}",
        (
            "scope="
            + json.dumps(
                {
                    "project": scope.get("project"),
                    "workspace": scope.get("workspace"),
                    "rubric": scope.get("rubric"),
                    "intake": scope.get("intake"),
                    "packet": scope.get("packet"),
                    "stagnation_threshold": scope.get("stagnation_threshold"),
                },
                sort_keys=True,
            )
        ),
    ]
    for row in report["components"]:
        lines.append(
            "- {component}: {status}; action={action}; next={next_command}; summary={summary}".format(
                component=row["component"],
                status=row["status"],
                action=row["action"],
                next_command=row["next_command"],
                summary=json.dumps(row["summary"], sort_keys=True),
            )
        )
    for row in report.get("evidence_gaps") or []:
        lines.append(
            "- evidence_gap:{id}: {status}; action={action}; next={next_command}; "
            "summary={summary}".format(
                id=row["id"],
                status=row["status"],
                action=row["action"],
                next_command=row["next_command"],
                summary=json.dumps(row["summary"], sort_keys=True),
            )
        )
    for row in report.get("coverage_opportunities") or []:
        lines.append(
            "- coverage_opportunity:{id}: {status}; action={action}; next={next_command}; "
            "summary={summary}".format(
                id=row["id"],
                status=row["status"],
                action=row["action"],
                next_command=row["next_command"],
                summary=json.dumps(row["summary"], sort_keys=True),
            )
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", help="Restrict project-scoped health where supported.")
    parser.add_argument("--workspace", help="Restrict mechanism evidence to one workspace.")
    parser.add_argument("--rubric", help="Restrict rubric-mode audit to one rubric path.")
    parser.add_argument(
        "--intake",
        "--packet",
        dest="packet",
        help="Optional project-intake JSON readiness boundary; --packet is a compatibility alias.",
    )
    parser.add_argument("--stagnation-threshold", type=int, default=2)
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when overall status is not ok.",
    )
    args = parser.parse_args(argv)

    report = build_autoresearch_kernel_health(
        project=args.project,
        workspace=args.workspace,
        rubric=args.rubric,
        packet=args.packet,
        stagnation_threshold=args.stagnation_threshold,
    )
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 1 if args.strict and report["summary"]["overall_status"] != "ok" else 0


if __name__ == "__main__":
    raise SystemExit(main())
