"""Identity and comparison objects for agent-authored theory programs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ztare.common.task_discharge import TaskDischargeContract
from ztare.leanmill.theory_ir import content_hash


THEORY_PROGRAM_V1 = "leanmill.theory_program.v1"
THEORY_PROGRAM_V2 = "leanmill.theory_program.v2"
FORMULA_PREDICTION_ADJUDICATOR = "leanmill.theory_program_prediction.v1"


@dataclass(frozen=True)
class TheoryProgram:
    campaign_id: str
    lineage_id: str
    context_hash: str
    context_epoch: int
    presentation_formula_ids: tuple[str, ...]
    prediction_formula_ids: tuple[str, ...]
    selection_receipt_id: str
    schema: str = THEORY_PROGRAM_V1
    task_discharge_contracts: tuple[TaskDischargeContract, ...] = ()

    def __post_init__(self) -> None:
        if self.schema not in {THEORY_PROGRAM_V1, THEORY_PROGRAM_V2}:
            raise ValueError("unsupported theory program schema")
        for field_name in (
            "campaign_id",
            "lineage_id",
            "context_hash",
            "selection_receipt_id",
        ):
            if not str(getattr(self, field_name)).strip():
                raise ValueError(f"theory program requires {field_name}")
        if self.context_epoch < 0:
            raise ValueError("theory program epoch must be nonnegative")
        if not self.presentation_formula_ids:
            raise ValueError("theory program requires hypotheses")
        if not self.prediction_formula_ids and not self.task_discharge_contracts:
            raise ValueError("theory program requires a prediction or task")
        if self.schema == THEORY_PROGRAM_V1 and self.task_discharge_contracts:
            raise ValueError("v1 theory programs cannot carry task contracts")
        if self.schema == THEORY_PROGRAM_V2 and not self.task_discharge_contracts:
            raise ValueError("v2 theory programs require a task contract")
        if len(set(self.presentation_formula_ids)) != len(
            self.presentation_formula_ids
        ) or len(set(self.prediction_formula_ids)) != len(self.prediction_formula_ids):
            raise ValueError("theory program formula identities must be unique")
        if set(self.presentation_formula_ids) & set(self.prediction_formula_ids):
            raise ValueError("theory program predictions must be outside its presentation")
        if any(
            not isinstance(row, TaskDischargeContract)
            for row in self.task_discharge_contracts
        ):
            raise TypeError("theory program tasks must be task-discharge contracts")
        task_hashes = tuple(row.sha256 for row in self.task_discharge_contracts)
        if len(set(task_hashes)) != len(task_hashes):
            raise ValueError("theory program task identities must be unique")

    @property
    def program_id(self) -> str:
        return "theory-program:" + content_hash(self.to_json(include_id=False))

    def to_json(self, *, include_id: bool = True) -> dict[str, Any]:
        core = {
            "schema": self.schema,
            "campaign_id": self.campaign_id,
            "lineage_id": self.lineage_id,
            "context_hash": self.context_hash,
            "context_epoch": self.context_epoch,
            "presentation_formula_ids": list(self.presentation_formula_ids),
            "prediction_formula_ids": list(self.prediction_formula_ids),
            "selection_receipt_id": self.selection_receipt_id,
            "authority": "frozen_navigator_choice_host_validated",
        }
        if self.schema == THEORY_PROGRAM_V2:
            core["task_discharge_contracts"] = [
                row.to_dict() for row in self.task_discharge_contracts
            ]
        return {**core, "program_id": self.program_id} if include_id else core

    def executable_task_contracts(self) -> tuple[TaskDischargeContract, ...]:
        """Project every program output into the shared task-discharge algebra.

        Formula predictions keep their historical representation and are
        losslessly lowered here.  New output kinds arrive already typed after
        host validation; neither path gives the common kernel substrate
        vocabulary or stopping authority.
        """

        lowered = tuple(
            formula_prediction_task_contract(self, target_id)
            for target_id in self.prediction_formula_ids
        )
        return lowered + self.task_discharge_contracts

    @classmethod
    def from_json(cls, value: Any) -> "TheoryProgram":
        if not isinstance(value, Mapping):
            raise ValueError("theory program must be an object")
        schema = str(value.get("schema") or "")
        required = {
            "schema",
            "campaign_id",
            "lineage_id",
            "context_hash",
            "context_epoch",
            "presentation_formula_ids",
            "prediction_formula_ids",
            "selection_receipt_id",
            "authority",
            "program_id",
        }
        if schema == THEORY_PROGRAM_V2:
            required.add("task_discharge_contracts")
        if set(value) != required:
            raise ValueError("theory program fields do not match the frozen schema")
        if value.get("authority") != "frozen_navigator_choice_host_validated":
            raise ValueError("theory program has unsupported authority")
        raw_tasks = value.get("task_discharge_contracts") or []
        if not isinstance(raw_tasks, list) or any(
            not isinstance(row, Mapping) for row in raw_tasks
        ):
            raise ValueError("theory program task contracts must be an array of objects")
        program = cls(
            schema=schema,
            campaign_id=str(value["campaign_id"]),
            lineage_id=str(value["lineage_id"]),
            context_hash=str(value["context_hash"]),
            context_epoch=int(value["context_epoch"]),
            presentation_formula_ids=tuple(
                str(row) for row in value["presentation_formula_ids"]
            ),
            prediction_formula_ids=tuple(
                str(row) for row in value["prediction_formula_ids"]
            ),
            selection_receipt_id=str(value["selection_receipt_id"]),
            task_discharge_contracts=tuple(
                TaskDischargeContract.from_dict(row) for row in raw_tasks
            ),
        )
        if value.get("program_id") != program.program_id:
            raise ValueError("theory program digest mismatch")
        return program


def formula_prediction_task_contract(
    program: TheoryProgram,
    target_formula_id: str,
) -> TaskDischargeContract:
    """Lower one legacy prediction without changing the program's wire form."""

    target = str(target_formula_id)
    if target not in program.prediction_formula_ids:
        raise ValueError("formula task target is not a prediction of this program")
    identity = {
        "program_id": program.program_id,
        "target_formula_id": target,
    }
    return TaskDischargeContract(
        contract_id="theory-task:" + content_hash(identity),
        adjudicator_id=FORMULA_PREDICTION_ADJUDICATOR,
        lifecycle_scope=program.campaign_id,
        owner=program.lineage_id,
        parameters={
            "kind": "theory_program_prediction",
            "program_id": program.program_id,
            "context_hash": program.context_hash,
            "context_epoch": program.context_epoch,
            "presentation_formula_ids": list(program.presentation_formula_ids),
            "target_formula_id": target,
        },
    )


