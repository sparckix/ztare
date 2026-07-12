"""Identity and comparison objects for agent-authored theory programs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ztare.leanmill.theory_ir import content_hash


@dataclass(frozen=True)
class TheoryProgram:
    campaign_id: str
    lineage_id: str
    context_hash: str
    context_epoch: int
    presentation_formula_ids: tuple[str, ...]
    prediction_formula_ids: tuple[str, ...]
    selection_receipt_id: str
    schema: str = "leanmill.theory_program.v1"

    def __post_init__(self) -> None:
        if self.schema != "leanmill.theory_program.v1":
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
        if not self.presentation_formula_ids or not self.prediction_formula_ids:
            raise ValueError("theory program requires hypotheses and predictions")
        if len(set(self.presentation_formula_ids)) != len(
            self.presentation_formula_ids
        ) or len(set(self.prediction_formula_ids)) != len(self.prediction_formula_ids):
            raise ValueError("theory program formula identities must be unique")
        if set(self.presentation_formula_ids) & set(self.prediction_formula_ids):
            raise ValueError("theory program predictions must be outside its presentation")

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
        return {**core, "program_id": self.program_id} if include_id else core

    @classmethod
    def from_json(cls, value: Any) -> "TheoryProgram":
        if not isinstance(value, Mapping):
            raise ValueError("theory program must be an object")
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
        if set(value) != required:
            raise ValueError("theory program fields do not match the frozen schema")
        if value.get("authority") != "frozen_navigator_choice_host_validated":
            raise ValueError("theory program has unsupported authority")
        program = cls(
            schema=str(value["schema"]),
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
        )
        if value.get("program_id") != program.program_id:
            raise ValueError("theory program digest mismatch")
        return program


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
    return {**core, "receipt_sha256": content_hash(core)}


def compare_independent_theory_programs(
    programs: Sequence[TheoryProgram],
) -> dict[str, Any]:
    """Compatibility alias for the earlier overbroad function name."""

    return compare_host_isolated_theory_programs(programs)


__all__ = [
    "TheoryProgram",
    "compare_host_isolated_theory_programs",
    "compare_independent_theory_programs",
    "derive_context_lineage_id",
    "derive_lineage_id",
]
