from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
from pathlib import Path
import pprint
from typing import Callable, Literal

from ztare.common.artifact_refs import collect_artifact_refs, missing_project_artifact_refs
from ztare.common.control_state_machine import CONTROL_RECEIPT_MARKERS, control_receipt_rows
from ztare.common.leaf_workbench_proposals import (
    sync_leaf_workbench_capability_proposals,
)
from ztare.common.patch_base_identity import TASK_HYPOTHESIS_COMPANION_SCHEMA
from ztare.validator.core.repair_preflight import (
    ambient_carrier_dependency_retry_message,
    boundary_cegar_ready_delta_retry_message,
    leaf_workbench_action_request_retry_message,
    leaf_workbench_retry_message,
    patch_base_regression_retry_message,
    strategy_card_retry_message,
    blocked_control_missing_evidence_action_retry_message,
)
from ztare.validator.worldmodel_typed_payload import extract_worldmodel_control_receipts


@dataclass(frozen=True)
class CandidatePreflightRequest:
    """Parent-owned compatibility checks before authority gates run."""

    project_dir: str | Path
    thesis_text: str
    executable_candidate_source: str
    python_executable: str
    pre_judge_gate_harness: bool
    is_worldmodel_contract: bool
    source_ref: str
    artifact_role: Literal["behavior_carrier", "task_hypothesis"] = "behavior_carrier"


@dataclass(frozen=True)
class ControlOnlyPreflightRequest:
    """Parent-owned compatibility checks for no-carrier control submissions."""

    project_dir: str | Path
    thesis_text: str


@dataclass(frozen=True)
class PreflightRule:
    """One parent-owned compatibility rule before authority gates."""

    id: str
    applies_to: Literal["candidate", "control_only"]
    authority: Literal["syntax", "admissibility", "diagnostic"]
    run: Callable[[], str | None]


def run_candidate_preflights(
    request: CandidatePreflightRequest,
    *,
    log: Callable[[str], None] | None = None,
) -> str | None:
    """Return the first compatibility failure, or None.

    This is the single parent preflight door for executable candidates. It
    deliberately receives only executable candidate bytes, never the surrounding
    response envelope, so control receipts cannot pollute carrier identity.
    """

    candidate_source = request.executable_candidate_source
    return _run_preflight_rules(_candidate_preflight_rules(request, candidate_source, log=log))


def task_hypothesis_companion_source(
    *,
    project_dir: str | Path,
    task_source: str,
) -> str:
    """Bind a standalone task predicate to the current carrier without copying it.

    Task hypotheses and transition carriers have separate promotion authority.
    The leaf authors only the predicate module; the kernel supplies an identity
    delta over the current content-addressed carrier so existing evaluation and
    candidate-memory machinery can observe the companion without asking the
    leaf to import, repeat, or mutate dynamics.
    """
    try:
        tree = ast.parse(task_source)
    except SyntaxError as exc:
        raise ValueError(f"task-hypothesis source is not valid Python: {exc}") from exc
    if any(isinstance(node, (ast.Import, ast.ImportFrom)) for node in ast.walk(tree)):
        raise ValueError(
            "task-hypothesis source must be standalone; imports and ambient carrier "
            "dependencies are forbidden"
        )
    forbidden = {
        "step", "f", "model", "I_model", "PROGRAM", "WORLD_MODEL_SPEC",
        "PATCH_BASE", "PATCH_DELTA", "PATCH_DELTA_SPEC",
    }
    defined = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }
    assigned = {
        target.id
        for node in tree.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in (
            node.targets if isinstance(node, ast.Assign) else (node.target,)
        )
        if isinstance(target, ast.Name)
    }
    collisions = sorted((defined | assigned) & forbidden)
    if collisions:
        raise ValueError(
            "task-hypothesis source may not define transition-carrier names: "
            + ", ".join(collisions)
        )
    predicates = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "GOAL_PREDICATE"
    ]
    if len(predicates) != 1:
        raise ValueError(
            "task-hypothesis source requires exactly one GOAL_PREDICATE(state)"
        )
    predicate = predicates[0]
    if (
        len(predicate.args.args) != 1
        or predicate.args.vararg is not None
        or predicate.args.kwarg is not None
    ):
        raise ValueError("GOAL_PREDICATE must accept exactly one state argument")

    from ztare.common.candidate_memory import (
        best_admissible_candidate_memory_record,
        candidate_memory_submission_path,
    )

    project = Path(project_dir).resolve()
    record = best_admissible_candidate_memory_record(
        project,
        source_types={"full_survivor"},
        require_submission_source=True,
    )
    carrier_path = (
        candidate_memory_submission_path(project, record)
        if record is not None
        else None
    )
    if carrier_path is None:
        raise ValueError(
            "task-hypothesis companion requires a current content-addressed carrier"
        )
    carrier_sha = hashlib.sha256(carrier_path.read_bytes()).hexdigest()
    carrier_ref = str(carrier_path.relative_to(project))
    provenance = {
        "schema": TASK_HYPOTHESIS_COMPANION_SCHEMA,
        "predicate_source_sha256": hashlib.sha256(
            task_source.encode("utf-8")
        ).hexdigest(),
        "carrier_source_ref": carrier_ref,
        "carrier_sha256": carrier_sha,
    }
    return (
        "TASK_HYPOTHESIS_PROVENANCE = "
        + pprint.pformat(provenance, sort_dicts=True, width=100)
        + "\nPATCH_BASE = "
        + pprint.pformat(
            {"source_ref": carrier_ref, "sha256": carrier_sha},
            sort_dicts=True,
            width=100,
        )
        + "\n\ndef PATCH_DELTA(base_next, state, action):\n"
        + "    return base_next\n\n"
        + task_source.strip()
        + "\n"
    )


