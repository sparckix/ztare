from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


Lane = Literal["skill_acquisition", "meta_hardening", "proof_work", "advisory"]
RunLane = Literal["skill_acquisition", "meta_hardening", "proof_work"]
BlockingPolicy = Literal["blocks_candidate", "blocks_meta_patch", "blocks_proof", "advisory", "audit_only"]
AuthorityLevel = Literal["routing_only", "diagnostic", "gate", "certificate"]
TargetSurface = Literal[
    "candidate",
    "prompt_sensor",
    "workbench_tool",
    "validator_surface",
    "mutable_sensor",
    "strategy",
    "proof",
    "advisory",
    "meta_tool",
]

SKILL_ACQUISITION_LANE: Lane = "skill_acquisition"
META_HARDENING_LANE: Lane = "meta_hardening"
PROOF_WORK_LANE: Lane = "proof_work"
ADVISORY_LANE: Lane = "advisory"

# Compatibility only for cards written before lane became part of card
# identity. New producers must write ``lane`` explicitly.
_LEGACY_SKILL_CARD_KINDS = frozenset(
    {
        "compressed_counterexample_repair",
        "evidence_probe",
        "search_control_residue_repair",
        "horizon_exhaustion_probe",
        "carrier_repair_probe",
    }
)


@dataclass(frozen=True)
class RunContext:
    lane: RunLane = SKILL_ACQUISITION_LANE


@dataclass(frozen=True)
class WorkItemRole:
    lane: Lane
    target_surface: TargetSurface
    blocking_policy: BlockingPolicy
    authority: AuthorityLevel
    gate_command: str = ""
    gate_success_status: str = ""
    target_artifact: str = ""
    mutable_surface: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_control_work_item(item: dict[str, Any]) -> WorkItemRole:
    """Classify a ledger/card/proposal row into a composable control role."""

    item_type = str(item.get("source_type") or item.get("type") or "")
    explicit_lane = str(item.get("lane") or "").strip()
    kind = str(item.get("kind") or "").strip()
    plan = item.get("action_plan") if isinstance(item.get("action_plan"), dict) else {}
    gate = _gate_from_item(item=item, plan=plan)
    target_artifact = str(plan.get("target_artifact") or item.get("target_artifact") or "")
    mutable_surface = str(plan.get("mutable_surface") or item.get("mutable_surface") or "")
    target_surface = str(plan.get("target_surface") or item.get("target_surface") or "")
    gate_command = str(gate.get("command") or "")
    gate_success_status = str(gate.get("success_status") or "")

    if explicit_lane in {SKILL_ACQUISITION_LANE, META_HARDENING_LANE, PROOF_WORK_LANE, ADVISORY_LANE}:
        return _role_from_explicit_lane(
            lane=explicit_lane,  # type: ignore[arg-type]
            target_surface=target_surface,
            gate_command=gate_command,
            gate_success_status=gate_success_status,
            target_artifact=target_artifact,
            mutable_surface=mutable_surface,
        )

    if _is_tool_or_prompt_hardening(kind, gate_command, target_surface, mutable_surface):
        return WorkItemRole(
            lane=META_HARDENING_LANE,
            target_surface=_target_surface_for_meta(
                target_artifact=target_artifact,
                mutable_surface=mutable_surface,
                target_surface=target_surface,
                kind=kind,
            ),
            blocking_policy="blocks_meta_patch",
            authority="routing_only",
            gate_command=gate_command,
            gate_success_status=gate_success_status,
            target_artifact=target_artifact,
            mutable_surface=mutable_surface,
        )

    if _is_proof_work(kind=kind, item_type=item_type, target_surface=target_surface):
        return WorkItemRole(
            lane=PROOF_WORK_LANE,
            target_surface="proof",
            blocking_policy="blocks_proof",
            authority="certificate",
            gate_command=gate_command,
            gate_success_status=gate_success_status,
        )

    if item_type == "strategy_experiment" and kind in _LEGACY_SKILL_CARD_KINDS:
        return WorkItemRole(
            lane=SKILL_ACQUISITION_LANE,
            target_surface="candidate",
            blocking_policy="blocks_candidate",
            authority="gate" if gate_command else "routing_only",
            gate_command=gate_command,
            gate_success_status=gate_success_status,
        )

    return WorkItemRole(
        lane=ADVISORY_LANE,
        target_surface="advisory",
        blocking_policy="advisory",
        authority="diagnostic",
        gate_command=gate_command,
        gate_success_status=gate_success_status,
    )


