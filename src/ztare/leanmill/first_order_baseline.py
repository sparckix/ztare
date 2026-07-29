"""Cheap proof-rule baseline for shallow first-order consequences."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations
from typing import Sequence

from ztare.leanmill.theory_ir import AxiomFormula, Binder, Formula, content_hash


@dataclass(frozen=True)
class ExistentialWitnessTransportWitness:
    existential_premise_hash: str
    bridge_premise_hash: str
    target_hash: str
    witness_binder_sorts: tuple[str, ...]
    bridge_witness_positions: tuple[int, ...]
    schema: str = "leanmill.existential_witness_transport.v1"

    def to_json(self) -> dict[str, object]:
        core = {
            "schema": self.schema,
            "existential_premise_hash": self.existential_premise_hash,
            "bridge_premise_hash": self.bridge_premise_hash,
            "target_hash": self.target_hash,
            "witness_binder_sorts": list(self.witness_binder_sorts),
            "bridge_witness_positions": list(self.bridge_witness_positions),
            "proof_rule": "exists_elim_forall_implies_exists_intro",
        }
        return {**core, "receipt_sha256": content_hash(core)}


def _peel(formula: Formula, kind: str) -> tuple[tuple[Binder, ...], Formula]:
    binders: list[Binder] = []
    body = formula
    while body.kind == kind:
        binders.extend(body.binders)
        body = body.formulas[0]
    return tuple(binders), body


def _quantify(kind: str, binders: Sequence[Binder], body: Formula) -> Formula:
    if not binders:
        return body
    if kind == "exists":
        return Formula.exists(tuple(binders), body)
    if kind == "forall":
        return Formula.forall(tuple(binders), body)
    raise ValueError(f"unsupported quantifier kind: {kind}")


def _shape_hash(formula: Formula) -> str:
    # Axiom names do not participate in ``semantic_hash``.  Wrapping free
    # witness variables in the same quantifier lets TheoryIR's existing
    # alpha-normalizer compare the proof-rule fragments without another AST
    # canonicalizer.
    return AxiomFormula("logical_shape", formula).semantic_hash


def existential_witness_transport_witness(
    premises: Sequence[AxiomFormula],
    target: AxiomFormula,
) -> ExistentialWitnessTransportWitness | None:
    """Recognize ``∃x P x`` + ``∀x y, P x → Q x y`` ⇒ ``∃x, ∀y, Q x y``.

    The matcher is symbol-agnostic, alpha-invariant, many-sorted, and permits
    the witness variables to occur anywhere in the bridge's leading universal
    binder block.  It intentionally implements only this fully receiptable
    proof rule; failure to match is inconclusive.
    """

    target_binders, target_body = _peel(target.formula, "exists")
    if not target_binders:
        return None
    target_forall, target_consequent = _peel(target_body, "forall")
    normalized_target = _quantify(
        "exists",
        target_binders,
        _quantify("forall", target_forall, target_consequent),
    )
    target_shape = _shape_hash(normalized_target)

    for existential in premises:
        witness_binders, witness_condition = _peel(
            existential.formula, "exists"
        )
        if not witness_binders or len(witness_binders) != len(target_binders):
            continue
        normalized_condition = _quantify(
            "exists", witness_binders, witness_condition
        )
        condition_shape = _shape_hash(normalized_condition)
        witness_sorts = tuple(row.sort for row in witness_binders)

        for bridge in premises:
            if bridge is existential:
                continue
            universal_binders, implication = _peel(bridge.formula, "forall")
            if implication.kind != "implies":
                continue
            antecedent, consequent = implication.formulas
            count = len(witness_binders)
            for positions in permutations(range(len(universal_binders)), count):
                selected = tuple(universal_binders[index] for index in positions)
                if tuple(row.sort for row in selected) != witness_sorts:
                    continue
                bridge_condition = _quantify("exists", selected, antecedent)
                if _shape_hash(bridge_condition) != condition_shape:
                    continue
                selected_positions = set(positions)
                remaining = tuple(
                    binder
                    for index, binder in enumerate(universal_binders)
                    if index not in selected_positions
                )
                bridge_target = _quantify(
                    "exists",
                    selected,
                    _quantify("forall", remaining, consequent),
                )
                if _shape_hash(bridge_target) != target_shape:
                    continue
                return ExistentialWitnessTransportWitness(
                    existential_premise_hash=existential.semantic_hash,
                    bridge_premise_hash=bridge.semantic_hash,
                    target_hash=target.semantic_hash,
                    witness_binder_sorts=witness_sorts,
                    bridge_witness_positions=tuple(positions),
                )
    return None


__all__ = [
    "ExistentialWitnessTransportWitness",
    "existential_witness_transport_witness",
]
