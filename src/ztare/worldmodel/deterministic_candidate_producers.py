"""Configured System-1 candidate producers for interactive substrates.

The play loop sees only typed candidate proposals.  Substrate profiles choose
which registered producer runs and provide input artifact refs; producer
results pass through the project gate harness and candidate pool unchanged.
No producer may edit the champion or candidate prompt.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import pprint
import sys
from typing import Any, Callable


@dataclass(frozen=True)
class DeterministicCandidateProposal:
    producer_id: str
    candidate_path: Path
    candidate_sha256: str
    input_sha256s: dict[str, str]


@dataclass(frozen=True)
class GatedDeterministicCandidate:
    proposal: DeterministicCandidateProposal
    gate_payload: dict[str, Any]
    gate_pass: bool


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _append_receipt(project: Path, row: dict[str, Any]) -> None:
    from ztare.common.schema_routes import append_schema_route_event, assert_schema_route

    route = assert_schema_route(
        str(row.get("schema") or ""), category="operational_carrier"
    )
    append_schema_route_event(
        project,
        schema_id=route.schema_id,
        event=str(row.get("event") or ""),
        join_values={field: row.get(field) for field in route.join_fields},
        payload={
            key: value
            for key, value in row.items()
            if key not in {"schema", "event", *route.join_fields}
        },
    )


def _catalog_operation_patch_compiler(
    project: Path,
    declaration: dict[str, Any],
) -> DeterministicCandidateProposal | None:
    """Compile a task-bound registered operation without another model call.

    The counterexample workbench owns adapter vocabulary and emits a literal
    lowering.  This producer only preserves the current carrier identity and
    applies that lowering through the already-registered catalog compiler.  A
    diagnostic receipt still has no promotion authority: the unchanged project
    gates decide whether the compiled conjecture survives.
    """

    from ztare.common.leaf_workbench_executor import (
        active_workbench_task_capability_scope,
        active_workbench_task_receipt_family,
    )
    from ztare.worldmodel.patch_base_carrier import (
        compact_literal_patch_prefix,
        materialize_immutable_patch_base,
    )
    from ztare.worldmodel.spec_catalog import validate_patch_delta_spec

    task_scope, task = active_workbench_task_capability_scope(
        project,
        adapter_id="worldmodel",
    )
    task_id = str(task.get("task_id") or "")
    if not task_scope or not task_id:
        return None

    receipt_family = active_workbench_task_receipt_family(
        project,
        adapter_id="worldmodel",
        materialize=True,
    )
    inspection_receipt = receipt_family.get(
        "inspect_worldmodel_counterexample_context"
    )
    selector_receipt = receipt_family.get("mine_worldmodel_lowerable_selectors")
    if not isinstance(inspection_receipt, dict) or not isinstance(
        selector_receipt, dict
    ):
        return None

    def receipt_summary(receipt: dict[str, Any]) -> dict[str, Any] | None:
        summary: Any = receipt.get("output_summary")
        if isinstance(summary, str):
            try:
                summary = json.loads(summary)
            except json.JSONDecodeError:
                return None
        return summary if isinstance(summary, dict) else None

    inspection = receipt_summary(inspection_receipt)
    selector = receipt_summary(selector_receipt)
    if inspection is None or selector is None:
        return None
    candidates = inspection.get("catalog_residual_event_candidates")
    operation_sha = str(selector.get("operation_identity_sha256") or "")
    event = next(
        (
            candidate
            for candidate in (candidates if isinstance(candidates, list) else ())
            if isinstance(candidate, dict)
            and str(candidate.get("operation_identity_sha256") or "")
            == operation_sha
        ),
        None,
    )
    if event is None:
        return None
    identity = event.get("operation_identity")
    event_lowering = event.get("lowering")
    if not isinstance(identity, dict) or not isinstance(event_lowering, dict):
        return None
    computed_operation_sha = hashlib.sha256(
        json.dumps(
            identity,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")
    ).hexdigest()
    if not operation_sha or operation_sha != computed_operation_sha:
        raise ValueError("catalog operation identity digest does not match")
    if (
        selector.get("schema") != "ztare-worldmodel-operation-domain-selector-v1"
        or selector.get("candidate_delta_admissible") is not True
        or str(selector.get("task_id") or "") != task_id
        or str(selector.get("task_source_sha256") or "")
        != str(task.get("source_sha256") or "")
        or str(selector.get("operation_identity_sha256") or "") != operation_sha
    ):
        return None
    operation_guard = selector.get("operation_guard")
    guard_lowering = (
        operation_guard.get("lowering")
        if isinstance(operation_guard, dict)
        else None
    )
    if not isinstance(guard_lowering, dict):
        return None
    lowering = dict(event_lowering)
    for key, value in guard_lowering.items():
        if key in lowering and lowering[key] != value:
            raise ValueError("operation-domain guard conflicts with event lowering")
        lowering[key] = value
    lowering_kind = str(event.get("lowering_kind") or event_lowering.get("op") or "")
    if lowering_kind != str(lowering.get("op") or ""):
        raise ValueError("catalog operation changed lowering family")

    # A lowering is an adapter presentation of the carried operation.  Trace
    # coordinates are evidence locators, not lawful selector fields.
    forbidden_properties = {"action", "intervention", "row", "t", "frame"}
    leaked = forbidden_properties & set(lowering)
    if leaked:
        raise ValueError(
            "catalog operation lowering contains diagnostic properties: "
            + ",".join(sorted(leaked))
        )
    patch_spec = {"actions": {}, "always": [dict(lowering)]}
    error = validate_patch_delta_spec(patch_spec)
    if error:
        raise ValueError(f"catalog operation receipt is not lowerable: {error}")

    # Compose over the carrier named by the active task, never over the mutable
    # project root.  The task-scope door already verifies that this source's
    # digest equals the active frontier identity; selecting test_model.py here
    # would silently drop intervening PATCH_BASE layers.
    from ztare.common.artifact_refs import resolve_project_artifact_ref

    task_source_ref = str(task.get("source_ref") or "").strip()
    task_source = resolve_project_artifact_ref(project, task_source_ref)
    if task_source is None or not task_source.is_file():
        return None
    current_source = task_source.read_text(encoding="utf-8")
    compacted_source = compact_literal_patch_prefix(
        task_source,
        project_dir=project,
    )
    base_ref, base_sha = materialize_immutable_patch_base(
        project,
        compacted_source or current_source,
        prefix=("compacted_frontier" if compacted_source else "governed_frontier"),
    )
    receipt_refs: list[str] = []
    for family_receipt in (inspection_receipt, selector_receipt):
        receipt_hashes = family_receipt.get("input_hashes")
        receipt_hashes = receipt_hashes if isinstance(receipt_hashes, dict) else {}
        receipt_ref = str(receipt_hashes.get("kernel_receipt_ref") or "")
        if receipt_ref and receipt_ref not in receipt_refs:
            receipt_refs.append(receipt_ref)
    source = (
        f"# TaskIdentity: {task_id}\n"
        f"# OperationIdentity: {operation_sha}\n"
        f"# ReceiptRefs: {','.join(receipt_refs)}\n"
        "PATCH_BASE = "
        + pprint.pformat(
            {"source_ref": base_ref, "sha256": base_sha},
            sort_dicts=True,
            width=100,
        )
        + "\n\nPATCH_DELTA_SPEC = "
        + pprint.pformat(patch_spec, sort_dicts=True, width=100)
        + "\n"
    )
    candidate_sha = hashlib.sha256(source.encode("utf-8")).hexdigest()
    output = project / "workspace" / "submissions" / f"compiled_op_{candidate_sha[:16]}.py"
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and _sha_file(output) != candidate_sha:
        raise ValueError("content-addressed catalog-operation path collision")
    if not output.exists():
        temporary = output.with_suffix(".tmp")
        temporary.write_text(source, encoding="utf-8")
        temporary.replace(output)

    input_sha256s = {
        base_ref: base_sha,
        task_source_ref: _sha_file(task_source),
        str(Path(__file__).resolve()): _sha_file(Path(__file__).resolve()),
    }
    for receipt_ref in receipt_refs:
        receipt_path = project / receipt_ref
        if receipt_path.is_file():
            input_sha256s[receipt_ref] = _sha_file(receipt_path)
    weakness = project / "workspace" / "latest_harness_weakness.json"
    if weakness.is_file():
        input_sha256s["workspace/latest_harness_weakness.json"] = _sha_file(weakness)
    return DeterministicCandidateProposal(
        producer_id=str(
            declaration.get("producer_id")
            or "worldmodel_catalog_operation_patch_compiler.v1"
        ),
        candidate_path=output,
        candidate_sha256=candidate_sha,
        input_sha256s=input_sha256s,
    )


CandidateProducer = Callable[
    [Path, dict[str, Any]], DeterministicCandidateProposal | None
]


_PRODUCERS: dict[str, CandidateProducer] = {
    "worldmodel.catalog_operation_patch_compiler.v1": _catalog_operation_patch_compiler,
}


def configured_proposals(
    project_dir: str | Path,
    play_config: dict[str, Any],
    *,
    phase: str,
) -> list[DeterministicCandidateProposal]:
    project = Path(project_dir).resolve()
    declarations = play_config.get("deterministic_candidate_producers") or []
    if not isinstance(declarations, list):
        raise ValueError("deterministic_candidate_producers must be a list")
    proposals: list[DeterministicCandidateProposal] = []
    for declaration in declarations:
        if not isinstance(declaration, dict) or declaration.get("phase") != phase:
            continue
        kind = str(declaration.get("kind") or "")
        producer = _PRODUCERS.get(kind)
        if producer is None:
            raise ValueError(f"unregistered deterministic candidate producer: {kind!r}")
        proposal = producer(project, declaration)
        if proposal is None:
            continue
        proposals.append(proposal)
    return proposals


def evaluate_configured_candidates(
    project_dir: str | Path,
    play_config: dict[str, Any],
    *,
    phase: str,
) -> list[GatedDeterministicCandidate]:
    """Materialize proposals and return every project-gate consequence.

    Rejected proposals remain first-class consequences: a localized residual
    can be a better repair frontier than restarting discovery over the raw
    bank.  This function grants no adoption authority; ``gate_pass`` is the
    only promotion boundary.
    """
    from ztare.validator.core.pre_judge_gate import (
        consume_pre_judge_gate_receipt,
        run_pre_judge_gate_harness,
    )

    project = Path(project_dir).resolve()
    assessed: list[GatedDeterministicCandidate] = []
    for proposal in configured_proposals(project, play_config, phase=phase):
        _append_receipt(
            project,
            {
                "schema": "ztare-deterministic-candidate-producer-receipt-v1",
                "event": "materialized",
                "phase": phase,
                "producer_id": proposal.producer_id,
                "candidate_ref": str(proposal.candidate_path.relative_to(project)),
                "candidate_sha256": proposal.candidate_sha256,
                "input_sha256s": proposal.input_sha256s,
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
            },
        )
        result = run_pre_judge_gate_harness(
            enabled=True,
            project_dir=project,
            latest_eval_results_path=project / "latest_eval_results.json",
            python_executable=sys.executable,
            candidate_path=proposal.candidate_path,
        )
        payload = result.payload if isinstance(result.payload, dict) else {}
        gates = payload.get("gates") if isinstance(payload.get("gates"), dict) else {}
        consumed = consume_pre_judge_gate_receipt(
            payload,
            candidate_path=proposal.candidate_path,
        )
        authorized = bool(result.ran and consumed["evaluator_authorized"])
        _append_receipt(
            project,
            {
                "schema": "ztare-deterministic-candidate-producer-receipt-v1",
                "event": "consumed_by_project_gate",
                "phase": phase,
                "producer_id": proposal.producer_id,
                "candidate_sha256": proposal.candidate_sha256,
                "gate_engine": payload.get("engine"),
                "gate_pass": authorized,
                "raw_gate_failures": consumed["failed_gates"],
                "pre_judge_decision_consumed": True,
                "gate_names": sorted(gates),
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
            },
        )
        assessed.append(GatedDeterministicCandidate(proposal, payload, authorized))
    return assessed


__all__ = [
    "DeterministicCandidateProposal",
    "GatedDeterministicCandidate",
    "configured_proposals",
    "evaluate_configured_candidates",
]
