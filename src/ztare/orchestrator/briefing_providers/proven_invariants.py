"""Proven-invariants briefing provider (ENGINE-level, general).

Fixes the gap the operator named (2026-07-03): a KERNEL-RATIFIED invariant — a
machine-checked theorem about the law — was NOT surfacing to the mutator at
all (it lived only in the worldmodel planner's prediction filter). This
provider reads current, identity-bound rows from
`workspace/invariant_certificates.jsonl` and surfaces them as a HARD constraint
tier.  A theorem about a catalog `specStep` is visible only while that exact
specification and evidence epoch remain the canonical executable subject.
"""

from __future__ import annotations

from pathlib import Path

from ztare.common.invariant_certificate import proven_constraints_briefing
from ztare.orchestrator.mutator_briefing import BriefingContext, BriefingProvider


class ProvenInvariantsProvider(BriefingProvider):
    name = "proven_invariants"

    def _certs(self, project: Path):
        from ztare.worldmodel.carrier_loader import load_carrier_path
        from ztare.worldmodel.lean_bridge import load_current_invariants

        carrier_path = project / "test_model.py"
        if not carrier_path.is_file():
            return []
        try:
            subject, _kind, _sha = load_carrier_path(
                carrier_path,
                project_dir=project,
                attach_projection=False,
            )
        except Exception:  # noqa: BLE001 - an unreadable subject has no authority
            return []
        return load_current_invariants(project, subject=subject)

    def applies(self, ctx: BriefingContext) -> bool:
        return bool(proven_constraints_briefing(self._certs(Path(ctx.project_dir or ""))))

    def fragment(self, ctx: BriefingContext) -> str:
        return proven_constraints_briefing(self._certs(Path(ctx.project_dir)))
