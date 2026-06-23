"""Guided project-intake walkthrough for the ZTARE project userland.

This is not an interactive installer. It is a deterministic tutorial wrapper
around existing intake primitives: build a boundary object, validate it, and
optionally enqueue it once the source preflight passes.
"""
from __future__ import annotations

import argparse
import json
import shlex
from pathlib import Path
from typing import Any

from ztare.scaffold.substrate_queue import (
    EXTERNAL_REF_RE,
    build_project_packet,
    enqueue_project_packet,
    queue_dir_from_arg,
    stable_packet_id,
    validate_project_packet,
    validate_project_packet_path,
    write_project_packet,
)


REPO = Path(__file__).resolve().parents[3]
PROJECT_PACKET_DIR = REPO / "examples/project_packets"
LEGACY_PACKET_DIR = REPO / "examples/substrate_packets"


def _fixture_path(name: str) -> Path:
    preferred = PROJECT_PACKET_DIR / name
    return preferred if preferred.exists() else LEGACY_PACKET_DIR / name


READY_PACKET = _fixture_path("ready_demo_claims_intake.json")
MALFORMED_PACKET = _fixture_path("malformed_missing_evidence_intake.json")
OPS_DEMO_PROJECT = "ops_root_cause_diagnosis_demo"
OPS_DEMO_RUBRIC = "ops_root_cause_diagnosis_demo"
OPS_DEMO_PACKET = REPO / "projects" / OPS_DEMO_PROJECT / f"{OPS_DEMO_PROJECT}_intake.json"


def _quote(value: str) -> str:
    return shlex.quote(value)


def default_expected_command(project: str, rubric: str, task: str) -> str:
    return (
        f"ztare autoresearch route --task {_quote(task)} "
        f"--project {_quote(project)} --rubric {_quote(rubric)}"
    )


def _portable_local_refs(refs: list[str], *, packet_dir: Path | None) -> list[str]:
    portable: list[str] = []
    roots: list[Path] = []
    if packet_dir is not None:
        roots.append(packet_dir.resolve())
    roots.append(REPO.resolve())
    for ref in refs:
        if EXTERNAL_REF_RE.match(ref):
            portable.append(ref)
            continue
        path = Path(ref)
        if not path.is_absolute():
            portable.append(ref)
            continue
        try:
            resolved = path.resolve()
        except OSError:
            portable.append(ref)
            continue
        for root in roots:
            try:
                portable.append(str(resolved.relative_to(root)))
                break
            except ValueError:
                continue
        else:
            portable.append(ref)
    return portable


