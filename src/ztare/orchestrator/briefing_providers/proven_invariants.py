"""Proven-invariants briefing provider (ENGINE-level, general).

Fixes the gap the operator named (2026-07-03): a KERNEL-RATIFIED invariant — a
machine-checked theorem about the law — was NOT surfacing to the mutator at
all (it lived only in the worldmodel planner's prediction filter). This
provider reads any project's `workspace/invariant_certificates.jsonl`, keeps
only kernel-ratified entries, and surfaces them as a HARD constraint tier —
stronger than the survived-N-runs derived constraints. General: any substrate
(fit monotonicity, PDE conservation, worldmodel dynamics) that proves an
invariant gets it enforced in identification.
"""

from __future__ import annotations

import json
from pathlib import Path

from ztare.common.invariant_certificate import (
    InvariantCertificate, proven_constraints_briefing)
from ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider


class ProvenInvariantsProvider(BriefingProvider):
    name = "proven_invariants"

    def _certs(self, project: Path):
        path = project / "workspace" / "invariant_certificates.jsonl"
        if not path.exists():
            return []
        out = []
        for line in path.read_text().splitlines():
            try:
                d = json.loads(line)
                out.append(InvariantCertificate(tuple(d["quantity"]), d["relation"],
                                                d["status"], d.get("theorem", "")))
            except Exception:  # noqa: BLE001
                continue
        return out

    def applies(self, ctx: BriefingContext) -> bool:
        return bool(proven_constraints_briefing(self._certs(Path(ctx.project_dir or ""))))

    def fragment(self, ctx: BriefingContext) -> str:
        return proven_constraints_briefing(self._certs(Path(ctx.project_dir)))
