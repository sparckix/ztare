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
from typing import Any, Literal

from ztare.research_director.autoresearch_plan_preview import (
    build_autoresearch_plan_preview,
    route_command_for_task,
    run_command_for_project,
)


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
    operator_card_routes: list[dict[str, Any]] = field(default_factory=list)
    surface_scaffold: list[dict] = field(default_factory=list)
    source_contract_errors: list[str] = field(default_factory=list)
    kernel_entry_contract: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        payload = asdict(self)
        kernel_entry = self.kernel_entry_contract or {}
        intake = str(
            kernel_entry.get("intake_path")
            or kernel_entry.get("packet_path")
            or ""
        ).strip()
        run_command = str(kernel_entry.get("run_command") or "").strip() or None
        preflight_command = (
            str(kernel_entry.get("preflight_command") or "").strip() or None
        )
        if self.decision == "invoke_autoresearch" and not run_command:
            run_command = run_command_for_project(
                project=self.project,
                rubric=self.rubric,
                intake=intake,
            )
        if self.decision == "invoke_autoresearch" and not preflight_command:
            preflight_command = run_command_for_project(
                project=self.project,
                rubric=self.rubric,
                intake=intake,
                preflight_only=True,
            )
        route_command = (
            str(kernel_entry.get("entry_command") or "").strip()
            or route_command_for_task(
                task=self.task,
                project=self.project,
                rubric=self.rubric,
                intake=intake,
            )
        )
        worker_transport = str((self.worker_metadata or {}).get("transport") or "")
        payload["plan_preview"] = build_autoresearch_plan_preview(
            decision=self.decision,
            project=self.project,
            rubric=self.rubric,
            route_command=route_command,
            preflight_command=preflight_command,
            run_command=run_command,
            can_run_now=self.decision == "invoke_autoresearch",
            missing=self.missing,
            blocking_missing=self.source_contract_errors,
            source="autoresearch_workbench_router",
            worker_transport=worker_transport,
        )
        return payload


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


def _operator_card_routes_for_decision(
    *,
    task: str,
    project: str,
    rubric: str,
    decision: Decision,
    missing: list[str],
    source_contract_errors: list[str],
) -> list[dict[str, Any]]:
    context = [
        "autoresearch_workbench_routing",
        task,
        project,
        rubric,
        decision,
        " ".join(missing),
        " ".join(source_contract_errors),
    ]
    try:
        from ztare.research_director.primitive_operator_cards import (
            operator_card_route_receipts,
            route_operator_cards_semantic,
        )

        return operator_card_route_receipts(
            route_operator_cards_semantic(context=context, top_n=3)
        )
    except Exception:  # noqa: BLE001
        return []


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
    source_contract_errors: list[str] | None = None,
    kernel_entry_contract: dict[str, Any] | None = None,
) -> WorkbenchRoutingDecision:
    """Return an RD routing decision for the autoresearch workbench."""
    reasons: list[str] = []
    missing: list[str] = []
    source_contract_errors = source_contract_errors or []
    kernel_entry_contract = kernel_entry_contract or {}
    kernel_focus_reasons = _kernel_entry_focus_reasons(kernel_entry_contract)
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

    if source_contract_errors:
        return WorkbenchRoutingDecision(
            decision="prepare_autoresearch_surface",
            confidence=0.31,
            reasons=[*reasons, *kernel_focus_reasons, "source contract failed preflight"],
            missing=[*missing, *source_contract_errors],
            suggested_next_step=(
                "repair the rubric/source/trace contract before invoking autoresearch; "
                "do not let context inference turn malformed or stale source rows into a ready workbench"
            ),
            task=task,
            project=project,
            rubric=rubric,
            bounded_claim=bounded_claim,
            stable_evaluator=stable_evaluator,
            rubric_ready=False,
            artifact_surface=artifact_surface,
            subscription_worker_available=subscription_worker_available,
            worker_metadata=_worker_metadata_for_decision(
                "prepare_autoresearch_surface",
                subscription_worker_available=subscription_worker_available,
            ),
            operator_card_routes=_operator_card_routes_for_decision(
                task=task,
                project=project,
                rubric=rubric,
                decision="prepare_autoresearch_surface",
                missing=[*missing, *source_contract_errors],
                source_contract_errors=source_contract_errors,
            ),
            surface_scaffold=_surface_scaffold(missing, project=project, rubric=rubric),
            source_contract_errors=source_contract_errors,
            kernel_entry_contract=kernel_entry_contract,
        )

    if stable_evaluator and bounded_claim and rubric_ready and artifact_surface:
        return WorkbenchRoutingDecision(
            decision="invoke_autoresearch",
            confidence=0.86 if subscription_worker_available else 0.78,
            reasons=[*reasons, *kernel_focus_reasons],
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
            operator_card_routes=_operator_card_routes_for_decision(
                task=task,
                project=project,
                rubric=rubric,
                decision="invoke_autoresearch",
                missing=[],
                source_contract_errors=[],
            ),
            surface_scaffold=[],
            source_contract_errors=[],
            kernel_entry_contract=kernel_entry_contract,
        )
    if stable_evaluator or bounded_claim or rubric_ready:
        return WorkbenchRoutingDecision(
            decision="prepare_autoresearch_surface",
            confidence=0.66,
            reasons=[*reasons, *kernel_focus_reasons],
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
            operator_card_routes=_operator_card_routes_for_decision(
                task=task,
                project=project,
                rubric=rubric,
                decision="prepare_autoresearch_surface",
                missing=missing,
                source_contract_errors=[],
            ),
            surface_scaffold=_surface_scaffold(missing, project=project, rubric=rubric),
            source_contract_errors=[],
            kernel_entry_contract=kernel_entry_contract,
        )
    return WorkbenchRoutingDecision(
        decision="stay_out_of_loop",
        confidence=0.72,
        reasons=[*(reasons or ["task is still exploratory and underspecified"]), *kernel_focus_reasons],
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
        operator_card_routes=_operator_card_routes_for_decision(
            task=task,
            project=project,
            rubric=rubric,
            decision="stay_out_of_loop",
            missing=missing,
            source_contract_errors=[],
        ),
        surface_scaffold=_surface_scaffold(missing, project=project, rubric=rubric),
        source_contract_errors=[],
        kernel_entry_contract=kernel_entry_contract,
    )


