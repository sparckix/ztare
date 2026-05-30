"""Typed cold-shot family registry and deterministic router.

Cold-shot calls are transient workers, not offices and not truth
authorities. This module owns the routing decision so individual cold-shot
families stay small and do not know about each other.

Phase 1 is deliberately conservative: it records the portfolio decision and
gates the existing GP-169 / GP-184 families. New families can register here
without adding branches to ``autoresearch_loop.py``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable, Literal, Optional


Lifecycle = Literal["pre_iter_1", "post_run", "frontier_planning"]
ColdShotMode = Literal["off", "observe", "advisory", "authoritative"]


@dataclass(frozen=True)
class ColdShotFamily:
    family_id: str
    lifecycle: Lifecycle
    purpose: str
    output_schema: str
    artifact_name: str
    briefing_tier: str = ""
    mutator_visible: bool = False
    claim_class: str = ""

    def to_record(self) -> dict[str, Any]:
        return {
            "family_id": self.family_id,
            "lifecycle": self.lifecycle,
            "purpose": self.purpose,
            "output_schema": self.output_schema,
            "artifact_name": self.artifact_name,
            "briefing_tier": self.briefing_tier,
            "mutator_visible": self.mutator_visible,
            "claim_class": self.claim_class,
        }


FAMILY_REGISTRY: dict[str, ColdShotFamily] = {
    "de_anchor_seed": ColdShotFamily(
        family_id="de_anchor_seed",
        lifecycle="pre_iter_1",
        purpose="Cross-domain/Erdos seed from an anonymized fingerprint.",
        output_schema="cold_llm_seed_candidates.v1",
        artifact_name="cold_llm_seed_iter0.json",
        briefing_tier="T4",
        mutator_visible=True,
        claim_class="cold_discovery_deanchored",
    ),
    "structural_seed": ColdShotFamily(
        family_id="structural_seed",
        lifecycle="pre_iter_1",
        purpose="Problem-specific structural family under gates, not physics by default.",
        output_schema="cold_shot_structural_seed.v1",
        artifact_name="structural_cold_shot_seed.json",
        briefing_tier="T1",
        mutator_visible=True,
        claim_class="architecture_guided_discovery",
    ),
    "physics_lagrangian_seed": ColdShotFamily(
        family_id="physics_lagrangian_seed",
        lifecycle="pre_iter_1",
        purpose="Domain/action-principle seed for dimensional or variational substrates.",
        output_schema="cold_shot_lagrangian_seed.v1",
        artifact_name="cold_shot_seed.json",
        briefing_tier="T1",
        mutator_visible=True,
        claim_class="expert_assisted_mechanism_search",
    ),
    "qualitative_evidence_seed": ColdShotFamily(
        family_id="qualitative_evidence_seed",
        lifecycle="pre_iter_1",
        purpose=(
            "Evidence-grounded thesis family generation: gives the cold LLM full "
            "substrate context (evidence brief + current weakest point + rubric gates) "
            "and asks for 3 thesis families that resolve the weakest point. Complements "
            "de_anchor_seed (cross-domain novelty) with domain-aware structural honesty. "
            "Disabled automatically on numerical substrates."
        ),
        output_schema="qualitative_evidence_seed.v1",
        artifact_name="qualitative_evidence_cold_shot.json",
        briefing_tier="T2",
        mutator_visible=True,
        claim_class="evidence_grounded_thesis_family",
    ),
    "discriminator": ColdShotFamily(
        family_id="discriminator",
        lifecycle="post_run",
        purpose="Post-run next-test / kill-shot proposal.",
        output_schema="discriminator_proposal.v2",
        artifact_name="next_discriminator_queue.jsonl",
        mutator_visible=False,
        claim_class="promotion_support_after_closure",
    ),
    "frontier_script_scaffold": ColdShotFamily(
        family_id="frontier_script_scaffold",
        lifecycle="frontier_planning",
        purpose="Scaffold scripts/public/checklists for expensive GPU/API tests.",
        output_schema="frontier_script_scaffold.v2",
        artifact_name="frontier_script_scaffold.json",
        mutator_visible=False,
        claim_class="instrument_repair_launch_hygiene",
    ),
}


@dataclass
class ColdShotFamilyDecision:
    family_id: str
    lifecycle: Lifecycle
    eligible: bool
    selected: bool
    mode: ColdShotMode
    reason: str
    artifact_name: str
    output_schema: str
    mutator_visible: bool
    consumption_ack: str = "not_consumed"

    def to_record(self) -> dict[str, Any]:
        return {
            "family_id": self.family_id,
            "lifecycle": self.lifecycle,
            "eligible": self.eligible,
            "selected": self.selected,
            "mode": self.mode,
            "reason": self.reason,
            "artifact_name": self.artifact_name,
            "output_schema": self.output_schema,
            "mutator_visible": self.mutator_visible,
            "consumption_ack": self.consumption_ack,
        }


@dataclass
class ColdShotPolicyDecision:
    project: str
    lifecycle: Lifecycle
    mode: ColdShotMode
    generated_utc: str
    selected_families: list[str] = field(default_factory=list)
    decisions: list[ColdShotFamilyDecision] = field(default_factory=list)
    router_reason: str = "deterministic"

    def family_selected(self, family_id: str) -> bool:
        return family_id in self.selected_families

    def to_record(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "project": self.project,
            "lifecycle": self.lifecycle,
            "mode": self.mode,
            "generated_utc": self.generated_utc,
            "router_reason": self.router_reason,
            "selected_families": list(self.selected_families),
            "families": [d.to_record() for d in self.decisions],
        }


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _policy_block(rubric_data: dict[str, Any]) -> dict[str, Any]:
    block = rubric_data.get("cold_shot") or {}
    return block if isinstance(block, dict) else {}


def _mode(rubric_data: dict[str, Any]) -> ColdShotMode:
    raw = str(_policy_block(rubric_data).get("mode") or "advisory").strip().lower()
    if raw in {"off", "observe", "advisory", "authoritative"}:
        return raw  # type: ignore[return-value]
    return "advisory"


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(x).strip() for x in value if str(x).strip()]


def _rubric_modes(rubric_data: dict[str, Any]) -> set[str]:
    modes: set[str] = set()
    primary = rubric_data.get("rubric_mode")
    if isinstance(primary, str) and primary.strip():
        modes.add(primary.strip().lower())
    secondary = rubric_data.get("rubric_modes")
    if isinstance(secondary, list):
        for item in secondary:
            if isinstance(item, str) and item.strip():
                modes.add(item.strip().lower())
    return modes


def _lifecycle_families(lifecycle: Lifecycle) -> Iterable[ColdShotFamily]:
    return (f for f in FAMILY_REGISTRY.values() if f.lifecycle == lifecycle)


def _family_eligibility(
    family_id: str,
    rubric_data: dict[str, Any],
    lifecycle: Lifecycle,
) -> tuple[bool, str]:
    modes = _rubric_modes(rubric_data)
    cage_meta = rubric_data.get("cage_meta") or {}
    substrate_class = str(cage_meta.get("class") or "").strip()

    if family_id == "de_anchor_seed":
        ok = bool(rubric_data.get("enable_cold_llm_erdos_seed", False))
        return ok, "enable_cold_llm_erdos_seed=true" if ok else "enable_cold_llm_erdos_seed=false"

    if family_id == "structural_seed":
        ok = bool(rubric_data.get("enable_problem_structural_cold_shot", False))
        return ok, (
            "enable_problem_structural_cold_shot=true"
            if ok else "structural_seed registered but opt-in flag is false"
        )

    if family_id == "physics_lagrangian_seed":
        explicit = bool(rubric_data.get("enable_cold_shot_seed", False))
        variational = bool(rubric_data.get("enable_lagrangian_derivation", False))
        invariant = "invariant_search" in modes
        ok = explicit and (variational or invariant)
        if ok:
            return True, "enable_cold_shot_seed=true and lagrangian/invariant mode active"
        if explicit:
            return False, "enable_cold_shot_seed=true but no lagrangian/invariant mode"
        return False, f"not routed for substrate_class={substrate_class or 'unknown'}"

    if family_id == "qualitative_evidence_seed":
        opt_in = bool(rubric_data.get("enable_qualitative_evidence_cold_shot", False))
        if not opt_in:
            return False, "enable_qualitative_evidence_cold_shot=false (opt-in required)"
        # Hard-disable on numerical substrates: evidence cold shot is prose-thesis only.
        is_numerical = (
            bool(rubric_data.get("enable_fit_primitive", True))
            and rubric_data.get("rubric_mode") not in ("kepler", "calibration")
            and rubric_data.get("falsification_mode") not in (
                "qualitative_thesis", "qualitative_audit"
            )
        )
        if is_numerical:
            return False, "qualitative_evidence_seed disabled on numerical substrates"
        return True, "enable_qualitative_evidence_cold_shot=true, qualitative substrate"

    if family_id == "discriminator":
        ok = bool(rubric_data.get("enable_cold_shot_discriminator", False))
        return ok, (
            "enable_cold_shot_discriminator=true"
            if ok else "post-run discriminator opt-in flag is false"
        )

    if family_id == "frontier_script_scaffold":
        ok = bool(rubric_data.get("enable_frontier_script_scaffold", False))
        return ok, (
            "enable_frontier_script_scaffold=true"
            if ok else "frontier_script_scaffold opt-in flag is false"
        )

    return False, "unknown family"


def route_cold_shot_families(
    *,
    project: str,
    rubric_data: dict[str, Any],
    lifecycle: Lifecycle,
) -> ColdShotPolicyDecision:
    """Return deterministic cold-shot routing decision for a lifecycle."""
    mode = _mode(rubric_data)
    policy = _policy_block(rubric_data)
    force = set(_string_list(policy.get("force_families")))
    disabled = set(_string_list(policy.get("disabled_families")))

    decisions: list[ColdShotFamilyDecision] = []
    selected: list[str] = []

    for family in _lifecycle_families(lifecycle):
        eligible, reason = _family_eligibility(family.family_id, rubric_data, lifecycle)
        if family.family_id in force:
            eligible = True
            reason = f"forced by cold_shot.force_families ({reason})"
        if family.family_id in disabled:
            selected_flag = False
            reason = f"disabled by cold_shot.disabled_families ({reason})"
        elif mode == "off":
            selected_flag = False
            reason = f"cold_shot.mode=off ({reason})"
        else:
            selected_flag = bool(eligible)

        if selected_flag:
            selected.append(family.family_id)

        decisions.append(ColdShotFamilyDecision(
            family_id=family.family_id,
            lifecycle=family.lifecycle,
            eligible=eligible,
            selected=selected_flag,
            mode=mode,
            reason=reason,
            artifact_name=family.artifact_name,
            output_schema=family.output_schema,
            mutator_visible=family.mutator_visible,
            consumption_ack="selected_not_yet_consumed" if selected_flag else "not_selected",
        ))

    return ColdShotPolicyDecision(
        project=project,
        lifecycle=lifecycle,
        mode=mode,
        generated_utc=_now_utc(),
        selected_families=selected,
        decisions=decisions,
    )


def write_policy_artifacts(
    *,
    workspace_dir: Path,
    decision: ColdShotPolicyDecision,
    event: str = "policy_decision",
) -> Path:
    """Persist routing decision and append an observability row."""
    workspace_dir.mkdir(parents=True, exist_ok=True)
    policy_path = workspace_dir / "cold_shot_policy.json"
    policy_path.write_text(
        json.dumps(decision.to_record(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    row = {
        "timestamp": decision.generated_utc,
        "event": event,
        "project": decision.project,
        "lifecycle": decision.lifecycle,
        "mode": decision.mode,
        "router_reason": decision.router_reason,
        "selected_families": decision.selected_families,
        "families": [d.to_record() for d in decision.decisions],
    }
    with (workspace_dir / "cold_shot_runs.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
    return policy_path


def family_selected(
    *,
    family_id: str,
    project: str,
    rubric_data: dict[str, Any],
    lifecycle: Lifecycle,
    workspace_dir: Optional[Path] = None,
) -> bool:
    """Convenience guard for existing call sites."""
    decision = route_cold_shot_families(
        project=project,
        rubric_data=rubric_data,
        lifecycle=lifecycle,
    )
    if workspace_dir is not None:
        write_policy_artifacts(workspace_dir=workspace_dir, decision=decision)
    return decision.family_selected(family_id)

