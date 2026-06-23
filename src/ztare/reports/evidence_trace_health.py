"""Fixture for the raw evidence -> loop trace chain.

The purpose is narrow: prove that a source bundle can move through the
deterministic trace surfaces that the in-loop autoresearch kernel consumes.
It does not call an LLM and does not certify any domain result.
"""
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from ztare.common.graph_carrier import validate_graph_carrier
from ztare.gates.derived_constraints import (
    render_confirmed_constraints_prompt_section,
    update_derived_constraints_ledger,
    write_derived_constraints_brief,
)
from ztare.orchestrator.mutator_briefing import BriefingContext, default_briefing
from ztare.reports.autoresearch_trace import REPO, build_autoresearch_trace
from ztare.validator.hypothesis_projection import build_projection
from ztare.workspace.compile_evidence import (
    collect_sources,
    render_evidence_markdown,
    sha256_text,
)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def _fixture_packet(project: str) -> dict[str, Any]:
    return {
        "project": project,
        "compiler_summary": (
            "Synthetic DK0 fixture packet. It checks source/evidence lineage, "
            "not a domain claim."
        ),
        "immutable_ground_truth": [
            {
                "statement": "The fixture source defines one bounded claim and one falsifier.",
                "strength": "source-bound",
                "source_ids": ["S001"],
            }
        ],
        "numerical_ranges_and_constraints": [],
        "identified_contradictions": [],
        "epistemic_voids": [
            {
                "unknown": "Whether the proposed claim survives an independent evaluator.",
                "why_it_matters": "The kernel should preserve the next falsifier.",
                "blocking": "Blocks promotion from evidence output to claim.",
            }
        ],
        "provenance": [
            {
                "source_id": "S001",
                "path": "source.md",
                "kind": "md",
                "source_type": "source_evidence",
                "summary": "Bounded claim source for DK0 trace fixture.",
            }
        ],
        "candidate_claims_to_test": [
            {
                "claim": "The trace preserves raw source refs into downstream surfaces.",
                "why_testable": "Each surface must expose S001 or the source hash.",
                "depends_on": ["S001"],
                "source_ids": ["S001"],
                "priority": "high",
            }
        ],
    }


