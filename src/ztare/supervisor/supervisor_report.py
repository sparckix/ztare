from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.ztare.supervisor.supervisor_attended_autoloop import fresh_input_tokens
from src.ztare.supervisor.supervisor_backlog import build_what_next
from src.ztare.supervisor.supervisor_state import status_from_dict


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _load_events(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    events: list[dict[str, Any]] = []
    for raw_line in path.read_text().splitlines():
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        events.append(json.loads(raw_line))
    return events


def _event_to_summary(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "revision": int(event["revision"]),
        "actor": str(event["actor"]),
        "prior_state": str(event["prior_state"]),
        "new_state": str(event["new_state"]),
        "reason": str(event["reason"]),
        "timestamp": str(event["timestamp"]),
        "human_gate_reason": event.get("human_gate_reason"),
    }


def build_supervisor_report(
    status_path: Path,
    *,
    events_path: Path | None = None,
    recent_event_limit: int = 5,
) -> dict[str, Any]:
    status = status_from_dict(_read_json(status_path))
    what_next = build_what_next(status_path)
    events = _load_events(events_path)
    recent_events = [_event_to_summary(event) for event in events[-recent_event_limit:]]
    last_event = recent_events[-1] if recent_events else None

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run_id": status.run_id,
        "program_id": status.active_program,
        "target": status.active_target,
        "state": status.state.value,
        "next_actor": status.next_actor.value,
        "status_reason": status.status_reason.value,
        "human_gate_reason": (
            status.human_gate_reason.value if status.human_gate_reason is not None else None
        ),
        "human_gate_resolved": status.human_gate_resolved,
        "debate_file": status.debate_file,
        "debate_last_turn": status.debate_last_turn,
        "artifact_paths": {
            "spec": status.artifact_paths.spec,
            "implementation": list(status.artifact_paths.implementation),
            "verification_report": status.artifact_paths.verification_report,
            "error_report": status.artifact_paths.error_report,
        },
        "costs": {
            "program_cost_usd": status.program_cost_usd,
            "refinement_cost_usd": status.refinement_cost_usd,
            "last_turn_usage": {
                "model_name": status.last_turn_usage.model_name,
                "input_tokens": status.last_turn_usage.input_tokens,
                "output_tokens": status.last_turn_usage.output_tokens,
                "fresh_input_tokens": fresh_input_tokens(status.last_turn_usage),
                "cache_creation_input_tokens": status.last_turn_usage.cache_creation_input_tokens,
                "cache_read_input_tokens": status.last_turn_usage.cache_read_input_tokens,
                "estimated_cost_usd": status.last_turn_usage.estimated_cost_usd,
                "telemetry_captured": status.last_turn_usage.telemetry_captured,
            },
        },
        "manifest": what_next.get("manifest"),
        "next_action": what_next.get("next_action"),
        "last_event": last_event,
        "recent_events": recent_events,
        "event_count": len(events),
    }


def render_supervisor_report_markdown(report: dict[str, Any]) -> str:
    manifest = report.get("manifest") or {}
    next_packet = manifest.get("next_packet") if isinstance(manifest, dict) else None
    costs = report["costs"]
    last_turn_usage = costs["last_turn_usage"]
    lines = [
        f"# Supervisor Report: {report['program_id']}",
        "",
        "## Run",
        "",
        f"- run_id: `{report['run_id']}`",
        f"- target: `{report['target']}`",
        f"- state: `{report['state']}`",
        f"- next_actor: `{report['next_actor']}`",
        f"- status_reason: `{report['status_reason']}`",
        f"- human_gate_reason: `{report['human_gate_reason']}`",
        f"- debate_file: `{report['debate_file']}`",
        f"- debate_last_turn: `{report['debate_last_turn']}`",
        "",
        "## Progress",
        "",
        f"- completion_policy: `{manifest.get('completion_policy')}`",
        f"- num_packets: `{manifest.get('num_packets')}`",
        f"- num_complete: `{manifest.get('num_complete')}`",
        f"- num_pending_like: `{manifest.get('num_pending_like')}`",
    ]
    if next_packet is not None:
        lines.extend(
            [
                f"- next_packet: `{next_packet['packet_id']}`",
                f"- next_packet_status: `{next_packet['status']}`",
                f"- next_packet_title: {next_packet['title']}",
                f"- next_packet_summary: {next_packet['summary']}",
            ]
        )
        if next_packet.get("read_bundle"):
            lines.append(f"- next_packet_read_bundle_size: `{len(next_packet['read_bundle'])}`")
        if next_packet.get("token_budget"):
            lines.append(f"- next_packet_token_budget: `{json.dumps(next_packet['token_budget'], sort_keys=True)}`")
    else:
        lines.append("- next_packet: `none`")

    lines.extend(
        [
            "",
            "## Costs",
            "",
            f"- program_cost_usd: `{costs['program_cost_usd']}`",
            f"- refinement_cost_usd: `{costs['refinement_cost_usd']}`",
            f"- last_turn_model: `{last_turn_usage['model_name']}`",
            f"- last_turn_input_tokens: `{last_turn_usage['input_tokens']}`",
            f"- last_turn_output_tokens: `{last_turn_usage['output_tokens']}`",
            f"- last_turn_fresh_input_tokens: `{last_turn_usage['fresh_input_tokens']}`",
            f"- last_turn_estimated_cost_usd: `{last_turn_usage['estimated_cost_usd']}`",
            f"- last_turn_telemetry_captured: `{last_turn_usage['telemetry_captured']}`",
            "",
            "## Artifacts",
            "",
            f"- spec: `{report['artifact_paths']['spec']}`",
            f"- verification_report: `{report['artifact_paths']['verification_report']}`",
            f"- error_report: `{report['artifact_paths']['error_report']}`",
        ]
    )
    implementation_paths = report["artifact_paths"]["implementation"]
    if implementation_paths:
        lines.append("- implementation:")
        lines.extend(f"  - `{path}`" for path in implementation_paths)

    lines.extend(
        [
            "",
            "## Recommended Next Action",
            "",
            f"- `{report['next_action']}`",
        ]
    )
    if report["last_event"] is not None:
        last_event = report["last_event"]
        lines.extend(
            [
                "",
                "## Last Event",
                "",
                f"- revision: `{last_event['revision']}`",
                f"- actor: `{last_event['actor']}`",
                f"- transition: `{last_event['prior_state']} -> {last_event['new_state']}`",
                f"- timestamp: `{last_event['timestamp']}`",
                f"- reason: {last_event['reason']}",
            ]
        )

    if report["recent_events"]:
        lines.extend(["", "## Recent Events", ""])
        for event in report["recent_events"]:
            lines.append(
                f"- r{event['revision']} `{event['actor']}` `{event['prior_state']} -> {event['new_state']}`: {event['reason']}"
            )

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a read-only supervisor report.")
    parser.add_argument("--status-path", type=Path, required=True)
    parser.add_argument("--events-path", type=Path, default=None)
    parser.add_argument("--output-path", type=Path, default=None)
    parser.add_argument("--json-out", type=Path, default=None)
    parser.add_argument("--recent-event-limit", type=int, default=5)
    args = parser.parse_args()

    report = build_supervisor_report(
        args.status_path,
        events_path=args.events_path,
        recent_event_limit=args.recent_event_limit,
    )
    markdown = render_supervisor_report_markdown(report)

    if args.output_path is not None:
        args.output_path.parent.mkdir(parents=True, exist_ok=True)
        args.output_path.write_text(markdown)
        print(f"Report written to {args.output_path}")
    else:
        print(markdown.rstrip())

    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2) + "\n")
        print(f"JSON summary written to {args.json_out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
