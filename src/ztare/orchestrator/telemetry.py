"""GP-157 v5.0 Phase 4b — orchestrator telemetry primitives.

Karpathy "extract what's already a primitive": JSONL append, Cage
engagement emit, iteration-start event. Keep this file <200 lines —
each helper one-shot, no hidden state, takes IterContext as input.

Consumers today (after Phase 4a step 2):
  - autoresearch_loop.py main loop, Cage observe-mode block.

Consumers planned (after Phase 3c authoritative flip + Phase 4b full):
  - per-iteration telemetry emit (mutator/judge usage, score deltas).
  - gate-engagement matrix as Cage gates migrate to authoritative run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ztare.orchestrator.iter_context import IterContext


@dataclass(frozen=True)
class CageEngagementRecord:
    """Single per-iter Cage engagement entry, JSONL-emitted.

    Mirrors the inline payload that lived in autoresearch_loop.py before
    Phase 4b. Each field maps 1:1 to a key in the JSONL line, so existing
    log-readers do not need to change.
    """
    iter: int
    utc: str
    substrate_meta_valid: bool
    substrate_meta_diagnostics: list[str]
    topo_order: list[str]
    engagements: dict[str, dict[str, Any]]
    engaged_count: int
    engaged: list[str]

    def to_jsonl_line(self) -> str:
        return json.dumps(
            {
                "iter": self.iter,
                "utc": self.utc,
                "substrate_meta_valid": self.substrate_meta_valid,
                "substrate_meta_diagnostics": self.substrate_meta_diagnostics,
                "topo_order": self.topo_order,
                "engagements": self.engagements,
                "engaged_count": self.engaged_count,
                "engaged": self.engaged,
            }
        )


def append_jsonl(path: Path, line: str) -> None:
    """Append one JSON line to `path` with a trailing newline.

    Single seam for telemetry emission so future tests can capture
    output without mocking the global file handle. Per Linus: the bug
    you can grep for is the bug you can fix.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def emit_cage_engagement(
    ctx: IterContext,
    *,
    utc: str,
    engagement_matrix: Any,
) -> CageEngagementRecord:
    """Build + emit a CageEngagementRecord from a Cage dispatch result.

    `engagement_matrix` is the object returned by Cage.dispatch (typed
    `EngagementMatrix` in src/ztare/gates/cage.py). Imported lazily by
    the caller so this module stays free of Cage dependencies.
    """
    engaged = sorted(
        name for name, (ok, _r) in engagement_matrix.engagements.items() if ok
    )
    record = CageEngagementRecord(
        iter=ctx.iteration_index + 1,
        utc=utc,
        substrate_meta_valid=bool(engagement_matrix.substrate_meta_valid),
        substrate_meta_diagnostics=list(engagement_matrix.substrate_meta_diagnostics),
        topo_order=list(engagement_matrix.topo_order),
        engagements={
            name: {"ok": bool(ok), "reason": reason}
            for name, (ok, reason) in engagement_matrix.engagements.items()
        },
        engaged_count=len(engaged),
        engaged=engaged,
    )
    append_jsonl(ctx.cage_engagement_log_path(), record.to_jsonl_line())
    return record


def format_cage_observe_summary(record: CageEngagementRecord, mode: str = "observe") -> str:
    """One-line console summary of an engagement record. `mode` is one of
    "observe" / "authoritative" — labels the banner so the trace doesn't
    say observe-mode after authoritative dispatch landed."""
    label = "AUTHORITATIVE" if mode == "authoritative" else "observe-mode"
    verb = "engaged" if mode == "authoritative" else "would engage"
    if not record.substrate_meta_valid:
        return (
            f"🦴 v5 Cage {label}: substrate.meta INVALID — "
            f"diagnostics: {record.substrate_meta_diagnostics[:3]}"
        )
    suffix = "…" if len(record.engaged) > 5 else ""
    return (
        f"🦴 v5 Cage {label}: {record.engaged_count}/{len(record.topo_order)} gates "
        f"{verb} on this iter ({record.engaged[:5]}{suffix})"
    )