def derive_lineage_id(*, campaign_id: str, attempt_id: str, branch: int = 0) -> str:
    if branch < 0:
        raise ValueError("lineage branch must be nonnegative")
    return "theory-lineage:" + content_hash(
        {
            "campaign_id": campaign_id,
            "attempt_id": attempt_id,
            "branch": branch,
        }
    )


def derive_context_lineage_id(
    *,
    campaign_id: str,
    attempt_id: str,
    context_epoch: int,
    branch: int = 0,
) -> str:
    """Start a fresh isolated generation after late cross-lineage synthesis."""

    if context_epoch < 0:
        raise ValueError("lineage context epoch must be nonnegative")
    generation_attempt = (
        attempt_id
        if context_epoch == 0
        else f"{attempt_id}:context-epoch:{context_epoch}"
    )
    return derive_lineage_id(
        campaign_id=campaign_id,
        attempt_id=generation_attempt,
        branch=branch,
    )


def compare_host_isolated_theory_programs(
    programs: Sequence[TheoryProgram],
) -> dict[str, Any]:
    """Compare host-isolated lineages without overstating independence."""

    rows = tuple(programs)
    if len(rows) < 2 or len({row.lineage_id for row in rows}) != len(rows):
        raise ValueError("program comparison requires distinct host-isolated lineages")
    contexts = {(row.context_hash, row.context_epoch) for row in rows}
    if len(contexts) != 1:
        raise ValueError("program comparison requires one frozen source context")
    if len({row.campaign_id for row in rows}) != 1:
        raise ValueError("program comparison cannot cross campaigns")
    presentations = [set(row.presentation_formula_ids) for row in rows]
    predictions = [set(row.prediction_formula_ids) for row in rows]
    tasks = [
        {task.sha256 for task in row.task_discharge_contracts}
        for row in rows
    ]
    common_hypotheses = set.intersection(*presentations)
    common_predictions = set.intersection(*predictions)
    core = {
        "schema": "leanmill.host_isolated_theory_program_comparison.v1",
        "context_hash": rows[0].context_hash,
        "context_epoch": rows[0].context_epoch,
        "program_ids": [row.program_id for row in rows],
        "lineage_ids": [row.lineage_id for row in rows],
        "common_hypothesis_ids": sorted(common_hypotheses),
        "common_prediction_ids": sorted(common_predictions),
        "lineage_unique_hypothesis_ids": {
            row.lineage_id: sorted(
                presentations[index]
                - set().union(
                    *(presentations[:index] + presentations[index + 1 :])
                )
            )
            for index, row in enumerate(rows)
        },
        "lineage_unique_prediction_ids": {
            row.lineage_id: sorted(
                predictions[index]
                - set().union(*(predictions[:index] + predictions[index + 1 :]))
            )
            for index, row in enumerate(rows)
        },
        "late_synthesis_candidate": {
            "presentation_formula_ids": sorted(set().union(*presentations)),
            "prediction_formula_ids": sorted(set().union(*predictions)),
            "status": "proposal_only_requires_fresh_context_replay",
        },
        "authority": "diagnostic_comparison_only",
    }
    if any(tasks):
        core["schema"] = "leanmill.host_isolated_theory_program_comparison.v2"
        core["common_task_contract_sha256s"] = sorted(set.intersection(*tasks))
        core["lineage_unique_task_contract_sha256s"] = {
            row.lineage_id: sorted(
                tasks[index] - set().union(*(tasks[:index] + tasks[index + 1 :]))
            )
            for index, row in enumerate(rows)
        }
        core["late_synthesis_candidate"]["task_contract_sha256s"] = sorted(
            set().union(*tasks)
        )
    return {**core, "receipt_sha256": content_hash(core)}


def compare_independent_theory_programs(
    programs: Sequence[TheoryProgram],
) -> dict[str, Any]:
    """Compatibility alias for the earlier overbroad function name."""

    return compare_host_isolated_theory_programs(programs)


__all__ = [
    "FORMULA_PREDICTION_ADJUDICATOR",
    "THEORY_PROGRAM_V1",
    "THEORY_PROGRAM_V2",
    "TheoryProgram",
    "compare_host_isolated_theory_programs",
    "compare_independent_theory_programs",
    "derive_context_lineage_id",
    "derive_lineage_id",
    "formula_prediction_task_contract",
]
