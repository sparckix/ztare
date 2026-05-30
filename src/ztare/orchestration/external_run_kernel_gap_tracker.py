"""Kernel-side tracker for external GPU/API run orchestration.

This is not the implementation. It is the durable kernel record of what is
already strong about the current launch/monitor path and what still prevents it
from being treated as a first-class org-runtime primitive.

Context:
    GP163D now has a workable project-local stack:
      - deploy/launch bash
      - remote-side fail-closed batch runner
      - generic remote watchdog
      - local monitor/downloader

The stack is useful and can run real work, but it is not yet kernel-strong.
The remaining gaps are architectural rather than cosmetic.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExternalRunKernelGap:
    gap_id: str
    status: str
    severity: str
    current_state: str
    target_state: str
    why_it_matters: str


CURRENT_STRENGTHS: tuple[str, ...] = (
    "Remote batches can already fail closed instead of silently drifting.",
    "Project launchers package a bounded repo slice and stage it remotely.",
    "Remote logs expose meaningful progress markers such as per-angle and per-boundary transitions.",
    "A generic external watchdog exists for PID/result/progress monitoring.",
    "Artifact bundling on completion already exists for the gp163d invariance path.",
)


OPEN_GAPS: tuple[ExternalRunKernelGap, ...] = (
    ExternalRunKernelGap(
        gap_id="ERK-001-typed-launch-contract",
        status="open",
        severity="high",
        current_state=(
            "External runs are launched through project-local bash plus env vars."
            " Host, remote root, launch command, result files, progress files,"
            " and artifact names are implicit per project."
        ),
        target_state=(
            "A typed kernel-owned launch contract describes host, staging root,"
            " remote command, pid file, progress file, result file, artifact bundle,"
            " and completion semantics in one canonical schema."
        ),
        why_it_matters=(
            "Without a typed contract, every new project recreates its own fragile"
            " bash protocol and every monitor has to rediscover filenames and states."
        ),
    ),
    ExternalRunKernelGap(
        gap_id="ERK-002-transport-split",
        status="open",
        severity="high",
        current_state=(
            "Kernel notifications moved to Telegram, but external-run launchers and"
            " watchdogs still push directly to ntfy.sh."
        ),
        target_state=(
            "External-run monitoring uses the same kernel notification transport as"
            " the rest of org-runtime, with one abstraction for push delivery."
        ),
        why_it_matters=(
            "Split transports mean duplicated failure modes, inconsistent operator"
            " expectations, and project code that bypasses the kernel notification layer."
        ),
    ),
    ExternalRunKernelGap(
        gap_id="ERK-003-local-closure-monitor",
        status="open",
        severity="high",
        current_state=(
            "Remote completion/failure alerts exist, but local download, artifact"
            " extraction, and safe-to-kill acknowledgment are not provided by the"
            " generic kernel path."
        ),
        target_state=(
            "A kernel-owned local closure monitor persists independently, downloads"
            " outputs, verifies expected artifacts, records the local landing path,"
            " and emits a final safe-to-kill signal."
        ),
        why_it_matters=(
            "A remote 'done' message is not enough. The operator needs to know that"
            " the artifacts are actually back on the local machine before terminating"
            " the rented box."
        ),
    ),
    ExternalRunKernelGap(
        gap_id="ERK-004-run-registry",
        status="partial",
        severity="medium",
        current_state=(
            "A kernel-owned registry primitive now exists and the gp163d local monitor"
            " writes contract/state/event records under ztare_workspace/external_runs."
            " But project launchers do not yet register runs generically at launch time,"
            " and other external-run paths do not automatically adopt it."
        ),
        target_state=(
            "Every external run writes a kernel-readable registry record that can be"
            " reattached to by later agents or dashboards."
        ),
        why_it_matters=(
            "Without a run registry, reattachment is manual and cold agents must infer"
            " state from logs, shell history, or chat."
        ),
    ),
    ExternalRunKernelGap(
        gap_id="ERK-005-progress-schema",
        status="open",
        severity="medium",
        current_state=(
            "Progress is exposed mainly through tailing text logs or ad hoc JSONs."
            " There is no shared heartbeat schema for active remote work."
        ),
        target_state=(
            "External runs write a standard machine-readable heartbeat schema with"
            " stage, substage, host, pid, gpu residency, elapsed time, and last-good"
            " artifact pointers."
        ),
        why_it_matters=(
            "Text-tail monitoring works for one project, but it does not scale into"
            " a reusable kernel primitive or dashboard surface."
        ),
    ),
    ExternalRunKernelGap(
        gap_id="ERK-006-supervision-persistence",
        status="open",
        severity="medium",
        current_state=(
            "Persistence of local monitors currently depends on ad hoc tmux/screen/"
            " shell wrapping rather than a kernel-owned supervision path."
        ),
        target_state=(
            "External-run monitors are spawned under a known supervision surface with"
            " explicit reattach, stop, and status operations."
        ),
        why_it_matters=(
            "A monitor that cannot be reliably kept alive is still partially manual,"
            " even if the underlying code is sound."
        ),
    ),
)


PROMOTION_TARGET = (
    "Treat external GPU/API runs as a first-class kernel primitive only after"
    " the launch contract, transport, local closure, registry, progress schema,"
    " and supervision path are unified."
)


def render_gap_summary() -> str:
    lines = ["External-run kernel strengths:"]
    lines.extend(f"- {item}" for item in CURRENT_STRENGTHS)
    lines.append("")
    lines.append("Open external-run kernel gaps:")
    for gap in OPEN_GAPS:
        lines.append(
            f"- {gap.gap_id} [{gap.severity}] {gap.current_state} "
            f"Target: {gap.target_state}"
        )
    lines.append("")
    lines.append(f"Promotion target: {PROMOTION_TARGET}")
    return "\n".join(lines)
