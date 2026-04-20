"""Findings → seed promotion edge for GP-031.

This is the explicit type-change edge Codex Turn 2 required: before
promotion, the object is a findings-debate seam; after promotion, it
is a program seed registered with the M-form supervisor and available
for A1/A2/B/C/D execution through the existing machinery.

The promotion edge is deliberately minimal:

- it does not auto-promote (Option C in GP-031 is rejected; operator
  confirms every promotion)
- it does not decide the target ``SeedPipelineType`` (operator picks)
- it does not write the seed spec itself (operator authors the spec
  at ``spec_path`` before calling this module)
- it only wires a confirmed finding into ``seed_registry.json`` with
  all the invariants the existing seed registry validator expects

After a successful promotion the existing supervisor primitives
(genesis → manifest → A1/A2/B/C/D execution) take over without any
further work in this module.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from src.ztare.common.paths import REPO_ROOT
from src.ztare.supervisor.supervisor_findings_debate import (
    DebateStatus,
    read_debate_state,
)
from src.ztare.supervisor.supervisor_seed_registry import (
    SeedPipelineType,
    SeedStatus,
    load_seed_registry,
    seed_registry_path,
)


@dataclass(frozen=True)
class PromotionRequest:
    """Operator-authored promotion request for a converged findings seam."""

    seam_path: Path
    seed_id: str
    spec_path: str  # repo-root-relative, matching existing registry convention
    pipeline_type: SeedPipelineType
    summary: str
    decision_reason: str
    status: SeedStatus = SeedStatus.ACTIVE


class PromotionError(RuntimeError):
    """Raised when a promotion request is structurally invalid or would
    violate an existing seed-registry invariant."""


def promote_findings_seam(
    request: PromotionRequest,
    *,
    registry_path: Path | None = None,
    allow_unconverged: bool = False,
) -> dict[str, object]:
    """Promote a findings-debate seam into the seed registry.

    Guardrails (fail-closed):

    1. ``seam_path`` must exist.
    2. The seam's debate state must be ``CONVERGED`` unless
       ``allow_unconverged=True`` is passed explicitly. This is the
       one operator-override knob, and it exists because an operator
       may choose to promote a seam that was escalated at the hard cap
       but that they judge converged on inspection (the fail-open
       contract from GP-031 Turn 2).
    3. ``spec_path`` (relative to repo root) must already exist on
       disk. The promotion edge does not author specs; it only records
       them.
    4. ``seed_id`` must not already be present in the registry. This
       module refuses to silently overwrite existing seeds, even
       closed ones — supersession is a separate workflow handled
       outside the promotion edge.
    5. If ``status`` is ``CLOSED``, the request must include a
       ``superseded_by`` field (not yet modeled on
       ``PromotionRequest`` because the promotion edge is only used
       for *new* active seeds in the first slice; closed-on-arrival
       promotions will fail validation).

    On success, writes the new entry to ``seed_registry.json`` and
    returns a dict describing what was written.
    """

    # 1. seam file exists
    if not request.seam_path.exists():
        raise PromotionError(f"seam file not found: {request.seam_path}")

    # 2. convergence gate
    state = read_debate_state(request.seam_path)
    if state.status != DebateStatus.CONVERGED and not allow_unconverged:
        raise PromotionError(
            "seam is not converged (status="
            f"{state.status.value}); pass allow_unconverged=True to "
            "override after operator inspection"
        )

    # 3. spec_path exists on disk
    spec_full = REPO_ROOT / request.spec_path
    if not spec_full.exists():
        raise PromotionError(
            f"spec_path does not exist on disk: {request.spec_path}"
        )

    # 4. seed_id not already present
    target = registry_path or seed_registry_path()
    existing = load_seed_registry(target)
    existing_ids = {entry.seed_id for entry in existing.seeds}
    if request.seed_id in existing_ids:
        raise PromotionError(
            f"seed_id already present in registry: {request.seed_id}"
        )

    # 5. closed-on-arrival promotions are not supported in the first slice
    if request.status == SeedStatus.CLOSED:
        raise PromotionError(
            "closed-on-arrival promotions are not supported; promote as "
            "active/deferred and close via a separate workflow"
        )

    # Write the new entry into the registry JSON, preserving existing
    # seed order and adding the new seed at the end of the map.
    payload = json.loads(target.read_text(encoding="utf-8"))
    seeds_payload: dict[str, dict[str, object]] = payload.setdefault("seeds", {})
    seeds_payload[request.seed_id] = {
        "spec_path": request.spec_path,
        "status": request.status.value,
        "pipeline_type": request.pipeline_type.value,
        "summary": request.summary,
        "decision_reason": request.decision_reason,
        "superseded_by": [],
    }

    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    return {
        "seed_id": request.seed_id,
        "spec_path": request.spec_path,
        "status": request.status.value,
        "pipeline_type": request.pipeline_type.value,
        "registry_path": str(target),
        "seam_path": str(request.seam_path),
        "debate_status_at_promotion": state.status.value,
        "turn_count_at_promotion": state.turn_count,
    }
