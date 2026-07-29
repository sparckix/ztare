"""Static handlers for frozen theory-task boundary identities.

The frontier boundary does not infer execution or evidence semantics from a
task's fields.  Each admitted adjudicator has one reviewed handler declaring
its executor kind, result validator, resource reservation, and journal
projection.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from ztare.common.task_discharge import TaskDischargeContract


FORMALIZATION_CAMPAIGN_EXECUTOR = "formalization_campaign"
DATA_ONLY_WITNESS_EXECUTOR = "data_only_witness_construction"

BoundaryValidator = Callable[[TaskDischargeContract, Mapping[str, Any]], dict[str, Any]]


@dataclass(frozen=True)
class TheoryTaskBoundaryHandler:
    adjudicator_id: str
    executor_kind: str
    validator: BoundaryValidator
    journal_authority: str
    required_request_extensions: frozenset[str]
    optional_request_extensions: frozenset[str]
    requires_selection_evidence: bool

    def __post_init__(self) -> None:
        if (
            not self.adjudicator_id
            or self.executor_kind
            not in {FORMALIZATION_CAMPAIGN_EXECUTOR, DATA_ONLY_WITNESS_EXECUTOR}
            or not callable(self.validator)
            or not self.journal_authority
            or self.required_request_extensions & self.optional_request_extensions
            or any(
                not str(field).strip()
                for field in self.required_request_extensions
                | self.optional_request_extensions
            )
        ):
            raise ValueError("theory-task boundary handler is incomplete")

    def work_reservation(
        self, verification_plan: Mapping[str, Any]
    ) -> dict[str, int]:
        if self.executor_kind != FORMALIZATION_CAMPAIGN_EXECUTOR:
            return {}
        timeout_ms = int(verification_plan.get("formal_task_timeout_ms", 180_000))
        if timeout_ms < 1:
            raise ValueError("formal-task timeout must be positive")
        return {
            "formal_peer_attempts": 1,
            "formal_peer_millis": timeout_ms,
            "lean_attempts": 1,
            "lean_millis": timeout_ms,
        }

    def evidence_status(self, boundary_row: Mapping[str, Any]) -> str:
        status = str(boundary_row.get("status") or "")
        if self.executor_kind == FORMALIZATION_CAMPAIGN_EXECUTOR:
            return "proved" if status.startswith("kernel_verified") else "unresolved"
        return "witnessed" if status == "witness_verified" else "unresolved"


def _handlers() -> dict[str, TheoryTaskBoundaryHandler]:
    from ztare.leanmill.formal_task_boundary import (
        GOVERNED_FORMAL_COUNTEREXAMPLE_ADJUDICATOR,
        validate_formal_task_boundary_result,
    )
    from ztare.leanmill.witness_construction_boundary import (
        GOVERNED_WITNESS_CONSTRUCTION_ADJUDICATOR,
        validate_witness_construction_boundary_result,
    )

    rows = (
        TheoryTaskBoundaryHandler(
            adjudicator_id=GOVERNED_FORMAL_COUNTEREXAMPLE_ADJUDICATOR,
            executor_kind=FORMALIZATION_CAMPAIGN_EXECUTOR,
            validator=validate_formal_task_boundary_result,
            journal_authority="frontier_boundary_formal_task_join",
            required_request_extensions=frozenset(),
            optional_request_extensions=frozenset({"finite_witness_residual"}),
            requires_selection_evidence=True,
        ),
        TheoryTaskBoundaryHandler(
            adjudicator_id=GOVERNED_WITNESS_CONSTRUCTION_ADJUDICATOR,
            executor_kind=DATA_ONLY_WITNESS_EXECUTOR,
            validator=validate_witness_construction_boundary_result,
            journal_authority="frontier_boundary_witness_construction_join",
            required_request_extensions=frozenset({"witness_construction"}),
            optional_request_extensions=frozenset(),
            requires_selection_evidence=False,
        ),
    )
    handlers = {row.adjudicator_id: row for row in rows}
    if len(handlers) != len(rows):
        raise ValueError("theory-task boundary handler registry duplicated an identity")
    return handlers


def registered_theory_task_boundary_handler(
    adjudicator_id: str,
) -> TheoryTaskBoundaryHandler | None:
    return _handlers().get(str(adjudicator_id))


def require_theory_task_boundary_handler(
    contract: TaskDischargeContract,
) -> TheoryTaskBoundaryHandler:
    handler = registered_theory_task_boundary_handler(contract.adjudicator_id)
    if handler is None:
        raise ValueError(
            "frozen theory task has no registered boundary handler: "
            + contract.adjudicator_id
        )
    return handler


def validate_registered_theory_task_boundary_result(
    contract: TaskDischargeContract,
    value: Mapping[str, Any],
) -> dict[str, Any]:
    handler = require_theory_task_boundary_handler(contract)
    return handler.validator(contract, value)


def theory_task_executor_kind(contract: TaskDischargeContract) -> str:
    return require_theory_task_boundary_handler(contract).executor_kind


def theory_task_request_extension_contract(
    contract: TaskDischargeContract,
) -> tuple[frozenset[str], frozenset[str]]:
    handler = registered_theory_task_boundary_handler(contract.adjudicator_id)
    if handler is None:
        # Adapter-local discharge contracts do not enter the frontier-boundary
        # executor registry.  They retain the closed base request envelope and
        # are adjudicated through their owning adapter capability.
        return frozenset(), frozenset()
    return (
        handler.required_request_extensions,
        handler.optional_request_extensions,
    )


def theory_task_requires_selection_evidence(
    contract: TaskDischargeContract,
) -> bool:
    handler = registered_theory_task_boundary_handler(contract.adjudicator_id)
    # An adapter-local task still selects a presentation, so it keeps the
    # standard evaluator-bound evidence obligation.  Only a reviewed handler
    # may explicitly remove that obligation (the data-only witness route).
    return True if handler is None else handler.requires_selection_evidence


def theory_task_work_reservation(
    contract: TaskDischargeContract,
    verification_plan: Mapping[str, Any],
) -> dict[str, int]:
    return require_theory_task_boundary_handler(contract).work_reservation(
        verification_plan
    )


def theory_task_journal_projection(
    contract: TaskDischargeContract,
    boundary_row: Mapping[str, Any],
) -> dict[str, str]:
    handler = require_theory_task_boundary_handler(contract)
    return {
        "evidence_status": handler.evidence_status(boundary_row),
        "authority": handler.journal_authority,
    }


__all__ = [
    "DATA_ONLY_WITNESS_EXECUTOR",
    "FORMALIZATION_CAMPAIGN_EXECUTOR",
    "TheoryTaskBoundaryHandler",
    "registered_theory_task_boundary_handler",
    "require_theory_task_boundary_handler",
    "theory_task_executor_kind",
    "theory_task_request_extension_contract",
    "theory_task_requires_selection_evidence",
    "theory_task_journal_projection",
    "theory_task_work_reservation",
    "validate_registered_theory_task_boundary_result",
]