def run_worldmodel_control_only_preflights(
    request: ControlOnlyPreflightRequest,
) -> str | None:
    """Return the first control-only compatibility failure, or None.

    Control-only rows are state transitions in the Boundary-CEGAR lifecycle:
    action request, capability proposal, receipt, or typed blocker. They are not
    executable candidates, so this door validates the control move without
    letting the general autoresearch loop learn each receipt dialect.
    """

    return _run_preflight_rules(_control_only_preflight_rules(request))


def has_worldmodel_control_marker(text: str) -> bool:
    """Whether text carries a recognized no-carrier worldmodel control move."""

    if control_receipt_rows(text or ""):
        return True
    return any(marker in (text or "") for marker in _WORLDMODEL_CONTROL_MARKERS)


def sync_worldmodel_capability_proposals(
    *,
    project_dir: str | Path,
    text: str,
    source_ref: str,
    log: Callable[[str], None] | None = None,
) -> None:
    """Mirror morphism-shaped capability proposals into the tool queue."""

    request = CandidatePreflightRequest(
        project_dir=project_dir,
        thesis_text=text,
        executable_candidate_source="",
        python_executable="",
        pre_judge_gate_harness=False,
        is_worldmodel_contract=True,
        source_ref=source_ref,
    )
    _sync_capability_proposals(request, log=log)


def _leaf_fact_markers(
    is_worldmodel_contract: bool,
    *,
    log: Callable[[str], None] | None = None,
) -> tuple[str, ...]:
    if not is_worldmodel_contract:
        return ()
    try:
        from ztare.worldmodel.leaf_workbench import (
            WORLD_MODEL_LEAF_WORKBENCH_FACT_MARKERS,
        )
    except Exception as exc:  # noqa: BLE001
        if log is not None:
            log(f"leaf fact markers unavailable: {exc}")
        return ()
    return WORLD_MODEL_LEAF_WORKBENCH_FACT_MARKERS


def _sync_capability_proposals(
    request: CandidatePreflightRequest,
    *,
    log: Callable[[str], None] | None,
) -> None:
    try:
        sync_leaf_workbench_capability_proposals(
            request.project_dir,
            request.thesis_text,
            source_ref=request.source_ref,
            default_target_artifact=(
                "src/ztare/worldmodel/leaf_workbench.py"
                if request.is_worldmodel_contract
                else None
            ),
        )
    except Exception as exc:  # noqa: BLE001
        if log is not None:
            log(f"leaf-workbench capability proposal sync skipped: {exc}")


def _run_preflight_rules(rules: tuple[PreflightRule, ...]) -> str | None:
    for rule in rules:
        message = rule.run()
        if message is not None:
            return message
    return None


