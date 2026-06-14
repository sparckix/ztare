"""RD helper for deciding when to invoke autoresearch as a workbench.

The research director is the persistent external agent. This module keeps that
role from bypassing the in-loop workbench when the task has the right shape:
bounded claim, stable evaluator, and a rubric surface that can turn work into
ratified artifacts.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal


Decision = Literal["invoke_autoresearch", "prepare_autoresearch_surface", "stay_out_of_loop"]
REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class WorkbenchRoutingDecision:
    decision: Decision
    confidence: float
    reasons: list[str]
    missing: list[str]
    suggested_next_step: str
    task: str = ""
    project: str = ""
    rubric: str = ""
    bounded_claim: bool = False
    stable_evaluator: bool = False
    rubric_ready: bool = False
    artifact_surface: bool = False
    subscription_worker_available: bool = False
    worker_metadata: dict[str, str] = field(default_factory=dict)
    surface_scaffold: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


SURFACE_SCAFFOLDS: dict[str, dict] = {
    "bounded claim/eigenquestion": {
        "surface": "bounded_claim",
        "artifact": "workspace/autoresearch_bounded_claim.md",
        "required_fields": [
            "claim",
            "eigenquestion",
            "discriminating_test",
            "success_criterion",
            "kill_condition",
        ],
        "acceptance_check": "a judge can tell pass/fail without inventing the target",
    },
    "stable evaluator/gate": {
        "surface": "stable_evaluator",
        "artifact": "test_model.py or gate_harness.py",
        "required_fields": [
            "deterministic_input",
            "scoring_or_gate_function",
            "heldout_or_negative_control",
            "failure_mode",
        ],
        "acceptance_check": "same artifact produces the same pass/fail signal across runs",
    },
    "rubric surface": {
        "surface": "rubric",
        "artifact": "rubrics/<project>.json",
        "required_fields": [
            "dimensions_or_criteria",
            "score_contract",
            "falsification_mode_or_hard_gate",
            "minimum_acceptance_threshold",
        ],
        "acceptance_check": "the autoresearch loop can score proposals without RD interpretation",
    },
    "artifact surface": {
        "surface": "artifact",
        "artifact": "current_iteration.md or thesis.md",
        "required_fields": [
            "mutable_claim_text",
            "evidence_refs",
            "known_failures",
            "projection_or_iteration_output_path",
        ],
        "acceptance_check": "mutator can edit the claim and projection can point to the result",
    },
}


def _surface_scaffold(missing: list[str], *, project: str, rubric: str) -> list[dict]:
    scaffold: list[dict] = []
    project_slug = project or "<project>"
    rubric_slug = rubric or project or "<rubric>"
    for item in missing:
        spec = dict(SURFACE_SCAFFOLDS.get(item, {}))
        if not spec:
            continue
        artifact = str(spec["artifact"])
        artifact = artifact.replace("<project>", project_slug)
        artifact = artifact.replace("rubrics/<project>.json", f"rubrics/{rubric_slug}.json")
        spec["artifact"] = artifact
        spec["missing"] = item
        spec["project"] = project_slug
        scaffold.append(spec)
    return scaffold


def _worker_metadata_for_decision(
    decision: Decision,
    *,
    subscription_worker_available: bool,
) -> dict[str, str]:
    if decision == "invoke_autoresearch":
        if subscription_worker_available:
            return {
                "worker_archetype": "fungible_agent_worker",
                "worker_capability": "tool_using_agent",
                "worker_state": "stateless_externalized_briefing",
                "worker_identity": "fungible",
                "transport": "subscription_cli",
                "worker_metadata_source": "autoresearch_workbench_router",
            }
        return {
            "worker_archetype": "fungible_llm_call",
            "worker_capability": "bare_llm_call",
            "worker_state": "stateless_externalized_briefing",
            "worker_identity": "fungible",
            "transport": "api",
            "worker_metadata_source": "autoresearch_workbench_router",
        }
    return {
        "worker_archetype": "persistent_agent",
        "worker_capability": "tool_using_agent",
        "worker_state": "stateful",
        "worker_identity": "persistent",
        "transport": "subscription_cli",
        "worker_metadata_source": "autoresearch_workbench_router",
    }


def route_autoresearch_workbench(
    task: str,
    *,
    stable_evaluator: bool,
    bounded_claim: bool,
    rubric_ready: bool,
    artifact_surface: bool,
    subscription_worker_available: bool = False,
    project: str = "",
    rubric: str = "",
) -> WorkbenchRoutingDecision:
    """Return an RD routing decision for the autoresearch workbench."""
    reasons: list[str] = []
    missing: list[str] = []
    if bounded_claim:
        reasons.append("bounded claim surface")
    else:
        missing.append("bounded claim/eigenquestion")
    if stable_evaluator:
        reasons.append("stable evaluator or deterministic gate")
    else:
        missing.append("stable evaluator/gate")
    if rubric_ready:
        reasons.append("rubric can encode success/failure")
    else:
        missing.append("rubric surface")
    if artifact_surface:
        reasons.append("artifact surface is available for mutation/projection")
    else:
        missing.append("artifact surface")
    if subscription_worker_available:
        reasons.append("subscription-backed fungible worker available")

    if stable_evaluator and bounded_claim and rubric_ready and artifact_surface:
        return WorkbenchRoutingDecision(
            decision="invoke_autoresearch",
            confidence=0.86 if subscription_worker_available else 0.78,
            reasons=reasons,
            missing=[],
            suggested_next_step=(
                "open an autoresearch run with worker metadata recorded; keep RD outside "
                "the loop and use the workbench output as ratified evidence"
            ),
            task=task,
            project=project,
            rubric=rubric,
            bounded_claim=bounded_claim,
            stable_evaluator=stable_evaluator,
            rubric_ready=rubric_ready,
            artifact_surface=artifact_surface,
            subscription_worker_available=subscription_worker_available,
            worker_metadata=_worker_metadata_for_decision(
                "invoke_autoresearch",
                subscription_worker_available=subscription_worker_available,
            ),
            surface_scaffold=[],
        )
    if stable_evaluator or bounded_claim or rubric_ready:
        return WorkbenchRoutingDecision(
            decision="prepare_autoresearch_surface",
            confidence=0.66,
            reasons=reasons,
            missing=missing,
            suggested_next_step=(
                "construct the missing evaluator/rubric/artifact surface before using "
                "out-of-loop agent work as the primary research path"
            ),
            task=task,
            project=project,
            rubric=rubric,
            bounded_claim=bounded_claim,
            stable_evaluator=stable_evaluator,
            rubric_ready=rubric_ready,
            artifact_surface=artifact_surface,
            subscription_worker_available=subscription_worker_available,
            worker_metadata=_worker_metadata_for_decision(
                "prepare_autoresearch_surface",
                subscription_worker_available=subscription_worker_available,
            ),
            surface_scaffold=_surface_scaffold(missing, project=project, rubric=rubric),
        )
    return WorkbenchRoutingDecision(
        decision="stay_out_of_loop",
        confidence=0.72,
        reasons=reasons or ["task is still exploratory and underspecified"],
        missing=missing,
        suggested_next_step=(
            "use RD agent work to define a bounded eigenquestion and evaluator, then reroute"
        ),
        task=task,
        project=project,
        rubric=rubric,
        bounded_claim=bounded_claim,
        stable_evaluator=stable_evaluator,
        rubric_ready=rubric_ready,
        artifact_surface=artifact_surface,
        subscription_worker_available=subscription_worker_available,
        worker_metadata=_worker_metadata_for_decision(
            "stay_out_of_loop",
            subscription_worker_available=subscription_worker_available,
        ),
        surface_scaffold=_surface_scaffold(missing, project=project, rubric=rubric),
    )


def _resolve_project_path(project: str, repo_root: Path = REPO_ROOT) -> Path | None:
    if not project:
        return None
    raw = Path(project)
    candidates = [raw if raw.is_absolute() else repo_root / raw]
    if not str(project).startswith("projects/"):
        candidates.append(repo_root / "projects" / project)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def _resolve_rubric_path(rubric: str, repo_root: Path = REPO_ROOT) -> Path | None:
    if not rubric:
        return None
    raw = Path(rubric)
    candidates = [raw if raw.is_absolute() else repo_root / raw]
    if raw.suffix != ".json":
        candidates.append(repo_root / "rubrics" / f"{rubric}.json")
    elif not str(rubric).startswith("rubrics/"):
        candidates.append(repo_root / "rubrics" / raw.name)
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[-1]


def _load_json(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _infer_rubric_ready(rubric_data: dict, rubric_path: Path | None) -> bool:
    if rubric_path is None or not rubric_path.exists():
        return False
    return bool(
        isinstance(rubric_data.get("dimensions"), list)
        or isinstance(rubric_data.get("criteria"), dict)
        or rubric_data.get("falsification_mode")
        or rubric_data.get("score_contract")
    )


def _infer_stable_evaluator(rubric_data: dict, project_path: Path | None, rubric_ready: bool) -> bool:
    project_has_gate = bool(
        project_path
        and project_path.exists()
        and (
            (project_path / "gate_harness.py").exists()
            or (project_path / "test_model.py").exists()
            or (project_path / "test_thesis.py").exists()
        )
    )
    rubric_has_gate = bool(
        rubric_ready
        and (
            isinstance(rubric_data.get("dimensions"), list)
            or isinstance(rubric_data.get("criteria"), dict)
            or rubric_data.get("holdout_hard_gate")
            or rubric_data.get("falsification_mode")
            or rubric_data.get("deterministic_score_gates")
        )
    )
    return project_has_gate or rubric_has_gate


def _infer_artifact_surface(project_path: Path | None) -> bool:
    if project_path is None or not project_path.exists():
        return False
    artifact_names = (
        "current_iteration.md",
        "thesis.md",
        "evidence.txt",
        "test_model.py",
        "project_charter.md",
    )
    return any((project_path / name).exists() for name in artifact_names) or project_path.is_dir()


def _infer_bounded_claim(task: str, rubric_ready: bool, artifact_surface: bool) -> bool:
    task_text = task.lower()
    bounded_terms = (
        "bounded",
        "eigenquestion",
        "discriminator",
        "gate",
        "theorem",
        "falsif",
        "artifact",
        "claim",
        "hypothesis",
    )
    return bool(task.strip() and (rubric_ready or artifact_surface or any(term in task_text for term in bounded_terms)))


def route_autoresearch_workbench_from_context(
    task: str,
    *,
    project: str = "",
    rubric: str = "",
    stable_evaluator: bool | None = None,
    bounded_claim: bool | None = None,
    rubric_ready: bool | None = None,
    artifact_surface: bool | None = None,
    subscription_worker_available: bool = False,
    repo_root: Path | None = None,
) -> WorkbenchRoutingDecision:
    """Infer missing route bits from project/rubric context, then route."""
    repo_root = repo_root or REPO_ROOT
    project_path = _resolve_project_path(project, repo_root)
    rubric_path = _resolve_rubric_path(rubric, repo_root)
    rubric_data = _load_json(rubric_path)

    inferred_rubric_ready = _infer_rubric_ready(rubric_data, rubric_path)
    inferred_artifact_surface = _infer_artifact_surface(project_path)
    inferred_stable_evaluator = _infer_stable_evaluator(
        rubric_data,
        project_path,
        inferred_rubric_ready,
    )
    inferred_bounded_claim = _infer_bounded_claim(
        task,
        inferred_rubric_ready,
        inferred_artifact_surface,
    )

    return route_autoresearch_workbench(
        task,
        stable_evaluator=inferred_stable_evaluator if stable_evaluator is None else stable_evaluator,
        bounded_claim=inferred_bounded_claim if bounded_claim is None else bounded_claim,
        rubric_ready=inferred_rubric_ready if rubric_ready is None else rubric_ready,
        artifact_surface=inferred_artifact_surface if artifact_surface is None else artifact_surface,
        subscription_worker_available=subscription_worker_available,
        project=project,
        rubric=rubric,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Route an RD task toward or away from autoresearch.")
    parser.add_argument("task")
    parser.add_argument("--stable-evaluator", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--project", default="")
    parser.add_argument("--rubric", default="")
    parser.add_argument("--bounded-claim", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--rubric-ready", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--artifact-surface", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--subscription-worker-available", action="store_true")
    args = parser.parse_args(argv)
    decision = route_autoresearch_workbench_from_context(
        args.task,
        stable_evaluator=args.stable_evaluator,
        bounded_claim=args.bounded_claim,
        rubric_ready=args.rubric_ready,
        artifact_surface=args.artifact_surface,
        subscription_worker_available=args.subscription_worker_available,
        project=args.project,
        rubric=args.rubric,
    )
    print(json.dumps(decision.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
