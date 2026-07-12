"""Context-aware witnessed failure memory for theory exploration.

This is the theory-search analogue of the solver's ``NoGoodStore``.  It uses
the shared :class:`ztare.common.conflict_ledger.ConflictLedger` protocol, but
keeps theory identity separate from Lean-statement identity.  A row is useful
only while its witness replays in the current semantic context.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from ztare.common.conflict_ledger import ConflictClause
from ztare.leanmill.common import append_jsonl_locked
from ztare.leanmill.theory_ir import content_hash


WitnessReplay = Callable[[Mapping[str, Any], str], bool]
THEORY_CONFLICT_SCHEMA = "leanmill.theory_conflict.v1"


@dataclass(frozen=True)
class TheoryConflictRecord:
    clause: ConflictClause
    context_hash: str
    source_context_hash: str
    witness_ref: str
    witness_payload: Mapping[str, Any]
    sealed: bool = False


class TheoryConflictLedger:
    """Persist and recall only witnessed clauses that replay in this context."""

    def __init__(
        self,
        *,
        context_hash: str,
        replay_witness: WitnessReplay,
        path: str | Path | None = None,
    ) -> None:
        if not context_hash:
            raise ValueError("context_hash must be non-empty")
        self.context_hash = context_hash
        self._replay_witness = replay_witness
        self.path = Path(path) if path is not None else None
        self._records: dict[str, TheoryConflictRecord] = {}
        self._seen_record_ids: set[str] = set()
        if self.path is not None and self.path.exists():
            self._load()

    def _load(self) -> None:
        assert self.path is not None
        for line_number, line in enumerate(
            self.path.read_text(encoding="utf-8").splitlines(), 1
        ):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"invalid theory conflict ledger line {line_number}: {exc.msg}"
                ) from exc
            if not isinstance(row, Mapping):
                raise ValueError(
                    f"invalid theory conflict ledger line {line_number}: object required"
                )
            required = {
                "schema",
                "record_sha256",
                "candidate_signature",
                "context_hash",
                "witness_ref",
                "witness_payload",
                "witness_summary",
                "sealed",
            }
            if set(row) != required or row.get("schema") != THEORY_CONFLICT_SCHEMA:
                raise ValueError(
                    f"invalid theory conflict ledger line {line_number}: schema mismatch"
                )
            core = {key: value for key, value in row.items() if key != "record_sha256"}
            record_id = str(row["record_sha256"])
            if record_id != content_hash(core):
                raise ValueError(
                    f"invalid theory conflict ledger line {line_number}: digest mismatch"
                )
            payload = row["witness_payload"]
            if not isinstance(payload, Mapping):
                raise ValueError(
                    f"invalid theory conflict ledger line {line_number}: witness object required"
                )
            self._seen_record_ids.add(record_id)
            if self._replay_witness(payload, self.context_hash):
                self._project(row, source_context_hash=str(row["context_hash"]))

    def _project(
        self,
        row: Mapping[str, Any],
        *,
        source_context_hash: str,
    ) -> TheoryConflictRecord:
        signature = str(row["candidate_signature"])
        witness_ref = str(row["witness_ref"])
        payload = row["witness_payload"]
        sealed = bool(row.get("sealed", False))
        conflict_kind = str(payload.get("kind") or "witnessed_conflict")
        clause = ConflictClause(
            signature=signature,
            receipts_refs=(witness_ref,),
            witness_summary=(
                "sealed witness"
                if sealed
                else str(row.get("witness_summary") or "replayed witness")
            ),
            provenance={
                "context_hash": self.context_hash,
                "source_context_hash": source_context_hash,
                "witness_ref": witness_ref,
                "conflict_kind": conflict_kind,
            },
            defeasible=True,
        )
        record = TheoryConflictRecord(
            clause=clause,
            context_hash=self.context_hash,
            source_context_hash=source_context_hash,
            witness_ref=witness_ref,
            witness_payload=dict(payload),
            sealed=sealed,
        )
        self._records[signature] = record
        return record

    def learn(self, conflict_receipt: Any) -> ConflictClause:
        if not isinstance(conflict_receipt, Mapping):
            raise ValueError("conflict receipt must be an object")
        required = {"candidate_signature", "context_hash", "witness_ref", "witness_payload"}
        if not required <= set(conflict_receipt):
            raise ValueError("conflict receipt lacks a replayable witness")
        context_hash = str(conflict_receipt["context_hash"])
        if context_hash != self.context_hash:
            raise ValueError("conflict receipt belongs to another context")
        signature = str(conflict_receipt["candidate_signature"])
        witness_ref = str(conflict_receipt["witness_ref"])
        payload = conflict_receipt["witness_payload"]
        if not signature or not witness_ref or not isinstance(payload, Mapping):
            raise ValueError("conflict identity and witness must be non-empty")
        if not self._replay_witness(payload, context_hash):
            raise ValueError("conflict witness does not replay")
        sealed = bool(conflict_receipt.get("sealed", False))
        core = {
            "schema": THEORY_CONFLICT_SCHEMA,
            "candidate_signature": signature,
            "context_hash": context_hash,
            "witness_ref": witness_ref,
            "witness_payload": dict(payload),
            "witness_summary": str(
                conflict_receipt.get("witness_summary") or "replayed witness"
            ),
            "sealed": sealed,
        }
        record_id = content_hash(core)
        row = {**core, "record_sha256": record_id}
        if self.path is not None and record_id not in self._seen_record_ids:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            append_jsonl_locked(self.path, row, ensure_ascii=True)
            self._seen_record_ids.add(record_id)
        return self._project(row, source_context_hash=context_hash).clause

    def blocks(self, candidate_signature: str) -> ConflictClause | None:
        record = self._records.get(str(candidate_signature))
        if record is None or record.context_hash != self.context_hash:
            return None
        if not self._replay_witness(record.witness_payload, self.context_hash):
            return None
        return record.clause

    def revive(self, evidence_card: Any) -> dict[str, Any]:
        """Move to a new context and retain only witnesses that replay there."""
        if not isinstance(evidence_card, Mapping) or not evidence_card.get("context_hash"):
            raise ValueError("revival requires a target context_hash")
        new_context = str(evidence_card["context_hash"])
        retained: dict[str, TheoryConflictRecord] = {}
        dropped: list[str] = []
        for signature, record in self._records.items():
            if self._replay_witness(record.witness_payload, new_context):
                provenance = dict(record.clause.provenance or {})
                provenance["context_hash"] = new_context
                retained[signature] = TheoryConflictRecord(
                    clause=ConflictClause(
                        signature=record.clause.signature,
                        receipts_refs=record.clause.receipts_refs,
                        witness_summary=record.clause.witness_summary,
                        provenance=provenance,
                        defeasible=True,
                    ),
                    context_hash=new_context,
                    source_context_hash=record.source_context_hash,
                    witness_ref=record.witness_ref,
                    witness_payload=record.witness_payload,
                    sealed=record.sealed,
                )
            else:
                dropped.append(signature)
        self.context_hash = new_context
        self._records = retained
        return {"context_hash": new_context, "retained": sorted(retained), "dropped": sorted(dropped)}

    def open_clauses(self) -> list[ConflictClause]:
        return [self._records[key].clause for key in sorted(self._records)]

    def navigator_rows(self) -> list[dict[str, Any]]:
        """Projection that never exposes sealed witness payloads."""
        return [
            {
                "candidate_signature": key,
                "context_hash": record.context_hash,
                "witness_ref": record.witness_ref,
                "witness_summary": record.clause.witness_summary,
                "conflict_kind": str(
                    (record.clause.provenance or {}).get("conflict_kind") or ""
                ),
            }
            for key, record in sorted(self._records.items())
        ]


def theory_presentation_signature(
    signature_hash: str, formula_ids: tuple[str, ...] | list[str]
) -> str:
    """Context-independent identity; context applicability is witness-replayed."""

    core = {
        "signature_sha256": str(signature_hash),
        "formula_ids": sorted(str(row) for row in formula_ids),
    }
    return "theory-presentation:" + content_hash(core).split(":", 1)[-1]


def theory_implication_signature(
    signature_hash: str,
    premise_formula_ids: tuple[str, ...] | list[str],
    target_formula_id: str,
) -> str:
    """Identity for one conditional consequence, independent of context epoch."""

    core = {
        "signature_sha256": str(signature_hash),
        "premise_formula_ids": sorted(str(row) for row in premise_formula_ids),
        "target_formula_id": str(target_formula_id),
    }
    return "theory-implication:" + content_hash(core).split(":", 1)[-1]


def _formal_context_witness_replay(context: Any) -> WitnessReplay:
    def replay(payload: Mapping[str, Any], target_context_hash: str) -> bool:
        if target_context_hash != context.context_hash:
            return False
        kind = str(payload.get("kind") or "")
        if kind == "zero_residual_presentation":
            formula_ids = tuple(sorted(str(row) for row in payload.get("formula_ids") or ()))
            if not formula_ids or any(row not in context.formula_ids for row in formula_ids):
                return False
            try:
                from ztare.leanmill.theory_interest import (
                    theory_residual_information_yield,
                )

                signal = theory_residual_information_yield(context, formula_ids)
            except (KeyError, TypeError, ValueError):
                return False
            return (
                not signal.residual_consequence_ids
                and not signal.cheap_baseline_inconclusive_ids
                and signal.coordinates.identification_bits == 0
            )
        if kind != "finite_countermodel":
            return False
        receipt = payload.get("countermodel_receipt")
        if not isinstance(receipt, Mapping):
            return False
        receipt_core = {
            key: value for key, value in receipt.items() if key != "receipt_sha256"
        }
        if (
            receipt.get("receipt_sha256") != content_hash(receipt_core)
            or receipt.get("status") != "countermodel_found"
        ):
            return False
        premises = tuple(
            sorted(str(row) for row in payload.get("premise_formula_ids") or ())
        )
        target_id = str(payload.get("target_formula_id") or "")
        axiom_map = {
            row.formula_id: row.axiom
            for row in getattr(context, "formula_profiles", ())
            if hasattr(row, "axiom")
        }
        if target_id not in axiom_map or any(row not in axiom_map for row in premises):
            return False
        if tuple(sorted(str(row) for row in receipt.get("premise_formula_ids") or ())) != premises:
            return False
        if str(receipt.get("target_formula_id") or "") != target_id:
            return False
        receipt_signature = str(receipt.get("signature_sha256") or "")
        if receipt_signature and receipt_signature != context.signature.content_hash:
            return False
        expected_base = tuple(
            sorted("formula:" + row.semantic_hash for row in context.base_axioms)
        )
        receipt_base = tuple(sorted(str(row) for row in receipt.get("base_formula_ids") or ()))
        if receipt_base and receipt_base != expected_base:
            return False
        witness = receipt.get("witness")
        if not isinstance(witness, Mapping):
            return False
        try:
            from ztare.leanmill.finite_model import (
                FiniteModel,
                evaluate_axiom,
                validate_model,
            )

            model = FiniteModel.from_json(witness)
            validate_model(context.signature, model)
            if not all(
                evaluate_axiom(context.signature, axiom, model)
                for axiom in (
                    *context.base_axioms,
                    *(axiom_map[row] for row in premises),
                )
            ):
                return False
            return not evaluate_axiom(context.signature, axiom_map[target_id], model)
        except (KeyError, TypeError, ValueError):
            return False

    return replay


def open_theory_conflict_ledger(
    context: Any, path: str | Path | None = None
) -> TheoryConflictLedger:
    """Open the canonical theory-search no-good memory for one exact context."""

    return TheoryConflictLedger(
        context_hash=context.context_hash,
        replay_witness=_formal_context_witness_replay(context),
        path=path,
    )


def zero_residual_conflict_receipt(
    context: Any, rejection: Mapping[str, Any]
) -> dict[str, Any]:
    formula_ids = tuple(sorted(str(row) for row in rejection.get("formula_ids") or ()))
    residual = rejection.get("residual_yield")
    if not formula_ids or not isinstance(residual, Mapping):
        raise ValueError("zero-residual conflict requires formulas and residual coordinates")
    witness_ref = str(rejection.get("selection_receipt_id") or "")
    if not witness_ref:
        raise ValueError("zero-residual conflict requires a selection receipt")
    return {
        "candidate_signature": theory_presentation_signature(
            context.signature.content_hash, formula_ids
        ),
        "context_hash": context.context_hash,
        "witness_ref": witness_ref,
        "witness_payload": {
            "kind": "zero_residual_presentation",
            "formula_ids": list(formula_ids),
            "baseline_ref": str(residual.get("baseline_ref") or ""),
        },
        "witness_summary": (
            "host replay found zero residual information after "
            + str(residual.get("baseline_ref") or "the named baseline")
        ),
    }


def finite_countermodel_conflict_receipt(
    context: Any,
    premise_formula_ids: tuple[str, ...] | list[str],
    target_formula_id: str,
    countermodel_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    premises = tuple(sorted(str(row) for row in premise_formula_ids))
    target = str(target_formula_id)
    witness_ref = str(countermodel_receipt.get("receipt_sha256") or "")
    if not witness_ref:
        raise ValueError("finite countermodel conflict requires a receipt digest")
    return {
        "candidate_signature": theory_implication_signature(
            context.signature.content_hash, premises, target
        ),
        "context_hash": context.context_hash,
        "witness_ref": witness_ref,
        "witness_payload": {
            "kind": "finite_countermodel",
            "premise_formula_ids": list(premises),
            "target_formula_id": target,
            "countermodel_receipt": dict(countermodel_receipt),
        },
        "witness_summary": "host-replayed finite model satisfies the premises and refutes the target",
    }


__all__ = [
    "THEORY_CONFLICT_SCHEMA",
    "TheoryConflictLedger",
    "TheoryConflictRecord",
    "finite_countermodel_conflict_receipt",
    "open_theory_conflict_ledger",
    "theory_implication_signature",
    "theory_presentation_signature",
    "zero_residual_conflict_receipt",
]