def _candidate_preflight_rules(
    request: CandidatePreflightRequest,
    candidate_source: str,
    *,
    log: Callable[[str], None] | None,
) -> tuple[PreflightRule, ...]:
    rules: list[PreflightRule] = [
        PreflightRule(
            id="strategy_card_receipt",
            applies_to="candidate",
            authority="admissibility",
            run=lambda: strategy_card_retry_message(
                project_dir=request.project_dir,
                thesis_text=request.thesis_text,
                candidate_source=candidate_source,
            ),
        )
    ]
    if not request.pre_judge_gate_harness:
        return tuple(rules)

    fact_markers = _leaf_fact_markers(request.is_worldmodel_contract, log=log)
    leaf_enabled = bool(fact_markers)
    rules.extend(
        [
            PreflightRule(
                id="leaf_action_request",
                applies_to="candidate",
                authority="admissibility",
                run=lambda: leaf_workbench_action_request_retry_message(
                    enabled=leaf_enabled,
                    project_dir=request.project_dir,
                    thesis_text=request.thesis_text,
                    candidate_source=candidate_source,
                ),
            ),
            PreflightRule(
                id="sync_capability_proposals",
                applies_to="candidate",
                authority="diagnostic",
                run=lambda: (_sync_capability_proposals(request, log=log), None)[1],
            ),
            PreflightRule(
                id="leaf_receipt_provenance",
                applies_to="candidate",
                authority="admissibility",
                run=lambda: leaf_workbench_retry_message(
                    enabled=leaf_enabled,
                    thesis_text=request.thesis_text,
                    candidate_source=candidate_source,
                    fact_markers=fact_markers,
                    project_dir=request.project_dir,
                ),
            ),
            PreflightRule(
                id="ambient_dependency",
                applies_to="candidate",
                authority="syntax",
                run=lambda: ambient_carrier_dependency_retry_message(
                    enabled=True,
                    candidate_source=candidate_source,
                ),
            ),
            PreflightRule(
                id="patch_base_improvement",
                applies_to="candidate",
                authority="admissibility",
                run=lambda: patch_base_regression_retry_message(
                    enabled=True,
                    project_dir=request.project_dir,
                    candidate_source=candidate_source,
                    python_executable=request.python_executable,
                    allow_behavioral_tie=(request.artifact_role == "task_hypothesis"),
                ),
            ),
        ]
    )
    return tuple(rules)


def _control_only_preflight_rules(request: ControlOnlyPreflightRequest) -> tuple[PreflightRule, ...]:
    thesis_text = request.thesis_text or ""
    return (
        PreflightRule(
            id="control_evidence_refs_resolve",
            applies_to="control_only",
            authority="admissibility",
            run=lambda: _control_receipt_refs_retry_message(request.project_dir, thesis_text),
        ),
        PreflightRule(
            id="leaf_action_request",
            applies_to="control_only",
            authority="admissibility",
            run=lambda: leaf_workbench_action_request_retry_message(
                enabled=True,
                project_dir=request.project_dir,
                thesis_text=thesis_text,
                candidate_source="",
            ),
        ),
        PreflightRule(
            id="blocked_control_boundary_morphism",
            applies_to="control_only",
            authority="admissibility",
            run=lambda: blocked_control_missing_evidence_action_retry_message(
                enabled=True,
                project_dir=request.project_dir,
                thesis_text=thesis_text,
                candidate_source="",
            ),
        ),
        PreflightRule(
            id="boundary_cegar_ready_delta",
            applies_to="control_only",
            authority="admissibility",
            run=lambda: boundary_cegar_ready_delta_retry_message(
                enabled=True,
                thesis_text=thesis_text,
                candidate_source="",
            ),
        ),
    )


def _control_receipt_refs_retry_message(project_dir: str | Path, thesis_text: str) -> str | None:
    receipts = extract_worldmodel_control_receipts(thesis_text or "")
    refs: list[str] = []
    for row in receipts:
        if not isinstance(row, dict):
            continue
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue
        refs.extend(collect_artifact_refs(payload))
    missing = missing_project_artifact_refs(project_dir, refs)
    if not missing:
        return None
    return (
        "Worldmodel control receipt cites local evidence refs that do not resolve in the "
        "project workspace. Re-run or cite durable visible receipts/artifacts before "
        "stopping; missing_refs="
        + ",".join(missing[:8])
    )

_WORLDMODEL_CONTROL_MARKERS = tuple(CONTROL_RECEIPT_MARKERS)
