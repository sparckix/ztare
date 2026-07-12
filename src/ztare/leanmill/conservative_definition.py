"""Conservative term macros for measured theory-language expansion."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from ztare.leanmill.theory_ir import (
    AxiomFormula,
    Binder,
    Formula,
    OperationSymbol,
    Term,
    TheorySignature,
    content_hash,
    validate_axiom,
)


@dataclass(frozen=True)
class ConservativeOperationDefinition:
    """A derived operation whose meaning expands into the prior signature.

    This is representation, rather than added mathematical strength.  The
    signature digest and a host typecheck bind that distinction explicitly.
    """

    name: str
    parameters: tuple[Binder, ...]
    result_sort: str
    body: Term
    theory_signature_sha256: str
    source_motif_refs: tuple[str, ...]
    schema: str = "leanmill.conservative_operation_definition.v1"

    def __post_init__(self) -> None:
        OperationSymbol(
            self.name,
            tuple(parameter.sort for parameter in self.parameters),
            self.result_sort,
        )
        names = tuple(parameter.name for parameter in self.parameters)
        if not names or len(names) != len(set(names)):
            raise ValueError("definition parameters must be nonempty and unique")
        if not self.theory_signature_sha256 or not self.source_motif_refs:
            raise ValueError("definition requires prior-signature and motif evidence")
        if not _term_contains_application(self.body):
            raise ValueError("a variable alias is not a useful derived definition")

    @property
    def arity(self) -> int:
        return len(self.parameters)

    @property
    def definition_id(self) -> str:
        return "definition:" + content_hash(self.to_json())

    def to_json(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "name": self.name,
            "parameters": [row.to_json() for row in self.parameters],
            "result_sort": self.result_sort,
            "body": self.body.to_json(),
            "theory_signature_sha256": self.theory_signature_sha256,
            "source_motif_refs": list(self.source_motif_refs),
            "conservative": True,
            "expansion_language": "prior_theory_signature_only",
        }

    def expand(self, arguments: Sequence[Term]) -> Term:
        if len(arguments) != self.arity:
            raise ValueError("macro argument count does not match definition arity")
        substitutions = {
            parameter.name: argument
            for parameter, argument in zip(self.parameters, arguments)
        }

        def substitute(term: Term) -> Term:
            if term.kind == "var":
                try:
                    return substitutions[term.name]
                except KeyError as exc:
                    raise ValueError("definition body contains an unbound parameter") from exc
            return Term.app(term.name, *(substitute(row) for row in term.args))

        return substitute(self.body)


def build_conservative_operation_definition(
    signature: TheorySignature,
    *,
    name: str,
    parameters: Sequence[Binder],
    result_sort: str,
    body: Term,
    source_motif_refs: Sequence[str],
) -> ConservativeOperationDefinition:
    """Typecheck a derived operation against exactly the prior signature."""

    params = tuple(parameters)
    if name in signature.operation_map or name in signature.relation_map:
        raise ValueError("derived operation name collides with the prior signature")
    probe_name = "definition_result"
    parameter_names = {row.name for row in params}
    while probe_name in parameter_names:
        probe_name += "_"
    probe = AxiomFormula(
        "definition_typecheck",
        Formula.forall(
            params + (Binder(probe_name, result_sort),),
            Formula.eq(body, Term.var(probe_name)),
        ),
    )
    validate_axiom(signature, probe)
    return ConservativeOperationDefinition(
        name=name,
        parameters=params,
        result_sort=result_sort,
        body=body,
        theory_signature_sha256=signature.content_hash,
        source_motif_refs=tuple(str(row) for row in source_motif_refs if str(row)),
    )


def _term_contains_application(term: Term) -> bool:
    return term.kind == "app" or any(_term_contains_application(row) for row in term.args)


def _ir_term_cost(term: Term) -> tuple[int, int]:
    if term.kind == "var":
        return 1, 0
    child = [_ir_term_cost(row) for row in term.args]
    return sum(row[0] for row in child), 1 + sum(row[1] for row in child)


def definition_retention_receipt(
    definition: ConservativeOperationDefinition,
    *,
    motif_occurrences: int,
    separated_consequence_class: bool = False,
) -> dict[str, Any]:
    if motif_occurrences < 1:
        raise ValueError("motif_occurrences must be positive")
    # Postfix tokens: body costs leaves+operations; a macro use costs one head
    # plus its arguments. The definition is paid once.
    leaf_count, operation_count = _ir_term_cost(definition.body)
    body_cost = leaf_count + operation_count
    definition_cost = body_cost + definition.arity + 1
    per_use_saved = max(0, body_cost - (definition.arity + 1))
    net_saving = motif_occurrences * per_use_saved - definition_cost
    retained = net_saving > 0 or separated_consequence_class
    core = {
        "schema": "leanmill.conservative_definition_retention.v1",
        "definition_id": definition.definition_id,
        "macro_expansion_verified": True,
        "old_vocabulary_strength_added": False,
        "motif_occurrences": motif_occurrences,
        "definition_cost": definition_cost,
        "per_use_saved": per_use_saved,
        "net_description_saving": net_saving,
        "separated_consequence_class": separated_consequence_class,
        "status": "retained" if retained else "rejected",
        "new_context_epoch_required": retained,
    }
    return {**core, "receipt_sha256": content_hash(core)}


__all__ = [
    "ConservativeOperationDefinition",
    "build_conservative_operation_definition",
    "definition_retention_receipt",
]
