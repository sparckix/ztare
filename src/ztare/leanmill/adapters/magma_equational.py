"""Optimized anonymous-equational magma campaign adapter."""
from __future__ import annotations

from pathlib import Path
from functools import partial
import re
from typing import Any, Mapping, Sequence

from ztare.leanmill.finite_model import FiniteModel
from ztare.leanmill.finite_table_model_finder import find_finite_countermodel
from ztare.leanmill.finite_model_census import (
    CanonicalModelRecord,
    FiniteModelUniverseReceipt,
    MagmaModelUniverse,
    enumerate_magma_model_universe,
)
from ztare.leanmill.magma_law_universe import (
    MAGMA_GRAMMAR_SCHEMA,
    MagmaLaw,
    MagmaTerm,
    _canonical_law_terms,
    magma_laws_through_order,
)
from ztare.leanmill.source_implication_oracle import (
    SourceImplicationOracle,
    sha256_file,
)
from ztare.leanmill.theory_ir import AxiomFormula, TheorySignature, content_hash


ADAPTER_ID = "magma_equational.v1"
_INFIX_TOKEN = re.compile(r"\s*(◇|\*|\(|\)|[A-Za-z][A-Za-z0-9_]*)")


def _validate_formula_grammar(
    formula_grammar: Mapping[str, Any], *, max_order: int
) -> None:
    declared = formula_grammar.get(
        "max_total_operation_order", formula_grammar.get("max_order")
    )
    schema = formula_grammar.get("schema")
    kind = str(formula_grammar.get("kind") or "")
    if (
        type(declared) is not int
        or declared != max_order
        or (
            schema not in {None, MAGMA_GRAMMAR_SCHEMA}
            or (schema is None and kind and "canonical" not in kind)
        )
    ):
        raise ValueError("magma formula grammar differs from adapter configuration")


def _parse_infix_equation(value: str) -> tuple[MagmaTerm, MagmaTerm]:
    parts = str(value).strip().split("=")
    if len(parts) != 2:
        raise ValueError("source equation must contain exactly one equality")
    variable_ids: dict[str, int] = {}

    def parse_side(text: str) -> MagmaTerm:
        tokens = _INFIX_TOKEN.findall(text)
        if not tokens or _INFIX_TOKEN.sub("", text).strip():
            raise ValueError("source equation contains unsupported magma syntax")
        index = 0

        def atom() -> MagmaTerm:
            nonlocal index
            if index >= len(tokens):
                raise ValueError("source equation ended inside a term")
            token = tokens[index]
            index += 1
            if token == "(":
                term = expression()
                if index >= len(tokens) or tokens[index] != ")":
                    raise ValueError("source equation has unmatched parentheses")
                index += 1
                return term
            if token in {"◇", "*", ")"}:
                raise ValueError("source equation expected a variable")
            variable_ids.setdefault(token, len(variable_ids))
            return MagmaTerm.var(variable_ids[token])

        def expression() -> MagmaTerm:
            nonlocal index
            term = atom()
            while index < len(tokens) and tokens[index] in {"◇", "*"}:
                index += 1
                term = MagmaTerm.app(term, atom())
            return term

        parsed = expression()
        if index != len(tokens):
            raise ValueError("source equation has trailing term syntax")
        return parsed

    return _canonical_law_terms(parse_side(parts[0]), parse_side(parts[1]))


def _law_key(left: MagmaTerm, right: MagmaTerm) -> tuple[str, str]:
    canonical_left, canonical_right = _canonical_law_terms(left, right)
    return canonical_left.postfix(), canonical_right.postfix()


def _map_formula_ids_to_source_nodes(
    laws: Sequence[MagmaLaw],
    *,
    catalog_path: str | Path,
    catalog_sha256: str,
    node_count: int,
    source_ref: str,
) -> tuple[dict[str, int], dict[str, Any]]:
    if sha256_file(catalog_path) != catalog_sha256:
        raise ValueError("source equation catalog digest mismatch")
    lines = Path(catalog_path).read_text(encoding="utf-8").splitlines()
    if len(lines) != node_count:
        raise ValueError("source equation catalog has the wrong line count")
    by_key = {_law_key(row.left, row.right): row.formula_id for row in laws}
    mapping: dict[str, int] = {}
    for source_node, line in enumerate(lines, 1):
        formula_id = by_key.get(_law_key(*_parse_infix_equation(line)))
        if formula_id is not None:
            if formula_id in mapping:
                raise ValueError("source equation catalog maps one formula twice")
            mapping[formula_id] = source_node
    core = {
        "schema": "leanmill.source_formula_mapping_receipt.v1",
        "adapter_id": ADAPTER_ID,
        "source_ref": source_ref,
        "catalog_sha256": catalog_sha256,
        "node_count": node_count,
        "mapped_formula_count": len(mapping),
        "mapping_sha256": content_hash(dict(sorted(mapping.items()))),
        "mapping_method": "canonical_binary_infix_equation.v1",
    }
    return mapping, {**core, "receipt_sha256": content_hash(core)}


