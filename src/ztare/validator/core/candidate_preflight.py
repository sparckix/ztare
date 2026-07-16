from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Literal

from ztare.common.artifact_refs import collect_artifact_refs, missing_project_artifact_refs
from ztare.common.control_state_machine import CONTROL_RECEIPT_MARKERS, control_receipt_rows
from ztare.common.leaf_workbench_proposals import (
    sync_leaf_workbench_capability_proposals,
)
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
