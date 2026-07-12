"""Anonymous interactive workbench over one frozen formal theory context."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from ztare.common.leaf_workbench_contract import (
    LeafWorkbenchCapability,
    LeafWorkbenchContract,
    validate_leaf_workbench_registry_parity,
)
from ztare.leanmill.finite_theory_context import FormalTheoryContext, SemanticTheoryNode
from ztare.leanmill.finite_model import evaluate_axiom
from ztare.leanmill.conservative_definition import (
    ConservativeOperationDefinition,
    build_conservative_operation_definition,
)
from ztare.leanmill.theory_context import TheoryLandscapeContext
from ztare.leanmill.theory_interest import (
    profile_theory_program_predictions,
    theory_program_information_yield,
    theory_residual_information_yield,
)
from ztare.leanmill.theory_language import (
    THEORY_LANGUAGE_CHANGE_KINDS,
    TheoryLanguageExpansionRequest,
    build_theory_language_expansion_request,
)
from ztare.leanmill.typed_axiom_proposal import (
    TypedAxiomProposal,
    build_typed_axiom_proposal,
)
from ztare.leanmill.typed_postfix_codec import (
    decode_postfix_equation,
    decode_postfix_formula,
    decode_postfix_term,
)
from ztare.leanmill.theory_ir import Binder, content_hash


def _cap(capability_id: str, purpose: str, inputs: Sequence[str], outputs: Sequence[str]) -> LeafWorkbenchCapability:
    return LeafWorkbenchCapability(
        capability_id=capability_id,
        purpose=purpose,
        authority="pure_diagnostic",
        secret_policy="public_only",
        input_contract=list(inputs),
        output_contract=list(outputs),
    )


AXIOMPACK_LEAF_WORKBENCH_CONTRACT = LeafWorkbenchContract(
    capabilities=(
        _cap("list_theory_nodes", "Page through anonymous theory-node topology.", ["offset", "limit"], ["nodes", "total", "next_offset"]),
        _cap("inspect_formula_profiles", "Inspect anonymous typed structure for existing formula IDs.", ["formula_ids"], ["formula_profiles"]),
        _cap("inspect_theory_node", "Inspect one anonymous bounded theory node.", ["node_id"], ["extent_size", "closure_size", "minimal_generators"]),
        _cap("compare_theory_nodes", "Compare two anonymous theory extents and closures.", ["left_node_id", "right_node_id"], ["extent_distance", "closure_distance", "separation_model_id"]),
        _cap("show_separation_models", "Return a canonical model separating two presentations.", ["left_formula_ids", "right_formula_ids"], ["model_id", "stratum_id"]),
        _cap(
            "show_indistinguishable_objects",
            "Page anonymous object pairs that agree on every current formula.",
            ["offset", "limit"],
            [
                "status",
                "pair_count",
                "pairs",
                "next_offset",
                "current_formula_count",
                "object_identity_policy",
                "claim_boundary",
            ],
        ),
        _cap(
            "propose_frontier_formula",
            "Typecheck one anonymous postfix first-order formula for a new immutable context epoch.",
            [
                "structural_conjecture",
                "axiom_name",
                "variables",
                "lhs_tokens",
                "rhs_tokens",
                "formula_tokens",
                "definitions",
                "nl_intent",
                "kill_condition",
                "contrast_object_ids",
            ],
            [
                "status",
                "formula_id",
                "formula_identity_new",
                "typed_proposal_sha256",
                "axiom_sha256",
                "theory_signature_sha256",
                "codec",
                "definition_ids",
                "definitions_expand_to_prior_signature",
                "claim_boundary",
                "contrast_truth_values",
                "separates_contrast",
                "semantic_profile_new_witness",
                "error_code",
                "error",
            ],
        ),
        _cap(
            "select_theory_presentation",
            "Preview a presentation; in theory-program mode also assess agent-chosen predictions.",
            ["formula_ids", "prediction_formula_ids"],
            [
                "node_id",
                "independent",
                "extent_size",
                "closure_size",
                "synergy_formula_ids",
                "cheap_baseline_formula_ids",
                "residual_synergy_formula_ids",
                "residual_yield",
                "cheap_baseline_inconclusive_ids",
                "cheap_baseline_inconclusive_receipts",
                "structural_baseline",
                "consequence_formula_ids",
                "residual_prediction_formula_ids",
                "program_yield",
                "prediction_profile",
            ],
        ),
        _cap(
            "propose_theory_language_expansion",
            "Receipt a new primitive, observable, quotient, or abstraction as an outbound blueprint request.",
            [
                "change_kind",
                "blind_spot",
                "proposed_interface",
                "evidence_refs",
                "discriminating_test",
                "kill_condition",
            ],
            [
                "status",
                "request_id",
                "request",
                "next_route",
                "claim_boundary",
                "error_code",
                "error",
            ],
        ),
    ),
    schema="leanmill-axiompack-leaf-workbench-v9",
)


def navigator_decision_output_schema() -> dict[str, Any]:
    """Typed final-message envelope for the anonymous navigator role."""

    text = {"type": "string", "minLength": 1}

    def obj(properties: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": list(properties),
            "properties": dict(properties),
        }

    def array(items: Mapping[str, Any], *, maximum: int | None = None) -> dict[str, Any]:
        schema: dict[str, Any] = {"type": "array", "minItems": 1, "items": dict(items)}
        if maximum is not None:
            schema["maxItems"] = maximum
        return schema

    string_array = array(text)
    variables_schema = array(obj({"name": text, "sort": text}), maximum=16)
    token_array = array(text, maximum=256)
    contrast_schema = {
        "anyOf": [
            {**array(text, maximum=2), "minItems": 2},
            {"type": "null"},
        ]
    }
    formula_common = {
        "structural_conjecture": text,
        "axiom_name": text,
        "variables": variables_schema,
        "nl_intent": text,
        "kill_condition": text,
        "contrast_object_ids": contrast_schema,
    }
    definitions_schema = array(
        obj(
            {
                "name": text,
                "parameters": variables_schema,
                "body_tokens": token_array,
            }
        ),
        maximum=8,
    )
    input_variants = [
        obj(
            {
                "offset": {"type": "integer", "minimum": 0},
                "limit": {"type": "integer", "minimum": 1, "maximum": 64},
            }
        ),
        obj({"formula_ids": string_array}),
        obj({"formula_ids": string_array, "prediction_formula_ids": string_array}),
        obj({"node_id": text}),
        obj({"left_node_id": text, "right_node_id": text}),
        obj({"left_formula_ids": string_array, "right_formula_ids": string_array}),
        obj({}),
        obj({**formula_common, "lhs_tokens": token_array, "rhs_tokens": token_array}),
        obj({**formula_common, "formula_tokens": token_array}),
        obj(
            {
                **formula_common,
                "lhs_tokens": token_array,
                "rhs_tokens": token_array,
                "definitions": definitions_schema,
            }
        ),
        obj(
            {
                "change_kind": {
                    "type": "string",
                    "enum": sorted(THEORY_LANGUAGE_CHANGE_KINDS),
                },
                "blind_spot": text,
                "proposed_interface": text,
                "evidence_refs": string_array,
                "discriminating_test": text,
                "kill_condition": text,
            }
        ),
        obj(
            {
                **formula_common,
                "formula_tokens": token_array,
                "definitions": definitions_schema,
            }
        ),
    ]
    return obj(
        {
            "decision": {
                "type": "string",
                "enum": [
                    "request",
                    "freeze",
                    "reject_candidate",
                    "reject_all",
                    "finish",
                ],
            },
            "rationale": text,
            "capability_id": {"type": ["string", "null"]},
            "input_refs": {"anyOf": input_variants},
            "formula_ids": {"anyOf": [string_array, {"type": "null"}]},
            "boundary_target_ids": {
                "anyOf": [string_array, {"type": "null"}]
            },
        }
    ) | {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
    }


def _receipt(context: TheoryLandscapeContext, capability_id: str, inputs: Mapping[str, Any], outputs: Mapping[str, Any]) -> dict[str, Any]:
    core = {
        "schema": "leanmill.axiompack_workbench_receipt.v1",
        "capability_id": capability_id,
        "context_hash": context.context_hash,
        "input_hashes": {
            key: "sha256:" + content_hash(value)
            for key, value in sorted(inputs.items())
        },
        "output_summary": dict(outputs),
        "claim_bindings": [capability_id],
        "authority": "deterministic_host",
    }
    return {**core, "receipt_id": "sha256:" + content_hash(core)}


def _rejected_action_receipt(
    context: TheoryLandscapeContext,
    capability_id: str,
    inputs: Mapping[str, Any],
    *,
    status: str,
    error_code: str,
    error: Exception | str,
    defaults: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    outputs = {
        "status": status,
        "error_code": error_code,
        "error": str(error),
        "claim_boundary": (
            "malformed model proposal rejected by the host; the context is unchanged "
            "and no semantic or promotion claim is made"
        ),
    }
    outputs.update(dict(defaults or {}))
    return _receipt(context, capability_id, inputs, outputs)


def _ids(value: Any, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field} must be a non-empty list")
    return tuple(str(row) for row in value)


_FRONTIER_FORMULA_COMMON_FIELDS = {
    "structural_conjecture",
    "axiom_name",
    "variables",
    "nl_intent",
    "kill_condition",
}
_FRONTIER_FORMULA_OPTIONAL_FIELDS = {"contrast_object_ids"}
_FRONTIER_EQUATION_FIELDS = {"lhs_tokens", "rhs_tokens"}
_FRONTIER_GENERAL_FORMULA_FIELDS = {"formula_tokens"}
_FRONTIER_DEFINITION_FIELDS = {"definitions"}


def _decode_frontier_formula_move(
    context: TheoryLandscapeContext,
    inputs: Mapping[str, Any],
) -> tuple[TypedAxiomProposal, tuple[ConservativeOperationDefinition, ...]]:
    """Lower one cold anonymous postfix draft through the existing typed proposal seam."""

    if not isinstance(context, FormalTheoryContext):
        raise ValueError("frontier formula proposals require a formal finite context")
    fields = set(inputs)
    equation_shape = _FRONTIER_EQUATION_FIELDS <= fields
    formula_shape = _FRONTIER_GENERAL_FORMULA_FIELDS <= fields
    allowed = (
        _FRONTIER_FORMULA_COMMON_FIELDS
        | _FRONTIER_FORMULA_OPTIONAL_FIELDS
        | _FRONTIER_EQUATION_FIELDS
        | _FRONTIER_GENERAL_FORMULA_FIELDS
        | _FRONTIER_DEFINITION_FIELDS
    )
    if (
        not _FRONTIER_FORMULA_COMMON_FIELDS <= fields
        or equation_shape == formula_shape
        or fields > allowed
        or (fields & _FRONTIER_EQUATION_FIELDS and not equation_shape)
    ):
        raise ValueError("frontier formula proposal fields do not match the typed codec")
    signature = context.signature
    sort_aliases = {
        f"sort_{index}": row.name for index, row in enumerate(signature.sorts)
    }
    operation_aliases = {
        f"op_{index}": row.name for index, row in enumerate(signature.operations)
    }
    relation_aliases = {
        f"rel_{index}": row.name for index, row in enumerate(signature.relations)
    }
    raw_variables = inputs.get("variables")
    if not isinstance(raw_variables, list) or not raw_variables:
        raise ValueError("frontier formula proposal requires variables")
    variable_sorts: dict[str, str] = {}
    for row in raw_variables:
        if not isinstance(row, Mapping) or set(row) != {"name", "sort"}:
            raise ValueError("frontier formula variables require name and anonymous sort")
        name = str(row["name"]).strip()
        sort_alias = str(row["sort"]).strip()
        if not name or name in variable_sorts or sort_alias not in sort_aliases:
            raise ValueError("frontier formula variables must be unique and use declared sort aliases")
        variable_sorts[name] = sort_aliases[sort_alias]

    definitions: dict[str, ConservativeOperationDefinition] = {}
    raw_definitions = inputs.get("definitions") or []
    if not isinstance(raw_definitions, list) or len(raw_definitions) > 8:
        raise ValueError("frontier definitions must be a bounded list")
    motif_refs = (
        context.context_hash,
        *(str(row) for row in inputs.get("contrast_object_ids") or ()),
    )
    for raw_definition in raw_definitions:
        if (
            not isinstance(raw_definition, Mapping)
            or set(raw_definition) != {"name", "parameters", "body_tokens"}
        ):
            raise ValueError("frontier definition fields do not match the typed codec")
        definition_name = str(raw_definition["name"]).strip()
        if definition_name in definitions:
            raise ValueError("frontier definition names must be unique")
        raw_parameters = raw_definition["parameters"]
        if not isinstance(raw_parameters, list) or not raw_parameters:
            raise ValueError("frontier definition parameters must be nonempty")
        parameter_sorts: dict[str, str] = {}
        for row in raw_parameters:
            if not isinstance(row, Mapping) or set(row) != {"name", "sort"}:
                raise ValueError("frontier definition parameters require name and sort")
            parameter_name = str(row["name"]).strip()
            sort_alias = str(row["sort"]).strip()
            if (
                not parameter_name
                or parameter_name in parameter_sorts
                or sort_alias not in sort_aliases
            ):
                raise ValueError("frontier definition parameters must be unique and typed")
            parameter_sorts[parameter_name] = sort_aliases[sort_alias]
        body_raw = raw_definition["body_tokens"]
        if not isinstance(body_raw, list):
            raise ValueError("frontier definition body must be a token list")
        body_tokens = tuple(
            operation_aliases.get(str(token), str(token)) for token in body_raw
        )
        body, result_sort = decode_postfix_term(
            signature,
            variable_sorts=parameter_sorts,
            tokens=body_tokens,
        )
        definitions[definition_name] = build_conservative_operation_definition(
            signature,
            name=definition_name,
            parameters=tuple(Binder(name, sort) for name, sort in parameter_sorts.items()),
            result_sort=result_sort,
            body=body,
            source_motif_refs=motif_refs,
        )

    def tokens(field: str) -> tuple[str, ...]:
        raw = inputs.get(field)
        if not isinstance(raw, list):
            raise ValueError(f"{field} must be a token list")
        return tuple(
            operation_aliases.get(
                str(token), relation_aliases.get(str(token), str(token))
            )
            for token in raw
        )

    if formula_shape:
        axiom = decode_postfix_formula(
            signature,
            name=str(inputs["axiom_name"]).strip(),
            variable_sorts=variable_sorts,
            tokens=tokens("formula_tokens"),
            derived_definitions=definitions,
        )
    else:
        axiom = decode_postfix_equation(
            signature,
            name=str(inputs["axiom_name"]).strip(),
            variable_sorts=variable_sorts,
            lhs_tokens=tokens("lhs_tokens"),
            rhs_tokens=tokens("rhs_tokens"),
            derived_definitions=definitions,
        )
    source = {
        "schema": "leanmill.navigator_structural_conjecture.v1",
        "context_hash": context.context_hash,
        "conjecture": str(inputs["structural_conjecture"]).strip(),
    }
    if formula_shape or definitions:
        source["formula_codec"] = (
            "leanmill.typed_postfix_formula.v1"
            if formula_shape
            else "leanmill.typed_postfix_equation.v1"
        )
        source["conservative_definitions"] = [
            row.to_json() for row in definitions.values()
        ]
    proposal = build_typed_axiom_proposal(
        theory_signature=signature,
        axiom=axiom,
        nl_intent=str(inputs["nl_intent"]).strip(),
        kill_condition=str(inputs["kill_condition"]).strip(),
        source_conjecture=source,
    )
    return proposal, tuple(definitions.values())


def decode_frontier_formula_proposal(
    context: TheoryLandscapeContext,
    inputs: Mapping[str, Any],
) -> TypedAxiomProposal:
    """Lower one cold theory-language move through the typed proposal seam."""

    return _decode_frontier_formula_move(context, inputs)[0]


def decode_theory_language_expansion_request(
    context: TheoryLandscapeContext,
    inputs: Mapping[str, Any],
    *,
    source_epoch: int,
) -> TheoryLanguageExpansionRequest:
    required = {
        "change_kind",
        "blind_spot",
        "proposed_interface",
        "evidence_refs",
        "discriminating_test",
        "kill_condition",
    }
    if set(inputs) != required or not isinstance(inputs.get("evidence_refs"), list):
        raise ValueError("theory-language request fields do not match the typed contract")
    return build_theory_language_expansion_request(
        source_context_hash=context.context_hash,
        source_epoch=source_epoch,
        change_kind=str(inputs["change_kind"]),
        blind_spot=str(inputs["blind_spot"]),
        proposed_interface=str(inputs["proposed_interface"]),
        evidence_refs=tuple(str(row) for row in inputs["evidence_refs"]),
        discriminating_test=str(inputs["discriminating_test"]),
        kill_condition=str(inputs["kill_condition"]),
    )


def axiompack_leaf_workbench_action_environment(
    *,
    context: TheoryLandscapeContext,
    max_presentation_size: int = 2,
    topology_presentation_size: int | None = None,
    context_epoch: int = 0,
    selection_mode: str = "compact_axiom_pack",
) -> dict[str, Any]:
    if selection_mode not in {"compact_axiom_pack", "theory_program"}:
        raise ValueError("unsupported workbench selection mode")
    topology_width = (
        min(2, max_presentation_size)
        if topology_presentation_size is None
        else topology_presentation_size
    )
    if type(topology_width) is not int or not 1 <= topology_width <= max_presentation_size:
        raise ValueError("topology_presentation_size must lie within presentation width")
    if not context.complete and selection_mode != "theory_program":
        raise ValueError("sampled panels support theory-program navigation only")
    sampled_capabilities = {
        "inspect_formula_profiles",
        "show_separation_models",
        "show_indistinguishable_objects",
        "propose_frontier_formula",
        "select_theory_presentation",
        "propose_theory_language_expansion",
    }
    contract = (
        AXIOMPACK_LEAF_WORKBENCH_CONTRACT
        if context.complete
        else LeafWorkbenchContract(
            capabilities=tuple(
                capability
                for capability in AXIOMPACK_LEAF_WORKBENCH_CONTRACT.capabilities
                if capability.capability_id in sampled_capabilities
            ),
            schema="leanmill-axiompack-sampled-leaf-workbench-v1",
        )
    )
    nodes: dict[str, SemanticTheoryNode] | None = None

    def topology_nodes() -> dict[str, SemanticTheoryNode]:
        nonlocal nodes
        if nodes is None:
            nodes = {
                row.node_id: row
                for row in context.generated_theory_nodes(
                    max_presentation_size=topology_width,
                    semantic_quotient=True,
                )
            }
        return nodes

    def anonymous_formula(formula_id: str) -> dict[str, Any]:
        return dict(context.anonymous_formula_profile(formula_id))

    def object_identity_policy() -> str:
        return str(context.object_identity_policy or "")

    def object_contrast_is_admissible() -> bool:
        return context.object_contrast_admissible is True

    def indistinguishable_pairs() -> list[dict[str, Any]]:
        if not object_contrast_is_admissible():
            return []
        profiles = {
            object_id: dict(context.anonymous_object_profile(object_id))
            for object_id in context.object_ids
        }
        pairs: list[dict[str, Any]] = []
        for observation_class in context.incidence.observational_object_classes():
            by_stratum: dict[str, list[str]] = {}
            for object_id in observation_class:
                profile = profiles[object_id]
                by_stratum.setdefault(str(profile["stratum_id"]), []).append(object_id)
            for stratum_id, object_ids in sorted(by_stratum.items()):
                if len(object_ids) < 2:
                    continue
                for left, right in zip(object_ids, object_ids[1:]):
                    pairs.append(
                        {
                            "object_ids": [left, right],
                            "stratum_id": stratum_id,
                            "observation_class_size": len(object_ids),
                        }
                    )
        pairs.sort(
            key=lambda row: (
                row["stratum_id"],
                row["object_ids"],
            )
        )
        return pairs

    def list_nodes(_project: str | Path, req: dict[str, Any], _row: Any, _contract: Any) -> dict[str, Any]:
        inputs = req.get("input_refs") or {}
        offset = max(0, int(inputs.get("offset", 0)))
        limit = min(64, max(1, int(inputs.get("limit", 24))))
        ordered = sorted(
            topology_nodes().values(),
            key=lambda row: (-row.extent_bits.bit_count(), -row.closure_bits.bit_count(), row.node_id),
        )
        page = ordered[offset:offset + limit]
        return _receipt(context, "list_theory_nodes", inputs, {
            "total": len(ordered),
            "topology_policy": (
                f"semantic_profile_representatives_through_width_{topology_width}; "
                "candidate identity and allowed presentation width remain independent"
            ),
            "nodes": [
                {
                    "node_id": row.node_id,
                    "extent_size": row.extent_bits.bit_count(),
                    "closure_size": row.closure_bits.bit_count(),
                    "minimum_basis_size": min(map(len, row.minimal_generators)),
                    "one_minimal_generator": list(row.minimal_generators[0]),
                }
                for row in page
            ],
            "next_offset": offset + len(page) if offset + len(page) < len(ordered) else None,
        })

    def inspect_formulas(_project: str | Path, req: dict[str, Any], _row: Any, _contract: Any) -> dict[str, Any]:
        inputs = req.get("input_refs") or {}
        formula_ids = _ids(inputs.get("formula_ids"), field="formula_ids")
        if len(formula_ids) > 32:
            raise ValueError("formula profile inspection is bounded to 32 IDs")
        return _receipt(context, "inspect_formula_profiles", inputs, {
            "formula_profiles": [anonymous_formula(formula_id) for formula_id in formula_ids]
        })

    def node(node_id: Any) -> SemanticTheoryNode:
        try:
            return topology_nodes()[str(node_id)]
        except KeyError as exc:
            raise ValueError("unknown node_id in frozen context") from exc

    def inspect(_project: str | Path, req: dict[str, Any], _row: Any, _contract: Any) -> dict[str, Any]:
        inputs = req.get("input_refs") or {}
        found = node(inputs.get("node_id"))
        return _receipt(context, "inspect_theory_node", inputs, {
            "node_id": found.node_id,
            "extent_size": found.extent_bits.bit_count(),
            "closure_size": found.closure_bits.bit_count(),
            "minimal_generator_count": len(found.minimal_generators),
            "minimal_generators": [list(row) for row in found.minimal_generators[:16]],
            "minimal_generators_truncated": len(found.minimal_generators) > 16,
        })

    def compare(_project: str | Path, req: dict[str, Any], _row: Any, _contract: Any) -> dict[str, Any]:
        inputs = req.get("input_refs") or {}
        left, right = node(inputs.get("left_node_id")), node(inputs.get("right_node_id"))
        difference = left.extent_bits ^ right.extent_bits
        separation_id = None
        if difference:
            index = (difference & -difference).bit_length() - 1
            separation_id = context.object_ids[index]
        return _receipt(context, "compare_theory_nodes", inputs, {
            "extent_distance": difference.bit_count(),
            "closure_distance": (left.closure_bits ^ right.closure_bits).bit_count(),
            "separation_model_id": separation_id,
        })

    def separation(_project: str | Path, req: dict[str, Any], _row: Any, _contract: Any) -> dict[str, Any]:
        inputs = req.get("input_refs") or {}
        left = _ids(inputs.get("left_formula_ids"), field="left_formula_ids")
        right = _ids(inputs.get("right_formula_ids"), field="right_formula_ids")
        witness = context.separation_witness(left, right)
        outputs = {"model_id": witness.model_id if witness else None}
        if witness:
            outputs["stratum_id"] = witness.stratum_id
        return _receipt(context, "show_separation_models", inputs, outputs)

    def indistinguishable(
        _project: str | Path,
        req: dict[str, Any],
        _row: Any,
        _contract: Any,
    ) -> dict[str, Any]:
        inputs = req.get("input_refs") or {}
        offset = max(0, int(inputs.get("offset", 0)))
        limit = min(4, max(1, int(inputs.get("limit", 1))))
        status = "available"
        if not object_contrast_is_admissible():
            status = "unavailable_without_distinct_object_identity"
        pairs = indistinguishable_pairs() if status == "available" else []
        page = pairs[offset:offset + limit]
        if status == "available" and not pairs:
            status = "current_formulas_separate_all_objects"
        return _receipt(
            context,
            "show_indistinguishable_objects",
            inputs,
            {
                "status": status,
                "pair_count": len(pairs),
                "pairs": [
                    {
                        **pair,
                        "objects": [
                            dict(context.anonymous_object_profile(object_id))
                            for object_id in pair["object_ids"]
                        ],
                    }
                    for pair in page
                ],
                "next_offset": (
                    offset + len(page) if offset + len(page) < len(pairs) else None
                ),
                "current_formula_count": len(context.formula_ids),
                "object_identity_policy": object_identity_policy(),
                "claim_boundary": (
                    "each displayed pair is in one stratum and agrees on every formula "
                    "in the current context; the agreement makes no claim beyond that "
                    "formula panel or its declared object strata"
                ),
            },
        )

    def propose_formula(
        _project: str | Path,
        req: dict[str, Any],
        _row: Any,
        _contract: Any,
    ) -> dict[str, Any]:
        inputs = req.get("input_refs") or {}
        if not isinstance(inputs, Mapping):
            return _rejected_action_receipt(
                context,
                "propose_frontier_formula",
                {"raw_input": inputs},
                status="rejected_invalid_typed_formula",
                error_code="typed_formula_input_object_required",
                error="frontier formula proposal inputs must be an object",
                defaults={
                    "formula_id": None,
                    "formula_identity_new": False,
                    "typed_proposal_sha256": "",
                    "axiom_sha256": "",
                    "theory_signature_sha256": context.signature.content_hash,
                    "codec": "leanmill.typed_postfix_codec",
                    "definition_ids": [],
                    "definitions_expand_to_prior_signature": False,
                    "contrast_truth_values": {},
                    "separates_contrast": None,
                    "semantic_profile_new_witness": None,
                },
            )

        def rejected(error: Exception, *, code: str = "typed_formula_decode_failed") -> dict[str, Any]:
            return _rejected_action_receipt(
                context,
                "propose_frontier_formula",
                inputs,
                status="rejected_invalid_typed_formula",
                error_code=code,
                error=error,
                defaults={
                    "formula_id": None,
                    "formula_identity_new": False,
                    "typed_proposal_sha256": "",
                    "axiom_sha256": "",
                    "theory_signature_sha256": context.signature.content_hash,
                    "codec": "leanmill.typed_postfix_codec",
                    "definition_ids": [],
                    "definitions_expand_to_prior_signature": False,
                    "contrast_truth_values": {},
                    "separates_contrast": None,
                    "semantic_profile_new_witness": None,
                },
            )

        try:
            proposal, definitions = _decode_frontier_formula_move(context, inputs)
        except (KeyError, TypeError, ValueError) as exc:
            return rejected(exc)
        formula_id = "formula:" + proposal.axiom.semantic_hash
        formula_identity_new = formula_id not in context.formula_ids
        contrast_ids_raw = inputs.get("contrast_object_ids")
        contrast_truth_values: dict[str, bool] = {}
        separates_contrast: bool | None = None
        semantic_profile_new_witness: dict[str, Any] | None = None
        try:
            if contrast_ids_raw is not None:
                if (
                    not isinstance(contrast_ids_raw, list)
                    or len(contrast_ids_raw) != 2
                    or len(set(map(str, contrast_ids_raw))) != 2
                ):
                    raise ValueError("contrast_object_ids must contain two distinct object IDs")
                if not isinstance(context, FormalTheoryContext) or not context.complete:
                    raise ValueError("formula contrasts require a complete formal context")
                if not object_contrast_is_admissible():
                    raise ValueError("formula contrasts require an isomorphism-quotiented universe")
                contrast_ids = tuple(map(str, contrast_ids_raw))
                classes = {
                    frozenset(row)
                    for row in context.incidence.observational_object_classes()
                }
                if not any(set(contrast_ids) <= row for row in classes):
                    raise ValueError("contrast objects are already distinguished by the current formulas")
                by_id = {row.model_id: row for row in context.universe.models}
                try:
                    records = tuple(by_id[model_id] for model_id in contrast_ids)
                except KeyError as exc:
                    raise ValueError("unknown contrast object in frozen context") from exc
                if records[0].stratum_id != records[1].stratum_id:
                    raise ValueError("contrast objects must belong to one stratum")
                contrast_truth_values = {
                    record.model_id: evaluate_axiom(
                        context.signature,
                        proposal.axiom,
                        record.model,
                    )
                    for record in records
                }
                separates_contrast = len(set(contrast_truth_values.values())) == 2
                if separates_contrast:
                    semantic_profile_new_witness = {
                        "authority": "exact_host_evaluation",
                        "object_ids": list(contrast_ids),
                        "truth_values": contrast_truth_values,
                        "context_hash": context.context_hash,
                        "claim_boundary": (
                            "the proposed formula has a truth profile absent from every "
                            "current formula in this finite context"
                        ),
                    }
        except (KeyError, TypeError, ValueError) as exc:
            return rejected(exc, code="typed_formula_contrast_invalid")
        status = (
            "existing_formula"
            if not formula_identity_new
            else "proposed_formula_failed_contrast"
            if separates_contrast is False
            else "proposed_new_formula"
        )
        outputs = {
            "status": status,
            "formula_id": formula_id,
            "formula_identity_new": formula_identity_new,
            "typed_proposal_sha256": proposal.content_hash,
            "axiom_sha256": proposal.axiom_sha256,
            "theory_signature_sha256": proposal.theory_signature_sha256,
            "codec": (
                "leanmill.typed_postfix_formula.v1"
                if "formula_tokens" in inputs
                else "leanmill.typed_postfix_equation.v1"
                if definitions
                else "leanmill.typed_postfix_codec"
            ),
            "contrast_truth_values": contrast_truth_values,
            "separates_contrast": separates_contrast,
            "semantic_profile_new_witness": semantic_profile_new_witness,
            "claim_boundary": (
                "typechecked context-expansion proposal only; no proof, novelty, "
                "semantic-fidelity, or promotion authority"
            ),
        }
        if definitions:
            outputs.update(
                {
                    "definition_ids": [row.definition_id for row in definitions],
                    "definitions_expand_to_prior_signature": True,
                }
            )
        return _receipt(
            context,
            "propose_frontier_formula",
            inputs,
            outputs,
        )

    def select(_project: str | Path, req: dict[str, Any], _row: Any, _contract: Any) -> dict[str, Any]:
        inputs = req.get("input_refs") or {}
        formulas = _ids(inputs.get("formula_ids"), field="formula_ids")
        if len(formulas) > max_presentation_size:
            raise ValueError("presentation exceeds the frozen width cap")
        if not context.complete:
            predictions = _ids(
                inputs.get("prediction_formula_ids"),
                field="prediction_formula_ids",
            )
            profile = profile_theory_program_predictions(
                context, formulas, predictions
            )
            sampled_yield = {
                "baseline_ref": "sampled_panel_unpriced.v1",
                "identification_bits": 0.0,
                "information_per_cost": 0.0,
                "residual_ids": [],
            }
            return _receipt(
                context,
                "select_theory_presentation",
                inputs,
                {
                    "node_id": "sampled-presentation:"
                    + content_hash(
                        {
                            "context_hash": context.context_hash,
                            "formula_ids": list(formulas),
                        }
                    ),
                    "independent": None,
                    "extent_size": profile["extent_size"],
                    "closure_size": None,
                    "synergy_formula_ids": [],
                    "cheap_baseline_formula_ids": [],
                    "residual_synergy_formula_ids": [],
                    "residual_yield": sampled_yield,
                    "consequence_formula_ids": [],
                    "residual_prediction_formula_ids": [],
                    "program_yield": {"coordinates": sampled_yield},
                    "prediction_profile": profile,
                    "claim_boundary": "sampled panel diagnostics only",
                },
            )
        extent = context.incidence.extent_bits(formulas)
        node_id = content_hash(
            {"context_hash": context.context_hash, "extent_bits_hex": hex(extent)}
        )
        independent = all(context.independence_witness(formulas, formula) is not None for formula in formulas)
        residual = theory_residual_information_yield(context, formulas)
        outputs = {
            "node_id": node_id,
            "independent": independent,
            "extent_size": extent.bit_count(),
            "closure_size": len(context.closure_ids(formulas)),
            "synergy_formula_ids": list(residual.joint_only_consequence_ids),
            "cheap_baseline_formula_ids": list(
                residual.cheap_baseline_consequence_ids
            ),
            "residual_synergy_formula_ids": list(residual.residual_consequence_ids),
            "residual_yield": residual.coordinates.to_json(),
            "cheap_baseline_witnesses": dict(residual.cheap_baseline_witnesses),
            "cheap_baseline_inconclusive_ids": list(
                residual.cheap_baseline_inconclusive_ids
            ),
            "cheap_baseline_inconclusive_receipts": dict(
                residual.cheap_baseline_inconclusive_receipts
            ),
            "structural_baseline": residual.structural_baseline,
        }
        if selection_mode == "theory_program":
            program = theory_program_information_yield(context, formulas)
            outputs.update(
                {
                    "consequence_formula_ids": list(program.consequence_ids),
                    "residual_prediction_formula_ids": list(
                        program.residual_prediction_ids
                    ),
                    "program_yield": program.to_json(),
                }
            )
            raw_predictions = inputs.get("prediction_formula_ids")
            if raw_predictions is not None:
                predictions = _ids(
                    raw_predictions, field="prediction_formula_ids"
                )
                outputs["prediction_profile"] = profile_theory_program_predictions(
                    context, formulas, predictions
                )
        elif inputs.get("prediction_formula_ids") is not None:
            raise ValueError(
                "compact-pack previews do not carry theory-program predictions"
            )
        return _receipt(context, "select_theory_presentation", inputs, outputs)

    def propose_language_expansion(
        _project: str | Path,
        req: dict[str, Any],
        _row: Any,
        _contract: Any,
    ) -> dict[str, Any]:
        inputs = req.get("input_refs") or {}
        if not isinstance(inputs, Mapping):
            return _rejected_action_receipt(
                context,
                "propose_theory_language_expansion",
                {"raw_input": inputs},
                status="rejected_invalid_language_request",
                error_code="language_request_input_object_required",
                error="theory-language request inputs must be an object",
                defaults={
                    "request_id": None,
                    "request": None,
                    "next_route": "frontier_blueprint_compiler_or_adapter_forge",
                },
            )
        try:
            request = decode_theory_language_expansion_request(
                context, inputs, source_epoch=context_epoch
            )
        except (KeyError, TypeError, ValueError) as exc:
            return _rejected_action_receipt(
                context,
                "propose_theory_language_expansion",
                inputs,
                status="rejected_invalid_language_request",
                error_code="language_request_decode_failed",
                error=exc,
                defaults={
                    "request_id": None,
                    "request": None,
                    "next_route": "frontier_blueprint_compiler_or_adapter_forge",
                },
            )
        return _receipt(
            context,
            "propose_theory_language_expansion",
            inputs,
            {
                "status": "outbound_blueprint_request",
                "request_id": request.request_id,
                "request": request.to_json(),
                "next_route": "frontier_blueprint_compiler_or_adapter_forge",
                "claim_boundary": (
                    "proposal only; a changed executable language requires a new "
                    "reviewed blueprint and cannot mutate this context"
                ),
            },
        )

    handlers = {
        "list_theory_nodes": list_nodes,
        "inspect_formula_profiles": inspect_formulas,
        "inspect_theory_node": inspect,
        "compare_theory_nodes": compare,
        "show_separation_models": separation,
        "show_indistinguishable_objects": indistinguishable,
        "propose_frontier_formula": propose_formula,
        "select_theory_presentation": select,
        "propose_theory_language_expansion": propose_language_expansion,
    }
    handlers = {
        key: value for key, value in handlers.items()
        if key in contract.registry()
    }
    validate_leaf_workbench_registry_parity(
        contract=contract,
        action_handlers=handlers,
        stateless_action_ids=handlers,
    ).raise_for_errors()
    return {
        "adapter_id": "axiompack",
        "contract": contract,
        "records_fn": lambda _project: [],
        "action_handlers": handlers,
        "stateless_actions": frozenset(handlers),
        "candidate_bound_actions": frozenset(),
        "context_hash": context.context_hash,
    }


__all__ = [
    "AXIOMPACK_LEAF_WORKBENCH_CONTRACT",
    "axiompack_leaf_workbench_action_environment",
    "decode_frontier_formula_proposal",
    "decode_theory_language_expansion_request",
    "navigator_decision_output_schema",
]