def build_single_premise_oracle(
    *,
    adapter_config: Mapping[str, Any],
    oracle_config: Mapping[str, Any],
) -> SourceImplicationOracle:
    """Materialize an optional external implication capability for this adapter."""

    required = {
        "source_ref",
        "node_catalog_path",
        "node_catalog_sha256",
        "relation_path",
        "relation_sha256",
        "node_count",
        "status_names",
        "proved_true_codes",
        "proved_false_codes",
    }
    if not required.issubset(oracle_config):
        raise ValueError("source implication capability configuration is incomplete")
    node_count = int(oracle_config["node_count"])
    source_ref = str(oracle_config["source_ref"])
    mapping, receipt = _map_formula_ids_to_source_nodes(
        magma_laws_through_order(
            int(adapter_config.get("max_total_operation_order", 3))
        ),
        catalog_path=str(oracle_config["node_catalog_path"]),
        catalog_sha256=str(oracle_config["node_catalog_sha256"]),
        node_count=node_count,
        source_ref=source_ref,
    )
    return SourceImplicationOracle.from_rle_file(
        mapping,
        relation_path=str(oracle_config["relation_path"]),
        relation_sha256=str(oracle_config["relation_sha256"]),
        node_count=node_count,
        status_names=tuple(str(row) for row in oracle_config["status_names"]),
        proved_true_codes=tuple(int(row) for row in oracle_config["proved_true_codes"]),
        proved_false_codes=tuple(int(row) for row in oracle_config["proved_false_codes"]),
        source_ref=source_ref,
        mapping_receipt=receipt,
    )


def build_fixed_size_countermodel_finder(
    *, signature: TheorySignature, adapter_config: Mapping[str, Any]
):
    del adapter_config
    return partial(find_finite_countermodel, signature)


def preflight_blueprint(
    signature: TheorySignature,
    *,
    adapter_config: Mapping[str, Any],
    formula_grammar: Mapping[str, Any],
    strata: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if len(signature.sorts) != 1 or len(signature.operations) != 1 or signature.relations:
        raise ValueError("magma adapter requires one sort, one operation, and no relations")
    operation = signature.operations[0]
    sort = signature.sorts[0].name
    if operation.arg_sorts != (sort, sort) or operation.result_sort != sort:
        raise ValueError("magma operation must be closed and binary")
    max_order = int(adapter_config.get("max_total_operation_order", 3))
    _validate_formula_grammar(formula_grammar, max_order=max_order)
    sizes = tuple(int(row["carrier_size"]) for row in strata)
    if max_order < 0 or not sizes or any(size < 1 for size in sizes):
        raise ValueError("magma grammar/order strata are invalid")
    return {
        "formula_count": len(magma_laws_through_order(max_order)),
        "labeled_model_count": sum(size ** (size * size) for size in sizes),
        "complete_census_available": True,
    }


def build_formulas(
    signature: TheorySignature,
    *,
    adapter_config: Mapping[str, Any],
    formula_grammar: Mapping[str, Any],
) -> tuple[AxiomFormula, ...]:
    del signature
    max_order = int(adapter_config.get("max_total_operation_order", 3))
    _validate_formula_grammar(formula_grammar, max_order=max_order)
    return tuple(row.axiom for row in magma_laws_through_order(max_order))


def build_model_universe(
    signature: TheorySignature,
    *,
    strata: Sequence[Mapping[str, Any]],
    base_axioms: Sequence[AxiomFormula] = (),
    adapter_config: Mapping[str, Any] | None = None,
) -> MagmaModelUniverse:
    del adapter_config
    sizes = tuple(int(row["carrier_size"]) for row in strata)
    return enumerate_magma_model_universe(
        signature, carrier_sizes=sizes, base_axioms=tuple(base_axioms)
    )


def load_model_universe(value: Mapping[str, Any]) -> MagmaModelUniverse:
    if value.get("adapter_id") != ADAPTER_ID:
        raise ValueError("magma universe adapter ID")
    signature = TheorySignature.from_json(value["signature"])
    receipt_row = value.get("receipt")
    if not isinstance(receipt_row, Mapping):
        raise ValueError("magma census receipt missing")
    receipt = FiniteModelUniverseReceipt(
        signature_hash=str(receipt_row["signature_sha256"]),
        carrier_sizes=tuple(int(row) for row in receipt_row["carrier_sizes"]),
        base_axiom_hashes=tuple(str(row) for row in receipt_row["base_axiom_sha256s"]),
        labeled_interpretation_count=int(receipt_row["labeled_interpretation_count"]),
        accepted_labeled_count=int(receipt_row["accepted_labeled_count"]),
        canonical_model_count=int(receipt_row["canonical_model_count"]),
        model_order_digest=str(receipt_row["model_order_digest"]),
        isomorphism_policy=str(receipt_row["isomorphism_policy"]),
        complete=receipt_row.get("complete") is True,
        schema=str(receipt_row["schema"]),
    )
    if receipt_row.get("receipt_sha256") != receipt.receipt_digest:
        raise ValueError("magma census receipt hash")
    models: list[CanonicalModelRecord] = []
    for row in value.get("models") or []:
        if not isinstance(row, Mapping):
            raise ValueError("magma model row must be an object")
        model = FiniteModel.from_json(row["model"])
        expected_id = "model:" + content_hash(
            {
                "signature_sha256": signature.content_hash,
                "carrier_size": int(row["carrier_size"]),
                "operation": str(row["operation_name"]),
                "canonical_table": list(row["canonical_table"]),
            }
        )
        if row.get("model_id") != expected_id:
            raise ValueError("magma canonical model identity")
        models.append(
            CanonicalModelRecord(
                model_id=expected_id,
                carrier_size=int(row["carrier_size"]),
                operation_name=str(row["operation_name"]),
                canonical_table=tuple(int(item) for item in row["canonical_table"]),
                model=model,
                labeled_orbit_count=int(row["labeled_orbit_count"]),
                schema=str(row["schema"]),
            )
        )
    return MagmaModelUniverse(signature=signature, models=tuple(models), receipt=receipt)


CAPABILITIES = {
    "fixed_size_countermodel_finder": build_fixed_size_countermodel_finder,
    "single_premise_implication_oracle": build_single_premise_oracle,
}


__all__ = [
    "ADAPTER_ID", "CAPABILITIES", "build_formulas", "build_model_universe",
    "build_fixed_size_countermodel_finder", "build_single_premise_oracle",
    "load_model_universe", "preflight_blueprint",
]