def build_evidence_trace_fixture() -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        project_dir = root / "projects" / "dk0_trace_fixture"
        raw_dir = project_dir / "raw"
        workspace = project_dir / "workspace"
        raw_dir.mkdir(parents=True, exist_ok=True)
        workspace.mkdir(parents=True, exist_ok=True)

        source_text = "\n".join(
            [
                "# DK0 Trace Source",
                "",
                "Claim: the kernel trace must preserve source S001.",
                "Evidence: the falsifier is explicit and source-bound.",
                "Non-claim: this fixture is not a domain benchmark.",
                "Falsifier: any downstream carrier without S001 or the source hash fails.",
                "",
            ]
        )
        source_path = raw_dir / "source.md"
        source_path.write_text(source_text, encoding="utf-8")
        (raw_dir / "source_type_map.json").write_text(
            json.dumps({"source.md": "source_evidence"}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        source_hash = sha256_text(source_text.strip())

        sources, source_warnings = collect_sources(
            raw_dir=raw_dir,
            max_files=5,
            max_chars_per_file=2000,
            max_total_chars=5000,
        )
        packet = _fixture_packet(project_dir.name)
        evidence_text = render_evidence_markdown(packet, project_dir.name, "June 19, 2026")
        evidence_path = project_dir / "evidence.txt"
        evidence_path.write_text(evidence_text, encoding="utf-8")
        evidence_hash = sha256_text(evidence_text)
        _write_json(workspace / "evidence_packet.json", packet)
        _write_json(
            workspace / "evidence_compile_provenance.json",
            {
                "schema": "ztare-evidence-trace-fixture-provenance-v1",
                "mode": "raw",
                "sources": [{k: v for k, v in source.items() if k != "content"} for source in sources],
                "source_count": len(sources),
                "evidence_path": str(evidence_path),
                "evidence_sha256": evidence_hash,
                "warnings": source_warnings,
            },
        )

        proposal = {
            "constraint": "Downstream carriers must preserve S001 or the source hash.",
            "applies_to": "raw evidence compile lineage",
            "failure_family": "source_lineage_drop",
            "severity": "blocking",
            "producer": "meta_judge",
            "rationale": "A trace that loses source refs cannot support claim audit.",
            "non_applicability_condition": "Only if the run has no source-bound evidence.",
        }
        ledger_path = workspace / "derived_constraints.json"
        update_derived_constraints_ledger(
            project=project_dir.name,
            ledger_path=ledger_path,
            proposals=[proposal],
            run_id=1001,
            iteration_index=1,
            source_score=50,
            weakest_point="source lineage missing from downstream carrier",
            score_regime_fingerprint="trace-a",
        )
        ledger = update_derived_constraints_ledger(
            project=project_dir.name,
            ledger_path=ledger_path,
            proposals=[proposal],
            run_id=1002,
            iteration_index=2,
            source_score=45,
            weakest_point="source lineage missing from downstream carrier",
            score_regime_fingerprint="trace-b",
        )
        write_derived_constraints_brief(ledger, workspace / "derived_constraints_brief.md")
        constraints_prompt = render_confirmed_constraints_prompt_section(ledger_path)

        repeated_failure = (
            "source lineage missing from downstream carrier despite S001 and "
            "source hash being available"
        )
        _write_jsonl(
            workspace / "eval_history.jsonl",
            [
                {
                    "iteration": 1,
                    "score": 50,
                    "timestamp": "2026-06-19T00:00:00Z",
                    "hypothesis": "baseline trace",
                    "weakest_point": "frontier still needs source-bound carrier proof",
                    "artifact_refs": ["projects/dk0_trace_fixture/evidence.txt"],
                    "held_out_admission": {"source_id": "S001"},
                    "worker_archetype": "fixture",
                    "worker_capability": "deterministic",
                    "worker_state": "stateless",
                    "worker_identity": "fixture",
                    "transport": "local_fixture",
                },
                {
                    "iteration": 2,
                    "score": 40,
                    "timestamp": "2026-06-19T00:01:00Z",
                    "hypothesis": "dropped source ref",
                    "weakest_point": repeated_failure,
                    "artifact_refs": ["projects/dk0_trace_fixture/evidence.txt"],
                },
                {
                    "iteration": 3,
                    "score": 45,
                    "timestamp": "2026-06-19T00:02:00Z",
                    "hypothesis": "renamed dropped source ref",
                    "weakest_point": repeated_failure,
                    "artifact_refs": ["projects/dk0_trace_fixture/evidence.txt"],
                },
            ],
        )
        _write_jsonl(
            workspace / "dag_steering_log.jsonl",
            [
                {"selected_node_id": "trace_baseline", "selected_urgency": 0.2},
                {"selected_node_id": "drop_source_ref", "selected_urgency": 0.9},
                {"selected_node_id": "drop_source_ref", "selected_urgency": 0.9},
            ],
        )
        _write_json(
            project_dir / "latest_probability_dag.json",
            {
                "nodes": [
                    {
                        "id": "trace_baseline",
                        "label": "preserve S001",
                        "probability": 0.4,
                    },
                    {
                        "id": "drop_source_ref",
                        "label": "source lineage drop",
                        "probability": 0.7,
                    },
                ],
                "edges": [
                    {
                        "from": "trace_baseline",
                        "to": "drop_source_ref",
                        "weight": 0.9,
                    }
                ],
            },
        )
        graph_carrier = {
            "graph_id": f"{project_dir.name}:latest_probability_dag",
            "graph_kind": "probability_dag",
            "producer": "latest_probability_dag.json",
            "source_artifacts": [str(project_dir / "latest_probability_dag.json")],
            "consumer": "compute_dag_steering_context",
            "freshness_rule": "rerun after eval_history or probability DAG updates",
            "node_count": 2,
            "edge_count": 1,
            "node_vocabulary": ["id", "label", "probability"],
            "edge_vocabulary": ["from", "to", "weight"],
            "diagnostics": [
                {
                    "method": "edge_weight_times_probability",
                    "baseline": "previous run order or no steering",
                    "result_summary": "steering selected drop_source_ref after repeated source-lineage failure",
                }
            ],
            "noise_filter": "ignore malformed nodes without ids and edges without sources",
            "decision_receipt": {
                "effect": "strategy_change",
                "selected_next_discriminator": "source-lineage-drop discriminator",
            },
            "library_anchor": "standard library JSON plus local DAG parser",
            "literature_anchor": "directed acyclic graph scheduling and dependency analysis",
        }
        graph_validation = validate_graph_carrier(graph_carrier)

        projection = build_projection(project_dir)
        briefing = default_briefing()
        briefing_text = briefing.render(
            BriefingContext(
                project_dir=project_dir,
                workspace_dir=workspace,
                iter_index=4,
                rubric={"require_i_model_in_submission": False},
                stagnation_count=3,
            )
        )
        briefing_records_path = workspace / "mutator_briefing_iter_004_records.json"
        briefing_records = json.loads(briefing_records_path.read_text(encoding="utf-8"))

        checks = [
            {
                "id": "raw_source_collected_with_hash",
                "passed": (
                    len(sources) == 1
                    and sources[0]["source_id"] == "S001"
                    and sources[0]["source_type"] == "source_evidence"
                    and sources[0]["full_sha256"] == source_hash
                ),
            },
            {
                "id": "source_typing_preserved_in_compile_provenance",
                "passed": (
                    len(sources) == 1
                    and sources[0]["path"] == "source.md"
                    and sources[0]["source_type"] == packet["provenance"][0]["source_type"]
                ),
            },
            {
                "id": "evidence_packet_preserves_source_id",
                "passed": "S001" in evidence_text and bool(evidence_hash),
            },
            {
                "id": "derived_constraint_confirmed_and_rendered",
                "passed": (
                    ledger["confirmed_constraint_count"] == 1
                    and "DC-001" in constraints_prompt
                    and "S001" in constraints_prompt
                ),
            },
            {
                "id": "projection_builds_negative_constraint",
                "passed": (
                    projection.summary.node_count == 3
                    and projection.summary.negative_constraint_count == 1
                    and projection.negative_constraints[0].count == 2
                ),
            },
            {
                "id": "briefing_consumes_projection_constraint",
                "passed": (
                    "negative constraint" in briefing_text
                    and "drop_source_ref" in briefing_text
                    and any(
                        row.get("source_type") == "projection_negative_constraint"
                        for row in briefing_records.get("records", [])
                    )
                ),
            },
            {
                "id": "graph_carrier_validates_decision_receipt",
                "passed": bool(
                    graph_validation.ok
                    and graph_carrier["decision_receipt"]["effect"] == "strategy_change"
                    and graph_carrier["decision_receipt"]["selected_next_discriminator"]
                ),
            },
        ]
        all_passed = all(bool(check["passed"]) for check in checks)
        return {
            "schema": "ztare-evidence-trace-health-v1",
            "all_passed": all_passed,
            "num_cases": len(checks),
            "num_passed": sum(1 for check in checks if check["passed"]),
            "checks": checks,
            "trace": {
                "project": project_dir.name,
                "source_id": "S001",
                "source_type": sources[0]["source_type"] if sources else None,
                "source_sha256": source_hash,
                "evidence_sha256": evidence_hash,
                "confirmed_constraint_count": ledger["confirmed_constraint_count"],
                "projection_nodes": projection.summary.node_count,
                "projection_negative_constraints": projection.summary.negative_constraint_count,
                "briefing_record_count": len(briefing_records.get("records", [])),
                "graph_carrier_ok": graph_validation.ok,
                "graph_carrier_errors": graph_validation.errors,
                "graph_carrier_effect": graph_carrier["decision_receipt"]["effect"],
            },
        }


def _surface_status(trace: dict[str, Any], surface: str) -> str | None:
    row = _surface_row(trace, surface)
    if row is not None:
        return str(row.get("status") or "")
    return None


def _surface_row(trace: dict[str, Any], surface: str) -> dict[str, Any] | None:
    for row in trace.get("carrier_chain", []):
        if isinstance(row, dict) and row.get("surface") == surface:
            return row
    return None


def _evidence_readiness(trace: dict[str, Any]) -> dict[str, Any]:
    source_index_status = _surface_status(trace, "source_index")
    compile_provenance_status = _surface_status(trace, "compile_provenance")
    evidence_output_status = _surface_status(trace, "evidence_output")
    evidence_replay_row = _surface_row(trace, "evidence_replay") or {}
    raw_evidence_replay_status = str(evidence_replay_row.get("status") or "")
    evidence_replay_required = bool(evidence_replay_row.get("required"))
    evidence_replay_status = (
        raw_evidence_replay_status
        if evidence_replay_required or raw_evidence_replay_status not in {"missing_manifest", ""}
        else "not_required"
    )
    status = "fresh"
    if source_index_status != "fresh":
        status = "blocked"
    if compile_provenance_status != "fresh":
        status = "blocked"
    if evidence_output_status != "fresh":
        status = "blocked"
    if evidence_replay_status not in {"ok", "not_required", "", None}:
        status = "blocked"
    return {
        "status": status,
        "source_index_status": source_index_status,
        "compile_provenance_status": compile_provenance_status,
        "evidence_output_status": evidence_output_status,
        "evidence_replay_status": evidence_replay_status,
        "evidence_replay_required": evidence_replay_required,
        "raw_evidence_replay_status": raw_evidence_replay_status,
    }


def build_project_evidence_trace_health(
    *,
    project: str,
    rubric: str | None = None,
    intake: str | None = None,
    model: str = "gemini",
    repo: Path = REPO,
) -> dict[str, Any]:
    """Audit the raw/source/evidence/trace chain for a real project surface."""
    trace = build_autoresearch_trace(
        project=project,
        rubric=rubric,
        model=model,
        packet=intake,
        repo=repo,
        full_health=False,
    )
    surfaces = trace.get("surfaces", {})
    kernel_entry = trace.get("kernel_entry", {})
    route_preview = trace.get("route_preview", {})
    projection = trace.get("projection", {})
    claim_support = surfaces.get("claim_support") if isinstance(surfaces.get("claim_support"), dict) else {}
    next_commands = [str(item) for item in trace.get("next_commands", [])]
    constraint_count = int(surfaces.get("confirmed_constraint_count") or 0) + int(
        surfaces.get("provisional_constraint_count") or 0
    )
    evidence_readiness = _evidence_readiness(trace)
    checks = [
        {
            "id": "project_trace_complete",
            "passed": trace.get("status") == "complete_trace",
            "detail": trace.get("status"),
        },
        {
            "id": "raw_sources_present",
            "passed": int(surfaces.get("raw_file_count") or 0) > 0,
            "detail": surfaces.get("raw_file_count"),
        },
        {
            "id": "source_preflight_ready",
            "passed": bool(surfaces.get("source_preflight_ok"))
            and not bool(surfaces.get("source_preflight_blocking")),
            "detail": surfaces.get("source_preflight_status"),
        },
        {
            "id": "source_index_fresh",
            "passed": _surface_status(trace, "source_index") == "fresh",
            "detail": _surface_status(trace, "source_index"),
        },
        {
            "id": "compile_provenance_fresh",
            "passed": _surface_status(trace, "compile_provenance") == "fresh",
            "detail": _surface_status(trace, "compile_provenance"),
        },
        {
            "id": "evidence_output_fresh",
            "passed": _surface_status(trace, "evidence_output") == "fresh",
            "detail": _surface_status(trace, "evidence_output"),
        },
        {
            "id": "evidence_readiness_replay_verified_or_not_required",
            "passed": evidence_readiness.get("evidence_replay_status")
            in {"ok", "not_required", ""},
            "detail": evidence_readiness.get("evidence_replay_status"),
        },
        {
            "id": "claim_support_available",
            "passed": bool(claim_support.get("ok")),
            "detail": claim_support.get("status") or "not_reported",
        },
        {
            "id": "derived_constraints_available",
            "passed": constraint_count > 0,
            "detail": constraint_count,
        },
        {
            "id": "projection_available",
            "passed": bool(projection.get("available")),
            "detail": projection.get("node_count"),
        },
        {
            "id": "route_preview_available",
            "passed": bool(route_preview.get("available")),
            "detail": route_preview.get("source_name") or route_preview.get("source"),
        },
        {
            "id": "kernel_entry_ready",
            "passed": bool(kernel_entry.get("can_enter_kernel")),
            "detail": kernel_entry.get("status"),
        },
        {
            "id": "guarded_run_command_available",
            "passed": bool(kernel_entry.get("preflight_command") and kernel_entry.get("run_command")),
            "detail": kernel_entry.get("run_command"),
        },
        {
            "id": "no_raw_loop_shortcut_in_next_commands",
            "passed": not any("make experiment-loop" in command for command in next_commands),
            "detail": next_commands,
        },
    ]
    all_passed = all(bool(check["passed"]) for check in checks)
    return {
        "schema": "ztare-evidence-trace-health-v1",
        "mode": "project",
        "project": project,
        "rubric": rubric,
        "intake": intake,
        "all_passed": all_passed,
        "num_cases": len(checks),
        "num_passed": sum(1 for check in checks if check["passed"]),
        "checks": checks,
        "trace": {
            "status": trace.get("status"),
            "readiness": trace.get("readiness"),
            "readiness_canonical": trace.get("readiness_canonical"),
            "missing": trace.get("missing", []),
            "blocking_missing": trace.get("blocking_missing", []),
            "evidence_readiness": evidence_readiness,
            "claim_support": {
                "status": claim_support.get("status"),
                "claim_count": claim_support.get("claim_count", 0),
                "weak_or_unsourced_count": claim_support.get("weak_or_unsourced_count", 0),
                "source_context_blocked_count": claim_support.get(
                    "source_context_blocked_count",
                    0,
                ),
                "status_counts": claim_support.get("status_counts", {}),
                "source_context_status_counts": claim_support.get(
                    "source_context_status_counts",
                    {},
                ),
            },
            "raw_file_count": surfaces.get("raw_file_count"),
            "source_preflight_status": surfaces.get("source_preflight_status"),
            "source_index_status": evidence_readiness.get("source_index_status"),
            "compile_provenance_status": evidence_readiness.get(
                "compile_provenance_status"
            ),
            "evidence_output_status": evidence_readiness.get("evidence_output_status"),
            "constraint_count": constraint_count,
            "projection_available": projection.get("available"),
            "projection_nodes": projection.get("node_count"),
            "kernel_entry_can_enter": kernel_entry.get("can_enter_kernel"),
            "route_can_run_now": route_preview.get("can_run_now"),
            "next_commands": next_commands,
            "recovery_actions": trace.get("recovery_actions", []),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", help="Project slug or path for real-project trace audit.")
    parser.add_argument("--rubric", help="Rubric slug or path for real-project trace audit.")
    parser.add_argument("--intake", "--packet", dest="intake", help="Optional project-intake JSON.")
    parser.add_argument(
        "--model",
        default="gemini",
        help="Model label to render in suggested evidence recovery commands. No model call is made.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON.")
    args = parser.parse_args(argv)

    if args.project:
        report = build_project_evidence_trace_health(
            project=args.project,
            rubric=args.rubric,
            intake=args.intake,
            model=args.model,
        )
        label = f"Evidence trace project audit: project={args.project}"
    else:
        report = build_evidence_trace_fixture()
        label = "Evidence trace fixture"
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            f"{label}: {report['num_passed']}/{report['num_cases']} "
            f"passed (all_passed={report['all_passed']})"
        )
        for check in report["checks"]:
            status = "PASS" if check["passed"] else "FAIL"
            print(f"  {status} {check['id']}")
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
