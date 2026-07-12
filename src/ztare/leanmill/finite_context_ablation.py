"""Logical premise ablation witnessed inside an exact finite context."""
from __future__ import annotations

from typing import Any, Sequence

from ztare.leanmill.finite_model import evaluate_axiom
from ztare.leanmill.finite_theory_context import FormalTheoryContext
from ztare.leanmill.theory_ir import content_hash


def audit_finite_context_single_premises(
    context: FormalTheoryContext,
    premise_formula_ids: Sequence[str],
    target_formula_id: str,
) -> dict[str, Any]:
    """Refute each singleton implication with a replayed finite model."""

    premises = tuple(sorted(dict.fromkeys(map(str, premise_formula_ids))))
    target_id = str(target_formula_id)
    formulas = {row.formula_id: row.axiom for row in context.formula_profiles}
    if target_id not in formulas or any(row not in formulas for row in premises):
        raise ValueError("single-premise ablation references an unknown formula")

    witnesses = []
    unresolved = list(premises) if len(premises) < 2 else []
    for premise_id in premises if len(premises) >= 2 else ():
        record = context.implication_countermodel((premise_id,), target_id)
        if record is None:
            unresolved.append(premise_id)
            continue
        model = record.model
        if not all(
            evaluate_axiom(context.signature, axiom, model)
            for axiom in context.base_axioms
        ):
            raise RuntimeError("finite-context ablation witness violates base theory")
        if not evaluate_axiom(context.signature, formulas[premise_id], model):
            raise RuntimeError("finite-context ablation witness violates its premise")
        if evaluate_axiom(context.signature, formulas[target_id], model):
            raise RuntimeError("finite-context ablation witness satisfies the target")
        witnesses.append(
            {
                "premise_formula_id": premise_id,
                "target_formula_id": target_id,
                "model_id": record.model_id,
                "stratum_id": record.stratum_id,
                "model": model.to_json(),
                "model_sha256": model.content_hash(context.signature),
                "multiplicity": int(getattr(record, "multiplicity", 1)),
                "host_replay": {
                    "base_holds": True,
                    "premise_holds": True,
                    "target_fails": True,
                },
            }
        )
    core = {
        "schema": "leanmill.finite_context_single_premise_ablation.v1",
        "status": (
            "certified_single_premise_nonimplication"
            if not unresolved
            else "unresolved_single_premise_implication"
        ),
        "authority": "exact_finite_context_countermodel_plus_host_replay",
        "context_hash": context.context_hash,
        "signature_sha256": context.signature.content_hash,
        "base_formula_ids": [
            "formula:" + row.semantic_hash for row in context.base_axioms
        ],
        "premise_formula_ids": list(premises),
        "target_formula_id": target_id,
        "singleton_countermodels": witnesses,
        "unresolved_premise_formula_ids": unresolved,
        "claim_boundary": (
            "each witnessed singleton implication is logically refuted by one model; "
            "no absence claim is inferred"
        ),
    }
    return {**core, "receipt_sha256": content_hash(core)}


__all__ = ["audit_finite_context_single_premises"]