def should_block(role: WorkItemRole, context: RunContext | None = None) -> bool:
    ctx = context or RunContext()
    if role.blocking_policy == "blocks_candidate":
        return ctx.lane == SKILL_ACQUISITION_LANE
    if role.blocking_policy == "blocks_meta_patch":
        return ctx.lane == META_HARDENING_LANE
    if role.blocking_policy == "blocks_proof":
        return ctx.lane == PROOF_WORK_LANE
    return False


def _gate_from_item(*, item: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    for key in ("required_next_gate", "next_gate"):
        value = item.get(key)
        if isinstance(value, dict):
            return value
    value = plan.get("required_next_gate")
    return value if isinstance(value, dict) else {}


def _is_tool_or_prompt_hardening(
    kind: str,
    gate_command: str,
    target_surface: str,
    mutable_surface: str,
) -> bool:
    if kind == "tool_synthesis":
        return True
    if gate_command == "tool_synthesis_gate":
        return True
    if target_surface in {"prompt_sensor", "workbench_tool", "validator_surface", "mutable_sensor", "meta_tool"}:
        return True
    return bool(mutable_surface)


def _target_surface_for_meta(
    *,
    target_artifact: str,
    mutable_surface: str,
    target_surface: str,
    kind: str,
) -> TargetSurface:
    if target_surface in {"prompt_sensor", "workbench_tool", "validator_surface", "mutable_sensor", "strategy", "meta_tool"}:
        return target_surface  # type: ignore[return-value]
    ref = target_artifact.replace("\\", "/")
    if "briefing" in ref or "prompt" in ref or "submission_path_helpers" in ref:
        return "prompt_sensor"
    if "leaf_workbench" in ref or "visible_workbench" in ref:
        return "workbench_tool"
    if "strategy" in ref:
        return "strategy"
    if mutable_surface:
        return "mutable_sensor"
    return "meta_tool"


def _role_from_explicit_lane(
    *,
    lane: Lane,
    target_surface: str,
    gate_command: str,
    gate_success_status: str,
    target_artifact: str,
    mutable_surface: str,
) -> WorkItemRole:
    if lane == META_HARDENING_LANE:
        return WorkItemRole(
            lane=lane,
            target_surface=_target_surface_for_meta(
                target_artifact=target_artifact,
                mutable_surface=mutable_surface,
                target_surface=target_surface,
                kind="",
            ),
            blocking_policy="blocks_meta_patch",
            authority="routing_only",
            gate_command=gate_command,
            gate_success_status=gate_success_status,
            target_artifact=target_artifact,
            mutable_surface=mutable_surface,
        )
    if lane == PROOF_WORK_LANE:
        return WorkItemRole(
            lane=lane,
            target_surface="proof",
            blocking_policy="blocks_proof",
            authority="certificate",
            gate_command=gate_command,
            gate_success_status=gate_success_status,
            target_artifact=target_artifact,
            mutable_surface=mutable_surface,
        )
    if lane == SKILL_ACQUISITION_LANE:
        return WorkItemRole(
            lane=lane,
            target_surface="candidate",
            blocking_policy="blocks_candidate",
            authority="gate" if gate_command else "routing_only",
            gate_command=gate_command,
            gate_success_status=gate_success_status,
            target_artifact=target_artifact,
            mutable_surface=mutable_surface,
        )
    return WorkItemRole(
        lane=ADVISORY_LANE,
        target_surface="advisory",
        blocking_policy="advisory",
        authority="diagnostic",
        gate_command=gate_command,
        gate_success_status=gate_success_status,
        target_artifact=target_artifact,
        mutable_surface=mutable_surface,
    )


def _is_proof_work(*, kind: str, item_type: str, target_surface: str) -> bool:
    if target_surface == "proof":
        return True
    # Compatibility fallback for older ledgers that predate explicit lanes.
    return "proof" in kind or "lean" in item_type or "lean" in kind