def _packet_preview(packet: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    packet_id = packet.get("packet_id") or stable_packet_id(packet)
    return {
        "intake_id": packet_id,
        "project": packet.get("project"),
        "rubric": packet.get("rubric"),
        "task": packet.get("task"),
        "bounded_claim": packet.get("bounded_claim"),
        "expected_command": packet.get("expected_command"),
        "source_ref_count": len(packet.get("source_refs") or []),
        "evidence_ref_count": len(packet.get("evidence_refs") or []),
        "non_claim_count": len(packet.get("non_claims") or []),
        "validation": validation,
        "legacy_receipt_surface": "project_packet",
    }


def _command_plan(
    *,
    project: str,
    rubric: str,
    packet_path: Path | None,
    expected_command: str,
    packet_validation: dict[str, Any],
    source_preflight_validation: dict[str, Any],
) -> list[dict[str, Any]]:
    packet_ref = str(packet_path) if packet_path else "<intake.json>"
    source_preflight = source_preflight_validation.get("source_preflight") or {}
    source_ready = bool(
        source_preflight_validation.get("ok")
        and source_preflight.get("checked")
        and source_preflight.get("ok")
    )
    packet_ready = bool(packet_validation.get("ok"))
    return [
        {
            "phase": "source_and_evidence_prep",
            "work_mode": "pre_kernel_project_prep",
            "ready": source_ready,
            "purpose": (
                "create and type the local source surface before any model-backed "
                "evidence compile or in-loop run"
            ),
            "commands": [
                f"ztare project source-init --project {_quote(project)} --rubric {_quote(rubric)}",
                f"ztare project source-check --project {_quote(project)} --json",
                f"make evidence-prepare PROJECT={_quote(project)} MODEL=gemini",
                f"ztare project intake validate --path {_quote(packet_ref)} --source-preflight",
            ],
        },
        {
            "phase": "read_only_trace",
            "work_mode": "inspection_only",
            "ready": packet_ready,
            "purpose": "inspect intake, source, evidence, graph, and prediction surfaces without running the loop",
            "commands": [
                (
                    f"ztare autoresearch trace --project {_quote(project)} "
                    f"--rubric {_quote(rubric)} --intake {_quote(packet_ref)} --json"
                )
            ],
        },
        {
            "phase": "in_loop_gate",
            "work_mode": "in_loop_autoresearch_gate",
            "ready": packet_ready and source_ready,
            "purpose": "enter autoresearch only after the intake and source preflight are ready",
            "commands": [expected_command],
        },
    ]


def _relative_validation(result: dict[str, Any]) -> dict[str, Any]:
    cleaned = dict(result)
    path = cleaned.get("path")
    if isinstance(path, str):
        try:
            cleaned["path"] = str(Path(path).resolve().relative_to(REPO))
        except ValueError:
            cleaned["path"] = path
    return cleaned


def demo_walkthrough() -> dict[str, Any]:
    ready = _relative_validation(validate_project_packet_path(READY_PACKET))
    malformed = _relative_validation(validate_project_packet_path(MALFORMED_PACKET))
    return {
        "schema": "ztare-project-walkthrough-v1",
        "mode": "demo",
        "writes": [],
        "steps": [
            {
                "name": "validate_ready_packet",
                "canonical_name": "validate_ready_intake",
                "command": f"ztare project intake validate --path {READY_PACKET.relative_to(REPO)}",
                "ok": ready["ok"],
                "result": ready,
            },
            {
                "name": "validate_malformed_packet",
                "canonical_name": "validate_malformed_intake",
                "command": f"ztare project intake validate --path {MALFORMED_PACKET.relative_to(REPO)}",
                "ok": not malformed["ok"],
                "result": malformed,
            },
            {
                "name": "inspect_trace_before_running",
                "command": (
                    "ztare autoresearch trace --project demo_claims --rubric demo_claims "
                    f"--intake {READY_PACKET.relative_to(REPO)} --json"
                ),
                "ok": True,
                "result": {
                    "reason": (
                        "trace is read-only; run it before launching new "
                        "iterations on a real project"
                    )
                },
            },
        ],
        "next_command": (
            "ztare project walkthrough --project <slug> --rubric <slug> "
            "--task '<bounded task>' --bounded-claim '<claim>' "
            "--source-ref <path-or-url> --evidence-ref <path-or-url> "
            "--non-claim '<non-claim>' --next-falsifier '<test>' "
            "--intake-out <intake.json>"
        ),
    }


def ops_demo_walkthrough() -> dict[str, Any]:
    packet_validation = _relative_validation(
        validate_project_packet_path(
            OPS_DEMO_PACKET,
            require_source_preflight=True,
        )
    )
    packet = json.loads(OPS_DEMO_PACKET.read_text(encoding="utf-8"))
    expected_command = str(packet.get("expected_command") or default_expected_command(
        OPS_DEMO_PROJECT,
        OPS_DEMO_RUBRIC,
        str(packet.get("task") or "verify a bounded operational diagnosis"),
    ))
    command_plan = _command_plan(
        project=OPS_DEMO_PROJECT,
        rubric=OPS_DEMO_RUBRIC,
        packet_path=OPS_DEMO_PACKET.relative_to(REPO),
        expected_command=expected_command,
        packet_validation=packet_validation,
        source_preflight_validation=packet_validation,
    )
    for phase in command_plan:
        if phase.get("phase") == "read_only_trace":
            phase["commands"] = [
                (
                    f"ztare autoresearch trace --project {OPS_DEMO_PROJECT} "
                    f"--rubric {OPS_DEMO_RUBRIC} "
                    f"--intake {OPS_DEMO_PACKET.relative_to(REPO)} --brief"
                )
            ]
    return {
        "schema": "ztare-project-walkthrough-v1",
        "mode": "ops_demo",
        "ok": bool(packet_validation.get("ok")),
        "writes": [],
        "project": OPS_DEMO_PROJECT,
        "rubric": OPS_DEMO_RUBRIC,
        "intake": _packet_preview(packet, packet_validation),
        "review_artifact": str(
            (REPO / "projects" / OPS_DEMO_PROJECT / "public" / "CLAIM_SUMMARY.md")
            .relative_to(REPO)
        ),
        "command_plan": command_plan,
        "what_this_demonstrates": [
            "bounded organizational diagnosis over typed local sources",
            "explicit root-cause claim with rivals and non-claims",
            "read-only trace before any model-backed in-loop run",
            "source-claim graph focus on the remaining local verification gaps",
        ],
        "next_commands": [
            f"ztare project source-check --project {OPS_DEMO_PROJECT} --json",
            f"ztare project source-index --project {OPS_DEMO_PROJECT} --json",
            (
                f"ztare project intake validate --path "
                f"{OPS_DEMO_PACKET.relative_to(REPO)} --source-preflight"
            ),
            (
                f"ztare autoresearch trace --project {OPS_DEMO_PROJECT} "
                f"--rubric {OPS_DEMO_RUBRIC} "
                f"--intake {OPS_DEMO_PACKET.relative_to(REPO)} --brief"
            ),
            expected_command + " --preflight-only",
            expected_command,
        ],
    }


def custom_walkthrough(args: argparse.Namespace) -> dict[str, Any]:
    missing = [
        name
        for name in ("project", "rubric", "task", "bounded_claim", "next_falsifier")
        if not getattr(args, name)
    ]
    if missing:
        return {
            "schema": "ztare-project-walkthrough-v1",
            "mode": "custom",
            "ok": False,
            "errors": [f"missing required option: --{name.replace('_', '-')}" for name in missing],
            "next_command": "ztare project walkthrough --demo",
        }

    expected_command = args.expected_command or default_expected_command(
        args.project,
        args.rubric,
        args.task,
    )
    packet_path = Path(args.packet_out).resolve() if args.packet_out else None
    packet_dir = packet_path.parent if packet_path else Path.cwd()
    packet = build_project_packet(
        project=args.project,
        rubric=args.rubric,
        task=args.task,
        bounded_claim=args.bounded_claim,
        source_refs=_portable_local_refs(args.source_ref, packet_dir=packet_dir),
        evidence_refs=_portable_local_refs(args.evidence_ref, packet_dir=packet_dir),
        non_claims=args.non_claim,
        next_falsifier=args.next_falsifier,
        expected_command=expected_command,
        notes=args.notes,
    )

    writes: list[str] = []
    validation = validate_project_packet(
        packet,
        base_dir=packet_path.parent if packet_path else Path.cwd(),
        repo_root=REPO,
    )
    if packet_path:
        write_project_packet(packet_path, packet)
        writes.append(str(packet_path))
        validation = validate_project_packet_path(packet_path)

    source_preflight_validation = (
        validate_project_packet_path(packet_path, require_source_preflight=True)
        if packet_path
        else validate_project_packet(
            packet,
            base_dir=Path.cwd(),
            repo_root=REPO,
            require_source_preflight=True,
        )
    )
    command_plan = _command_plan(
        project=args.project,
        rubric=args.rubric,
        packet_path=packet_path,
        expected_command=expected_command,
        packet_validation=validation,
        source_preflight_validation=source_preflight_validation,
    )
    intake_preview = _packet_preview(packet, validation)

    queued: dict[str, Any] | None = None
    if args.enqueue:
        if not packet_path:
            return {
                "schema": "ztare-project-walkthrough-v1",
                "mode": "custom",
                "ok": False,
                "intake": intake_preview,
                "writes": writes,
                "command_plan": command_plan,
                "errors": ["--enqueue requires --intake-out so the queue has an artifact ref"],
            }
        validation = source_preflight_validation
        intake_preview = _packet_preview(packet, validation)
        if not validation["ok"]:
            return {
                "schema": "ztare-project-walkthrough-v1",
                "mode": "custom",
                "ok": False,
                "intake": intake_preview,
                "writes": writes,
                "command_plan": command_plan,
                "errors": ["refusing to enqueue an intake that does not validate"],
            }
        queue_dir = queue_dir_from_arg(args.queue_dir)
        queued = enqueue_project_packet(
            queue_dir=queue_dir,
            packet_path=packet_path,
            notes="created by ztare project walkthrough",
        )
        writes.append(str(queue_dir / "pending.jsonl"))
        writes.append(str(queue_dir / "events.jsonl"))

    return {
        "schema": "ztare-project-walkthrough-v1",
        "mode": "custom",
        "ok": validation["ok"],
        "intake": intake_preview,
        "writes": writes,
        "queued": queued,
        "command_plan": command_plan,
        "next_commands": [
            f"ztare project intake validate --path {_quote(str(packet_path or '<intake.json>'))}",
            (
                f"ztare autoresearch trace --project {_quote(args.project)} "
                f"--rubric {_quote(args.rubric)} "
                f"--intake {_quote(str(packet_path or '<intake.json>'))} --json"
            ),
            expected_command,
        ],
    }


def render_text(report: dict[str, Any]) -> str:
    lines = ["ZTARE project walkthrough", ""]
    def _append_source_preflight(prefix: str, validation: dict[str, Any]) -> None:
        source_preflight = validation.get("source_preflight") or {}
        if not source_preflight.get("checked"):
            return
        lines.append(
            f"{prefix}source-preflight: {source_preflight.get('status')} "
            f"({source_preflight.get('source_evidence_count', 0)} source evidence, "
            f"{source_preflight.get('untyped_source_count', 0)} untyped)"
        )

    if report["mode"] == "demo":
        lines.append("Demo mode: no writes, current public project-intake fixtures.")
        for step in report["steps"]:
            status = "ok" if step["ok"] else "blocked"
            name = step.get("canonical_name") or step["name"]
            lines.append(f"- {name}: {status}")
            lines.append(f"  command: {step['command']}")
            _append_source_preflight("  ", step.get("result") or {})
            errors = step.get("result", {}).get("errors") or []
            for error in errors:
                lines.append(f"  stop: {error}")
        lines.extend(["", "Next:", f"  {report['next_command']}"])
        return "\n".join(lines)

    if report["mode"] == "ops_demo":
        lines.append("Ops diagnosis demo: no writes, concrete in-loop candidate.")
        lines.append(f"- project/rubric: {report.get('project')} / {report.get('rubric')}")
        packet = report.get("intake") or report.get("packet") or {}
        if packet:
            lines.append(f"- intake id: {packet.get('packet_id')}")
            validation = packet.get("validation") or {}
            _append_source_preflight("- ", validation)
            for error in validation.get("errors", []):
                lines.append(f"- validation stop: {error}")
        demonstrations = report.get("what_this_demonstrates") or []
        if demonstrations:
            lines.append("- demonstrates:")
            lines.extend(f"  {item}" for item in demonstrations)
        review_artifact = report.get("review_artifact")
        if review_artifact:
            lines.append(f"- review artifact: {review_artifact}")
        command_plan = report.get("command_plan") or []
        if command_plan:
            lines.append("- command plan:")
            for phase in command_plan:
                ready = "ready" if phase.get("ready") else "prep-needed"
                lines.append(
                    f"  {phase.get('phase')} [{phase.get('work_mode')}]: {ready}"
                )
                for command in phase.get("commands") or []:
                    lines.append(f"    {command}")
        next_commands = report.get("next_commands") or []
        if next_commands:
            lines.append("- next commands:")
            lines.extend(f"  {command}" for command in next_commands)
        return "\n".join(lines)

    ok = bool(report.get("ok"))
    lines.append("Custom mode: " + ("intake validates" if ok else "intake blocked"))
    for error in report.get("errors", []):
        lines.append(f"- stop: {error}")
    packet = report.get("intake") or report.get("packet") or {}
    if packet:
        lines.append(f"- intake id: {packet.get('packet_id')}")
        lines.append(f"- project/rubric: {packet.get('project')} / {packet.get('rubric')}")
        validation = packet.get("validation") or {}
        _append_source_preflight("- ", validation)
        for error in validation.get("errors", []):
            lines.append(f"- validation stop: {error}")
    writes = report.get("writes") or []
    if writes:
        lines.append("- writes:")
        lines.extend(f"  {path}" for path in writes)
    command_plan = report.get("command_plan") or []
    if command_plan:
        lines.append("- command plan:")
        for phase in command_plan:
            ready = "ready" if phase.get("ready") else "prep-needed"
            lines.append(
                f"  {phase.get('phase')} [{phase.get('work_mode')}]: {ready}"
            )
            for command in phase.get("commands") or []:
                lines.append(f"    {command}")
    next_commands = report.get("next_commands") or []
    if next_commands:
        lines.append("- next commands:")
        lines.extend(f"  {command}" for command in next_commands)
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="run the bundled no-write walkthrough")
    parser.add_argument(
        "--ops-demo",
        action="store_true",
        help="show the concrete operational-diagnosis project walkthrough",
    )
    parser.add_argument("--project")
    parser.add_argument("--rubric")
    parser.add_argument("--task")
    parser.add_argument("--bounded-claim")
    parser.add_argument("--source-ref", action="append", default=[])
    parser.add_argument("--evidence-ref", action="append", default=[])
    parser.add_argument("--non-claim", action="append", default=[])
    parser.add_argument("--next-falsifier")
    parser.add_argument("--expected-command")
    parser.add_argument(
        "--intake-out",
        "--packet-out",
        dest="packet_out",
        help="write the generated project-intake file; --packet-out is a compatibility alias",
    )
    parser.add_argument("--enqueue", action="store_true", help="enqueue source-ready intake")
    parser.add_argument("--queue-dir")
    parser.add_argument("--notes")
    parser.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    has_custom_input = any(
        getattr(args, name)
        for name in (
            "project",
            "rubric",
            "task",
            "bounded_claim",
            "source_ref",
            "evidence_ref",
            "non_claim",
            "next_falsifier",
            "expected_command",
            "packet_out",
            "enqueue",
            "queue_dir",
            "notes",
        )
    )
    if args.ops_demo:
        report = ops_demo_walkthrough()
    else:
        report = demo_walkthrough() if args.demo or not has_custom_input else custom_walkthrough(args)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report))
    return 0 if report.get("ok", True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
