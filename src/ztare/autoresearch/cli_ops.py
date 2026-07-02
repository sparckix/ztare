# SPDX-License-Identifier: MIT
"""Engine helpers for the ``ztare autoresearch run`` verb.

These functions own the computation the dispatcher used to inline:

- ``project_intake_path`` resolves the ``--intake`` / ``--packet`` alias pair.
- ``packet_run_defaults`` extracts launch defaults from a packet's explicit
  ``ztare autoresearch run`` command.
- ``run_packet_blocker`` computes the run-readiness contract message that
  blocks ``--intake`` launches when the kernel-entry contract fails.

The CLI keeps argument parsing and output formatting; this module keeps the
logic. Stdlib-only; the repo root is passed in so these stay pure of CLI
globals.
"""
from __future__ import annotations

import importlib
import json
import shlex
from pathlib import Path

_PACKET_RUN_FLAGS = {
    "--iters",
    "--mutator",
    "--judge",
    "--inverter",
    "--llm-timeout-seconds",
    "--llm-retries",
}


def project_intake_path(kv: dict[str, str]) -> str:
    """Return the preferred project-intake path from CLI aliases.

    ``--intake`` is canonical; ``--packet`` is the legacy alias. Supplying both
    with conflicting values is an error.
    """
    intake = str(kv.get("--intake") or "").strip()
    packet = str(kv.get("--packet") or "").strip()
    if intake and packet and intake != packet:
        raise ValueError(
            "ztare: use either --intake or --packet, not conflicting paths"
        )
    return intake or packet


def _parse_packet_command_flags(tokens: list[str]) -> dict[str, str]:
    """Parse ``--key value`` pairs from a packet command's run flags."""
    out: dict[str, str] = {}
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in _PACKET_RUN_FLAGS and i + 1 < len(tokens):
            out[token] = tokens[i + 1]
            i += 2
        else:
            i += 1
    return out


def packet_run_defaults(packet: str, *, repo_root: Path) -> dict[str, str]:
    """Extract launch defaults from a packet's explicit autoresearch run command."""
    if not packet:
        return {}
    packet_path = Path(packet)
    if not packet_path.is_absolute():
        packet_path = repo_root / packet
    try:
        payload = json.loads(packet_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    command = str(payload.get("expected_command") or "").strip()
    if not command:
        return {}
    try:
        tokens = shlex.split(command)
    except ValueError:
        return {}
    if tokens[:3] != ["ztare", "autoresearch", "run"]:
        return {}
    run_kv = _parse_packet_command_flags(tokens[3:])
    return {
        "ITERS": run_kv.get("--iters", ""),
        "MUTATOR_MODEL": run_kv.get("--mutator", ""),
        "JUDGE_MODEL": run_kv.get("--judge", ""),
        "INVERTER_MODEL": run_kv.get("--inverter", ""),
        "AUTORESEARCH_LLM_TIMEOUT": run_kv.get("--llm-timeout-seconds", ""),
        "AUTORESEARCH_LLM_RETRIES": run_kv.get("--llm-retries", ""),
    }


def run_packet_blocker(
    *, project: str, rubric: str, packet: str, repo_root: Path
) -> str | None:
    """Return a launch-blocking message when packet-backed run readiness fails."""
    trace_module = importlib.import_module("ztare.reports.autoresearch_trace")
    trace = trace_module.build_autoresearch_trace(
        project=project,
        rubric=rubric,
        packet=packet,
        repo=repo_root,
        full_health=False,
    )
    kernel_entry = trace.get("kernel_entry") if isinstance(trace, dict) else {}
    if isinstance(kernel_entry, dict) and kernel_entry.get("can_enter_kernel") is True:
        return None

    readiness_label = (
        kernel_entry.get("readiness_canonical")
        or kernel_entry.get("readiness")
        or trace.get("readiness_canonical")
        or trace.get("readiness")
    )
    lines = [
        "ztare: `autoresearch run --intake` blocked by run-readiness contract",
        f"readiness: {readiness_label}",
    ]
    blockers = kernel_entry.get("blockers") if isinstance(kernel_entry, dict) else []
    if blockers:
        lines.append("blockers:")
        for blocker in blockers:
            if not isinstance(blocker, dict):
                continue
            label = str(blocker.get("canonical_id") or blocker.get("id") or "unknown")
            channel = str(
                blocker.get("canonical_recovery_channel")
                or blocker.get("recovery_channel")
                or "unknown"
            )
            command = str(blocker.get("next_command") or "").strip()
            suffix = f"; next: {command}" if command else ""
            lines.append(f"  - {label} ({channel}){suffix}")
    else:
        missing = trace.get("blocking_missing") if isinstance(trace, dict) else []
        lines.append(f"blocking_missing: {missing}")
    lines.append(
        "Run `ztare autoresearch trace --project "
        f"{project} --rubric {rubric} --intake {packet} --json` for the full contract."
    )
    return "\n".join(lines)