def _kernel_entry_focus_reasons(kernel_entry_contract: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    focus_receipts = kernel_entry_contract.get("in_loop_focus_receipts")
    if not isinstance(focus_receipts, list):
        focus_receipts = []
    for receipt in focus_receipts:
        if not isinstance(receipt, dict):
            continue
        reason = str(receipt.get("reason") or "").strip()
        graph_id = str(receipt.get("graph_id") or "").strip()
        if reason:
            suffix = f" ({graph_id})" if graph_id else ""
            reasons.append(f"run-readiness in-loop focus: {reason}{suffix}")

    withheld_receipts = kernel_entry_contract.get("withheld_in_loop_focus_receipts")
    if not isinstance(withheld_receipts, list):
        withheld_receipts = []
    for receipt in withheld_receipts:
        if not isinstance(receipt, dict):
            continue
        reason = str(receipt.get("reason") or "").strip()
        graph_id = str(receipt.get("graph_id") or "").strip()
        if reason:
            suffix = f" ({graph_id})" if graph_id else ""
            reasons.append(
                "run-readiness in-loop focus withheld until blockers clear: "
                f"{reason}{suffix}"
            )
    return reasons


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
    except json.JSONDecodeError as exc:
        raise ValueError(f"malformed rubric JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"malformed rubric JSON: {path}: top-level value must be an object")
    return data


def _rubric_source_contract_errors(
    rubric_data: dict,
    *,
    rubric_path: Path | None,
    project_path: Path | None,
) -> list[str]:
    if rubric_path is None or not rubric_path.exists():
        return []
    errors: list[str] = []
    dimensions = rubric_data.get("dimensions")
    if dimensions is not None:
        if not isinstance(dimensions, list) or not dimensions:
            errors.append("rubric dimensions must be a non-empty list when provided")
        else:
            weights: list[float] = []
            for idx, dimension in enumerate(dimensions, start=1):
                if not isinstance(dimension, dict):
                    errors.append(f"rubric dimensions[{idx}] must be an object")
                    continue
                if not str(dimension.get("name") or "").strip():
                    errors.append(f"rubric dimensions[{idx}] missing name")
                if not str(dimension.get("description") or "").strip():
                    errors.append(f"rubric dimensions[{idx}] missing description")
                try:
                    weight = float(dimension.get("weight"))
                except (TypeError, ValueError):
                    errors.append(f"rubric dimensions[{idx}] weight must be numeric")
                    continue
                if weight <= 0:
                    errors.append(f"rubric dimensions[{idx}] weight must be positive")
                weights.append(weight)
            if weights and abs(sum(weights) - 100.0) > 0.01:
                errors.append("rubric dimensions weights must sum to 100")
    criteria = rubric_data.get("criteria")
    if criteria is not None:
        if not isinstance(criteria, dict) or not criteria:
            errors.append("rubric criteria must be a non-empty object when provided")
        else:
            for name, criterion in criteria.items():
                if not str(name or "").strip():
                    errors.append("rubric criteria contains an empty name")
                if not str(criterion or "").strip():
                    errors.append(f"rubric criteria[{name!r}] must be non-empty")
    if rubric_data.get("holdout_hard_gate") is True:
        if project_path is None or not project_path.exists():
            errors.append("holdout_hard_gate requires an existing project path")
        else:
            for name in ("gate_harness.py", "evidence_holdout.txt"):
                if not (project_path / name).exists():
                    errors.append(f"holdout_hard_gate requires {name}")
    return errors


def _infer_rubric_ready(rubric_data: dict, rubric_path: Path | None) -> bool:
    if rubric_path is None or not rubric_path.exists():
        return False
    return bool(
        (isinstance(rubric_data.get("dimensions"), list) and bool(rubric_data.get("dimensions")))
        or (isinstance(rubric_data.get("criteria"), dict) and bool(rubric_data.get("criteria")))
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
            (isinstance(rubric_data.get("dimensions"), list) and bool(rubric_data.get("dimensions")))
            or (isinstance(rubric_data.get("criteria"), dict) and bool(rubric_data.get("criteria")))
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


def _project_has_trace_source_surface(project_path: Path | None) -> bool:
    if project_path is None or not project_path.exists():
        return False
    raw_dir = project_path / "raw"
    has_raw_files = bool(
        raw_dir.exists()
        and any(
            path.is_file() and path.name != "source_type_map.json"
            for path in raw_dir.rglob("*")
        )
    )
    workspace = project_path / "workspace"
    return any(
        (
            has_raw_files,
            (project_path / "evidence.txt").exists(),
            (project_path / "compiled_evidence_provenance.json").exists(),
            (workspace / "evidence_compile_provenance.json").exists(),
            (workspace / "source_index.json").exists(),
            (workspace / "latest_evidence_gaps.json").exists(),
        )
    )


def _trace_source_contract_errors(
    *,
    project: str,
    rubric: str,
    project_path: Path | None,
    repo_root: Path,
    packet: str | None = None,
) -> tuple[list[str], dict[str, Any]]:
    if not project or (not packet and not _project_has_trace_source_surface(project_path)):
        return [], {}
    try:
        from ztare.reports.autoresearch_trace import build_autoresearch_trace

        trace = build_autoresearch_trace(
            project=project,
            rubric=rubric or None,
            packet=packet,
            repo=repo_root,
            full_health=False,
        )
    except Exception as exc:  # noqa: BLE001
        return [f"autoresearch trace preflight unavailable: {type(exc).__name__}: {exc}"], {}

    kernel_entry = trace.get("kernel_entry") if isinstance(trace.get("kernel_entry"), dict) else {}
    blocking = [
        str(item)
        for item in trace.get("blocking_missing", [])
        if packet or str(item) != "project_packet"
    ]
    if packet and not bool(kernel_entry.get("can_enter_kernel")):
        for blocker in kernel_entry.get("blockers") or []:
            if not isinstance(blocker, dict):
                continue
            blocker_id = str(blocker.get("id") or "").strip()
            if blocker_id and blocker_id not in blocking:
                blocking.append(blocker_id)
    if not blocking:
        return [], kernel_entry
    errors = [f"autoresearch trace blocks run readiness: {item}" for item in blocking]
    for action in trace.get("recovery_actions", []):
        if not isinstance(action, dict):
            continue
        action_id = str(action.get("id") or "").strip()
        next_command = str(action.get("next_command") or "").strip()
        if action_id and next_command:
            errors.append(f"autoresearch trace recovery[{action_id}]: {next_command}")
    for blocker in kernel_entry.get("blockers") or []:
        if not isinstance(blocker, dict):
            continue
        blocker_id = str(blocker.get("id") or "").strip()
        next_command = str(blocker.get("next_command") or "").strip()
        if blocker_id and next_command:
            row = f"autoresearch run-readiness recovery[{blocker_id}]: {next_command}"
            if row not in errors:
                errors.append(row)
    return errors, kernel_entry


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
    packet: str | None = None,
) -> WorkbenchRoutingDecision:
    """Infer missing route bits from project/rubric context, then route."""
    repo_root = repo_root or REPO_ROOT
    project_path = _resolve_project_path(project, repo_root)
    rubric_path = _resolve_rubric_path(rubric, repo_root)
    rubric_data = _load_json(rubric_path)
    source_contract_errors = _rubric_source_contract_errors(
        rubric_data,
        rubric_path=rubric_path,
        project_path=project_path,
    )
    trace_errors, kernel_entry_contract = _trace_source_contract_errors(
        project=project,
        rubric=rubric,
        project_path=project_path,
        repo_root=repo_root,
        packet=packet,
    )
    source_contract_errors.extend(trace_errors)

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
        source_contract_errors=source_contract_errors,
        kernel_entry_contract=kernel_entry_contract,
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
    parser.add_argument(
        "--intake",
        "--packet",
        dest="packet",
        help="Optional project-intake JSON to enforce as the run-readiness boundary; --packet is a compatibility alias.",
    )
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
        packet=args.packet,
    )
    print(json.dumps(decision.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
