"""Execution-route classifier for role-daemon tasks.

The daemon should not rely on a spawned agent to intuit whether a work item
belongs in direct work, expert review, artifact construction, or a repeatable
experiment loop. This module is deliberately small: it turns task
frontmatter + body into a typed routing contract the runtime must obey or
explicitly override.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


ROUTES = {
    "route_only",
    "direct_work",
    "expert_review",
    "synthesis_review",
    "scripted_run",
    "artifact_build",
    "experiment_loop",
    "docs_records",
    # RD-1.12 (2026-05-02): research_director's standard route. Live
    # co-drive — RD reads iter outputs, mutates substrate (evidence /
    # charter / rubric), forks successor projects, queues cold-shots, and
    # writes Lean cages from verified axioms. Subject to per-action budget
    # gates (spend_tracker + agent_utilization_tracker) and damage-signal
    # audit. Does NOT bypass safety rails; bypasses only the prior policy
    # ceiling that constrained RD to route_only handoff specs.
    "frontier_co_drive",
}
ROUTE_ALIASES = {
    # Backward-compatible / domain-specific local names. Product-facing org
    # primitives should use the generic route names above.
    "manual_agent": "direct_work",
    "cold_shot": "expert_review",
    "deanchored_synthesis": "synthesis_review",
    "big_picture": "synthesis_review",
    "script_or_gpu": "scripted_run",
    "substrate_build": "artifact_build",
    "ztare_loop": "experiment_loop",
    "paper_or_docs": "docs_records",
    "live_co_drive": "frontier_co_drive",
    "live_codrive": "frontier_co_drive",
    "rd_live": "frontier_co_drive",
}


@dataclass(frozen=True)
class ExecutionRoute:
    route: str
    confidence: str
    rationale: str
    ztare_allowed: bool
    experiment_loop_allowed: bool
    artifact_build_allowed: bool
    substrate_build_allowed: bool
    live_api_allowed: bool
    gpu_allowed: bool
    required_first_artifact: str
    escalation: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "route": self.route,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "ztare_allowed": self.ztare_allowed,
            "experiment_loop_allowed": self.experiment_loop_allowed,
            "artifact_build_allowed": self.artifact_build_allowed,
            "substrate_build_allowed": self.substrate_build_allowed,
            "live_api_allowed": self.live_api_allowed,
            "gpu_allowed": self.gpu_allowed,
            "required_first_artifact": self.required_first_artifact,
            "escalation": self.escalation,
        }


def _bool_frontmatter(fm: dict[str, Any], key: str, default: bool) -> bool:
    if key not in fm:
        return default
    value = fm.get(key)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _explicit_route(fm: dict[str, Any]) -> str | None:
    for key in ("execution_route", "route_hint", "recommended_route"):
        value = str(fm.get(key) or "").strip()
        if value:
            value = ROUTE_ALIASES.get(value, value)
            if value not in ROUTES:
                raise ValueError(
                    f"unknown execution route {value!r}; expected one of {sorted(ROUTES)}"
                )
            return value
    return None


def infer_execution_route(
    *,
    frontmatter: dict[str, Any] | None = None,
    body: str = "",
    role_id: str = "manager",
) -> ExecutionRoute:
    """Infer the cheapest safe execution route for a task.

    Explicit frontmatter wins. Heuristics are intentionally conservative:
    absent a stable contract, default to manual-agent routing rather than
    launching ZTARE or paid infrastructure.
    """
    fm = dict(frontmatter or {})
    text = f"{body}\n{fm}".lower()
    explicit = _explicit_route(fm)

    # RD-1.12 (2026-05-02): research_director's STANDARD route is live
    # co-drive (frontier_co_drive). The prior route_only ceiling was
    # explicitly retired per principal authorization 2026-05-02
    # ("WE DONT NEED TO RESTRICT CO DRIVE, THAT SHOULD BE STANDARD
    # OPERATING WAY"). RD still respects budget gates + damage signals
    # + audit trail at execution time; only the policy ceiling shifts.
    rd_default_co_drive = (
        role_id == "research_director"
        and not explicit
        and not _bool_frontmatter(fm, "rd_co_drive_disabled", False)
    )

    if explicit:
        route = explicit
        confidence = "frontmatter"
        rationale = f"task frontmatter selected {route}"
    elif rd_default_co_drive:
        route = "frontier_co_drive"
        confidence = "role_default"
        rationale = "RD-1.12: research_director defaults to live frontier co-drive"
    elif any(
        k in text
        for k in (
            "de-anchor",
            "deanchor",
            "big picture",
            "10k view",
            "10000-foot",
            "10,000-foot",
            "alien math",
            "meta pattern",
            "proof object",
            "hiding in plain sight",
        )
    ):
        route = "synthesis_review"
        confidence = "medium"
        rationale = "task asks for RD-1.10 de-anchored synthesis before more local slicing"
    elif "generate_substrate" in text or "substrate" in text and "ztare" in text:
        route = "artifact_build"
        confidence = "medium"
        rationale = "task discusses building a reusable artifact/contract for a repeatable loop"
    elif "ztare" in text and any(k in text for k in ("experiment-loop", "make loop", "mutator", "gate_harness", "many candidate")):
        route = "experiment_loop"
        confidence = "medium"
        rationale = "task names the inner ZTARE loop and repeatable gated candidate search"
    elif any(k in text for k in ("gpu", "jax", "nohup", "ssh", "solver", "simulation", "batch")):
        route = "scripted_run"
        confidence = "medium"
        rationale = "task requires one-off scripted or external-compute orchestration"
    elif any(k in text for k in ("cold-shot", "cold shot", "gemini", "gpt-5", "llm api")):
        route = "expert_review"
        confidence = "medium"
        rationale = "task calls for adversarial interpretation or expert review"
    elif any(k in text for k in ("paper", "ssrn", "readme", "docs", "ledger", "manual")):
        route = "docs_records"
        confidence = "medium"
        rationale = "task is primarily prose, public/private sync, or recording"
    else:
        route = "direct_work"
        confidence = "low"
        rationale = "no stable execution contract detected; use operator-agent/manual exploration first"

    # Frontmatter can narrow permissions. Defaults are route-derived and
    # intentionally conservative for paid or contaminating operations.
    # frontier_co_drive (RD-1.12) authorizes the union of experiment_loop +
    # artifact_build + expert_review + scripted_run, gated only by USD/agent-
    # utilization budgets at execution time (not by the routing layer).
    is_co_drive = route == "frontier_co_drive"
    experiment_loop_allowed = (route == "experiment_loop") or is_co_drive
    ztare_allowed = experiment_loop_allowed
    artifact_build_allowed = (route == "artifact_build") or is_co_drive
    substrate_allowed = artifact_build_allowed
    live_api_allowed = (route == "expert_review") or is_co_drive
    gpu_allowed = (route == "scripted_run") or is_co_drive

    experiment_loop_allowed = _bool_frontmatter(fm, "experiment_loop_allowed", experiment_loop_allowed)
    ztare_allowed = _bool_frontmatter(fm, "ztare_allowed", ztare_allowed)
    artifact_build_allowed = _bool_frontmatter(fm, "artifact_build_allowed", artifact_build_allowed)
    substrate_allowed = _bool_frontmatter(fm, "substrate_build_allowed", substrate_allowed)
    live_api_allowed = _bool_frontmatter(fm, "live_api_allowed", live_api_allowed)
    gpu_allowed = _bool_frontmatter(fm, "gpu_allowed", gpu_allowed)

    first_artifact = str(fm.get("required_first_artifact") or "").strip()
    if not first_artifact:
        first_artifact = {
            "route_only": "workspace/execution_route_decision.md",
            "direct_work": "workspace/execution_route_decision.md",
            "expert_review": "workspace/expert_review_packet.md",
            "synthesis_review": "workspace/deanchored_synthesis_checkpoint.md",
            "scripted_run": "workspace/run_packet.md",
            "artifact_build": "workspace/artifact_build_spec.md",
            "experiment_loop": "workspace/preflight_substrate_audit.md",
            "docs_records": "workspace/doc_edit_plan.md",
            "frontier_co_drive": "workspace/frontier_co_drive_log.md",
        }[route]

    escalation = str(fm.get("route_escalation") or "").strip()
    if not escalation:
        if route == "experiment_loop":
            escalation = "If preflight fails or no sealed gates exist, do not launch; write an artifact_build task."
        elif route == "artifact_build":
            escalation = "Director roles may specify the artifact, but implementation must be assigned to an authorized builder role."
        elif route == "synthesis_review":
            escalation = "Write the de-anchored synthesis checkpoint before recommending paid API/GPU or another ZTARE iteration."
        elif route in {"expert_review", "scripted_run"}:
            escalation = "Escalate before live spend above the task budget cap or if static replay can answer the question."
        else:
            escalation = "Escalate if the task requires paid API/GPU, substrate mutation, or ZTARE launch not explicitly allowed."

    # The Research Director is a reviewer/director by mandate, not the entity
    # that silently edits substrates or runs the inner loop.
    if role_id == "research_director" and route in {"artifact_build", "experiment_loop"}:
        rationale += "; research_director must produce a handoff spec, not perform this route directly"

    return ExecutionRoute(
        route=route,
        confidence=confidence,
        rationale=rationale,
        ztare_allowed=ztare_allowed,
        experiment_loop_allowed=experiment_loop_allowed,
        artifact_build_allowed=artifact_build_allowed,
        substrate_build_allowed=substrate_allowed,
        live_api_allowed=live_api_allowed,
        gpu_allowed=gpu_allowed,
        required_first_artifact=first_artifact,
        escalation=escalation,
    )


def render_route_contract(route: ExecutionRoute) -> str:
    """Render a compact prompt block for spawned role agents."""
    return (
        "EXECUTION ROUTE CONTRACT\n"
        f"- route: {route.route}\n"
        f"- confidence: {route.confidence}\n"
        f"- rationale: {route.rationale}\n"
        f"- experiment_loop_allowed: {str(route.experiment_loop_allowed).lower()}\n"
        f"- ztare_allowed: {str(route.ztare_allowed).lower()}\n"
        f"- artifact_build_allowed: {str(route.artifact_build_allowed).lower()}\n"
        f"- substrate_build_allowed: {str(route.substrate_build_allowed).lower()}\n"
        f"- live_api_allowed: {str(route.live_api_allowed).lower()}\n"
        f"- gpu_allowed: {str(route.gpu_allowed).lower()}\n"
        f"- required_first_artifact: {route.required_first_artifact}\n"
        f"- escalation: {route.escalation}\n"
        "- rule: prefer an existing repo command or Python entrypoint before authoring a new one.\n"
        "- rule: write or update the required_first_artifact before executing the route.\n"
        "- rule: if you disagree with the inferred route, write the override rationale first; do not silently switch modes.\n"
    )
