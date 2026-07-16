"""Post-freeze literature packet and strict result contract for AxiomPack."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from ztare.leanmill.common import read_json
from ztare.leanmill.frontier_blueprint import (
    FrontierTheoryBlueprint,
    presentation_size_bounds,
)
from ztare.leanmill.finite_theory_context import load_formal_theory_context
from ztare.leanmill.theory_ir import content_hash, render_formula_plain
from ztare.leanmill.theory_ir import operation_argument_permutation_variants


POST_FREEZE_RESULT_PACKET_SCHEMA = "leanmill.post_freeze_result_packet.v4"


def _coordinate_search_rows(
    context: Any,
    formula_rows: Sequence[Mapping[str, Any]],
    base_theory: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Render deterministic source-search queries under input-coordinate changes."""

    source_rows: list[tuple[str, Any]] = []
    profiles = {row.formula_id: row.axiom for row in context.formula_profiles}
    for row in formula_rows:
        formula_id = str(row["formula_id"])
        source_rows.append((formula_id, profiles[formula_id]))
    for index, row in enumerate(base_theory):
        semantic_hash = str(row.get("semantic_hash") or "")
        axiom = context.base_axioms[index]
        source_rows.append((f"base:{semantic_hash}", axiom))

    variants: list[dict[str, Any]] = []
    try:
        for formula_ref, axiom in source_rows:
            for mapping, transformed in operation_argument_permutation_variants(
                context.signature, axiom.formula, max_variants=120
            ):
                mapping_json = [
                    {"symbol": symbol, "permutation": list(permutation)}
                    for symbol, permutation in mapping
                ]
                core = {
                    "formula_ref": formula_ref,
                    "operation_argument_permutations": mapping_json,
                    "formula": render_formula_plain(transformed),
                    "formula_ir": transformed.to_json(),
                }
                variants.append(
                    {
                        **core,
                        "variant_id": "coordinate:" + content_hash(core),
                    }
                )
    except ValueError as exc:
        return [], {
            "status": "unavailable_bounds",
            "reason": str(exc),
            "variant_count": 0,
        }
    return variants, {
        "status": "available",
        "reason": None,
        "variant_count": len(variants),
    }


def _finite_witness_search_rows(
    context: Any,
    premise_ids: Sequence[str],
    *,
    max_witnesses: int = 24,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Expose a bounded post-freeze witness set for executable source comparison."""

    signature = context.signature
    eligible = (
        len(signature.sorts) == 1
        and len(signature.operations) == 1
        and not signature.relations
    )
    if eligible:
        sort = signature.sorts[0]
        operation = signature.operations[0]
        eligible = (
            operation.result_sort == sort.name
            and operation.arg_sorts
            and set(operation.arg_sorts) == {sort.name}
        )
    if not eligible or not hasattr(context, "extent_models"):
        return [], {
            "status": "unavailable_signature",
            "candidate_count": 0,
            "included_count": 0,
            "selection_policy": "smallest_stratum_then_model_id.v1",
        }
    records = sorted(
        context.extent_models(premise_ids),
        key=lambda row: (
            sum(row.model.sort_size_map.values()),
            str(row.stratum_id),
            str(row.model_id),
        ),
    )
    selected = records[:max_witnesses]
    rows = []
    for record in selected:
        model = record.model
        rows.append(
            {
                "candidate_model_id": str(record.model_id),
                "stratum_id": str(record.stratum_id),
                "model_sha256": model.content_hash(signature),
                "carrier_size": model.sort_size_map[sort.name],
                "operation": {
                    "symbol": operation.name,
                    "arity": len(operation.arg_sorts),
                    "table": list(model.operation_map[operation.name]),
                },
            }
        )
    return rows, {
        "status": "complete_extent" if len(selected) == len(records) else "bounded_sample",
        "candidate_count": len(records),
        "included_count": len(selected),
        "selection_policy": "smallest_stratum_then_model_id.v1",
    }


def validate_post_freeze_finite_witness_matches(
    result_packet: Mapping[str, Any],
    review: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Host-check source tables proposed by the post-freeze literature role."""

    proposals = [
        dict(row)
        for row in review.get("finite_witness_matches") or ()
        if isinstance(row, Mapping)
    ]
    if not proposals:
        return []
    packet_core = {
        key: value for key, value in result_packet.items() if key != "packet_sha256"
    }
    if result_packet.get("packet_sha256") != content_hash(packet_core):
        raise ValueError("finite-witness review requires an intact result packet")
    structural = result_packet.get("structural_source_search")
    if not isinstance(structural, Mapping):
        raise ValueError("finite-witness review has no structural search packet")
    witnesses = {
        str(row.get("candidate_model_id") or ""): dict(row)
        for row in structural.get("finite_witnesses") or ()
        if isinstance(row, Mapping)
    }
    citation_urls = {
        str(row.get("source_url") or "")
        for collection in (
            review.get("implication_prior_art") or (),
            review.get("formula_matches") or (),
        )
        for row in collection
        if isinstance(row, Mapping) and row.get("source_url")
    }
    from ztare.leanmill.finite_model import (
        FiniteModel,
        classify_single_operation_equivalence,
    )
    from ztare.leanmill.theory_ir import TheorySignature

    context = result_packet.get("interpretation_context")
    signature_row = context.get("signature") if isinstance(context, Mapping) else None
    if not isinstance(signature_row, Mapping):
        raise ValueError("finite-witness review has no frozen signature")
    signature = TheorySignature.from_json(signature_row)
    if len(signature.sorts) != 1 or len(signature.operations) != 1:
        raise ValueError("finite-witness review requires the advertised single-operation lane")
    sort = signature.sorts[0].name
    operation = signature.operations[0]
    checks = []
    for proposal in proposals:
        proposal_sha256 = content_hash(proposal)
        candidate_id = str(proposal.get("candidate_model_id") or "")
        source_url = str(proposal.get("source_url") or "")
        claimed_relation = str(proposal.get("claimed_relation") or "")
        computed: Mapping[str, Any] | None = None
        reason: str | None = None
        status = "rejected"
        try:
            if source_url not in citation_urls:
                raise ValueError("external table URL is absent from the source review")
            witness = witnesses.get(candidate_id)
            if witness is None:
                raise ValueError("candidate model is outside the frozen premise extent")
            candidate_operation = witness.get("operation")
            source_operation = proposal.get("source_operation")
            if not isinstance(candidate_operation, Mapping) or not isinstance(
                source_operation, Mapping
            ):
                raise ValueError("finite-witness comparison lacks an operation table")
            carrier_size = int(witness.get("carrier_size"))
            if (
                source_operation.get("carrier_size") != carrier_size
                or source_operation.get("arity") != len(operation.arg_sorts)
                or candidate_operation.get("arity") != len(operation.arg_sorts)
                or candidate_operation.get("symbol") != operation.name
            ):
                raise ValueError("external and candidate operation profiles differ")
            candidate_model = FiniteModel(
                sort_sizes=((sort, carrier_size),),
                operations=((operation.name, tuple(candidate_operation["table"])),),
            )
            if candidate_model.content_hash(signature) != witness.get("model_sha256"):
                raise ValueError("frozen candidate model digest mismatch")
            reference_model = FiniteModel(
                sort_sizes=((sort, carrier_size),),
                operations=((operation.name, tuple(source_operation["table"])),),
            )
            computed = classify_single_operation_equivalence(
                signature,
                candidate_model,
                reference_model,
                max_term_depth=2,
                max_term_compositions=100_000,
                max_relabelings=720,
            )
            if computed.get("status") == "unavailable":
                status = "unavailable"
                reason = str(computed.get("reason") or "bounded check unavailable")
            elif computed.get("relation") == claimed_relation:
                status = "verified"
            else:
                status = "refuted"
                reason = (
                    f"claimed {claimed_relation!r}, computed "
                    f"{computed.get('relation')!r}"
                )
        except (KeyError, TypeError, ValueError) as exc:
            reason = str(exc)
        core = {
            "schema": "leanmill.finite_witness_source_match_check.v1",
            "packet_sha256": result_packet.get("packet_sha256"),
            "context_hash": result_packet.get("context_hash"),
            "proposal_sha256": proposal_sha256,
            "candidate_model_id": candidate_id,
            "source_url": source_url,
            "claimed_relation": claimed_relation,
            "status": status,
            "computed_relation": (
                computed.get("relation") if isinstance(computed, Mapping) else None
            ),
            "equivalence_receipt": dict(computed) if isinstance(computed, Mapping) else None,
            "reason": reason,
            "authority": "deterministic_host_table_replay",
            "claim_boundary": (
                "one finite algebra pair only; no theory or variety equivalence"
            ),
        }
        checks.append({**core, "receipt_sha256": content_hash(core)})
    return checks


def post_freeze_literature_output_schema(
    *,
    formula_count: int = 3,
    premise_formula_ids: Sequence[str] = (),
) -> dict[str, Any]:
    if formula_count < 2:
        raise ValueError("literature review requires at least one premise and one target")
    citation = {
        "type": "object",
        "additionalProperties": False,
        "required": ["source_title", "source_url", "relationship", "evidence"],
        "properties": {
            "source_title": {"type": "string", "minLength": 1},
            "source_url": {"type": "string", "minLength": 8},
            "relationship": {"type": "string", "minLength": 1},
            "evidence": {"type": "string", "minLength": 1},
        },
    }
    formula_match = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "role", "formula_id", "formula", "match_status", "external_id",
            "source_title", "source_url", "confidence", "evidence",
            "equivalence_kind", "coordinate_variant_id",
        ],
        "properties": {
            "role": {"enum": ["premise", "target"]},
            "formula_id": {"type": "string", "minLength": 1},
            "formula": {"type": "string", "minLength": 1},
            "match_status": {"enum": ["exact", "equivalent", "not_found"]},
            "external_id": {"type": ["string", "null"]},
            "source_title": {"type": ["string", "null"]},
            "source_url": {"type": ["string", "null"]},
            "confidence": {"enum": ["high", "medium", "low"]},
            "evidence": {"type": "string", "minLength": 1},
            "equivalence_kind": {
                "enum": [
                    "literal", "bound_variable_renaming",
                    "operation_coordinate_permutation", "other_equivalent", "none",
                ]
            },
            "coordinate_variant_id": {"type": ["string", "null"]},
        },
    }
    finite_witness_match = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "candidate_model_id", "source_title", "source_url",
            "source_operation", "claimed_relation", "scope", "confidence",
            "evidence",
        ],
        "properties": {
            "candidate_model_id": {"type": "string", "minLength": 1},
            "source_title": {"type": "string", "minLength": 1},
            "source_url": {"type": "string", "minLength": 8},
            "source_operation": {
                "type": "object",
                "additionalProperties": False,
                "required": ["carrier_size", "arity", "table"],
                "properties": {
                    "carrier_size": {"type": "integer", "minimum": 1, "maximum": 8},
                    "arity": {"type": "integer", "minimum": 1, "maximum": 6},
                    "table": {
                        "type": "array", "minItems": 1, "maxItems": 262144,
                        "items": {"type": "integer", "minimum": 0},
                    },
                },
            },
            "claimed_relation": {
                "enum": [
                    "exact_isomorphism", "operation_coordinate_equivalent",
                    "parastrophe_equivalent", "one_way_term_reduct",
                    "mutual_term_equivalent", "unmatched",
                ]
            },
            "scope": {"const": "finite_witness_only"},
            "confidence": {"enum": ["high", "medium", "low"]},
            "evidence": {"type": "string", "minLength": 1},
        },
    }
    frozen_premises = tuple(str(row) for row in premise_formula_ids)
    premise_count = len(frozen_premises) or formula_count - 1
    premise_id_schema = (
        {"enum": list(frozen_premises)}
        if frozen_premises
        else {"type": "string", "minLength": 1}
    )
    mechanism_analysis = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "key_idea", "recombination", "invariant_or_obstruction",
            "premise_roles", "evidence_refs", "transportable_constraint",
        ],
        "properties": {
            "key_idea": {"type": "string", "minLength": 1},
            "recombination": {"type": "string", "minLength": 1},
            "invariant_or_obstruction": {"type": "string", "minLength": 1},
            "premise_roles": {
                "type": "array",
                "minItems": premise_count,
                "maxItems": premise_count,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["formula_id", "role"],
                    "properties": {
                        "formula_id": premise_id_schema,
                        "role": {"type": "string", "minLength": 1},
                    },
                },
            },
            "evidence_refs": {
                "type": "array", "minItems": 1, "maxItems": 12,
                "items": {"type": "string", "minLength": 1},
            },
            "transportable_constraint": {
                "type": "object",
                "additionalProperties": False,
                "required": ["constraint_class", "abstract_form", "invariants", "home_field"],
                "properties": {
                    "constraint_class": {"type": "string", "minLength": 1},
                    "abstract_form": {"type": "string", "minLength": 1},
                    "invariants": {
                        "type": "array",
                        "maxItems": 12,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["name", "value"],
                            "properties": {
                                "name": {"type": "string", "minLength": 1},
                                "value": {"type": "string", "minLength": 1},
                            },
                        },
                    },
                    "home_field": {"type": "string", "minLength": 1},
                },
            },
        },
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "status", "formula_matches", "implication_prior_art",
            "recognized_theory_connections", "finite_witness_matches",
            "novelty_assessment",
            "mechanism_analysis", "summary",
            "limitations", "next_checks",
        ],
        "properties": {
            "status": {"enum": ["completed", "inconclusive"]},
            "formula_matches": {
                "type": "array", "minItems": formula_count, "maxItems": formula_count,
                "items": formula_match,
            },
            "implication_prior_art": {
                "type": "array", "maxItems": 12, "items": citation,
            },
            "recognized_theory_connections": {
                "type": "array", "maxItems": 12,
                "items": {"type": "string", "minLength": 1},
            },
            "finite_witness_matches": {
                "type": "array", "maxItems": 12, "items": finite_witness_match,
            },
            "mechanism_analysis": mechanism_analysis,
            "novelty_assessment": {
                "enum": [
                    "known_implication", "likely_elementary_or_known",
                    "not_located_in_bounded_review", "conflicting_evidence",
                    "review_unavailable",
                ]
            },
            "summary": {"type": "string", "minLength": 1},
            "limitations": {
                "type": "array", "minItems": 1, "maxItems": 12,
                "items": {"type": "string", "minLength": 1},
            },
            "next_checks": {
                "type": "array", "minItems": 1, "maxItems": 12,
                "items": {"type": "string", "minLength": 1},
            },
        },
    }


def build_post_freeze_result_packet(
    attempt_dir: str | Path, *, query_index: int = 0
) -> dict[str, Any]:
    """Reveal one boundary-ranked frozen candidate and its verifier receipts."""

    directory = Path(attempt_dir)
    boundary = read_json(directory / "boundary_result.json", None)
    recheck = read_json(directory / "boundary_governance_recheck.json", None)
    blueprint_row = read_json(directory / "blueprint.json", None)
    if not all(
        isinstance(row, Mapping) and row for row in (boundary, blueprint_row)
    ):
        raise ValueError("post-freeze interpretation requires boundary and blueprint receipts")
    boundary_core = {
        key: value for key, value in boundary.items() if key != "result_sha256"
    }
    if boundary.get("result_sha256") != content_hash(boundary_core):
        raise ValueError("post-freeze boundary result digest mismatch")
    governed_rows: tuple[Mapping[str, Any], ...] = ()
    governance_digest: str | None = None
    if isinstance(recheck, Mapping) and recheck:
        recheck_core = {
            key: value for key, value in recheck.items() if key != "receipt_sha256"
        }
        if recheck.get("receipt_sha256") != content_hash(recheck_core):
            raise ValueError("post-freeze governance recheck digest mismatch")
        if recheck.get("boundary_result_sha256") != boundary.get("result_sha256"):
            raise ValueError("governance recheck is not bound to the boundary result")
        governed_rows = tuple(
            row
            for row in recheck.get("query_rechecks") or ()
            if isinstance(row, Mapping)
        )
        governance_digest = str(recheck.get("receipt_sha256") or "") or None
    boundary_rows = tuple(
        row
        for row in boundary.get("query_results") or ()
        if isinstance(row, Mapping)
    )
    rows = governed_rows or boundary_rows
    blueprint = FrontierTheoryBlueprint.from_json(blueprint_row)
    context = load_formal_theory_context(directory / "formal_context.json")
    if context.context_hash != boundary.get("context_hash"):
        raise ValueError("post-freeze context differs from the boundary result")
    formulas = {row.formula_id: row.axiom for row in context.formula_profiles}
    if (
        type(query_index) is not int
        or query_index < 0
        or query_index >= len(rows)
        or not isinstance(rows[query_index], Mapping)
    ):
        raise ValueError("post-freeze query index is outside boundary rows")
    query = rows[query_index]
    premise_ids = tuple(str(value) for value in query.get("premise_formula_ids") or ())
    target_id = str(query.get("target_formula_id") or "")
    minimum, maximum = presentation_size_bounds(blueprint)
    if (
        not minimum <= len(premise_ids) <= maximum
        or target_id not in formulas
        or any(value not in formulas for value in premise_ids)
    ):
        raise ValueError("frozen query is outside the declared formula universe")

    def formula_row(role: str, formula_id: str) -> dict[str, Any]:
        axiom = formulas[formula_id]
        return {
            "role": role,
            "formula_id": formula_id,
            "formula": render_formula_plain(axiom.formula),
            "formula_ir": axiom.formula.to_json(),
        }

    formula_rows = [formula_row("premise", row) for row in premise_ids] + [
        formula_row("target", target_id)
    ]
    base_theory = [
        {
            "name": axiom.name,
            "semantic_hash": axiom.semantic_hash,
            "formula": render_formula_plain(axiom.formula),
            "formula_ir": axiom.formula.to_json(),
        }
        for axiom in getattr(context, "base_axioms", ())
    ]
    coordinate_variants, coordinate_receipt = _coordinate_search_rows(
        context, formula_rows, base_theory
    )
    finite_witnesses, witness_receipt = _finite_witness_search_rows(
        context, premise_ids
    )
    governed = query.get("recheck") or {}
    boundary_queries = [
        row
        for row in boundary.get("query_results") or ()
        if isinstance(row, Mapping)
        and tuple(row.get("premise_formula_ids") or ()) == premise_ids
        and row.get("target_formula_id") == target_id
    ]
    if len(boundary_queries) != 1:
        raise ValueError("post-freeze selection does not identify one boundary query")
    boundary_query = boundary_queries[0]
    if not governed_rows:
        lean = boundary_query.get("lean") or {}
        lean = lean if isinstance(lean, Mapping) else {}
        governed_attempt = lean.get("governed_attempt") or {}
        governed_attempt = (
            governed_attempt if isinstance(governed_attempt, Mapping) else {}
        )
        governed = {
            "status": str(
                boundary_query.get("program_prediction_status")
                or governed_attempt.get("status")
                or lean.get("status")
                or "unresolved"
            ),
            "proof_text": governed_attempt.get("proof_text"),
            "attribution": governed_attempt.get("attribution"),
            "refutation": governed_attempt.get("refutation"),
        }
    countermodels = boundary_query.get("countermodel_searches", [])
    core = {
        "schema": POST_FREEZE_RESULT_PACKET_SCHEMA,
        "context_hash": boundary.get("context_hash"),
        "boundary_result_sha256": boundary.get("result_sha256"),
        "governance_recheck_sha256": governance_digest,
        "query_selection": {
            "query_index": query_index,
            "available_query_count": len(rows),
            "governed_query_count": len(governed_rows),
            "evidence_mode": (
                "governed_proof" if governed_rows else "boundary_disposition"
            ),
            "selection_policy": "navigator_boundary_order.v1",
        },
        "formulas": formula_rows,
        "interpretation_context": {
            "eigenquestion": str(getattr(blueprint, "eigenquestion", "")),
            "adapter_id": str(getattr(blueprint, "adapter_id", "")),
            "signature": context.signature.to_json(),
            "primitive_semantics": dict(
                getattr(blueprint, "primitive_semantics", {})
            ),
            "base_theory": base_theory,
            "visibility": "post_freeze_only",
        },
        "structural_source_search": {
            "operation_coordinate_variants": coordinate_variants,
            "coordinate_variant_receipt": coordinate_receipt,
            "finite_witnesses": finite_witnesses,
            "finite_witness_receipt": witness_receipt,
            "finite_witness_relation_order": [
                "exact_isomorphism",
                "operation_coordinate_equivalent",
                "parastrophe_equivalent",
                "mutual_term_equivalent",
                "one_way_term_reduct",
                "unmatched",
            ],
            "claim_boundary": (
                "coordinate variants are source-search queries; finite witness "
                "relations apply only to the displayed finite operations and do "
                "not establish theory or variety equivalence"
            ),
        },
        "bounded_context": {
            "complete_strata": [
                dict(row) for row in blueprint.model_or_observation_strata
            ],
            "targeted_countermodel_searches": [
                {
                    "sort_sizes": (
                        dict(row.get("sort_sizes") or {})
                        if row.get("sort_sizes") is not None
                        else (
                            {context.signature.sorts[0].name: row.get("carrier_size")}
                            if row.get("carrier_size") is not None
                            and len(context.signature.sorts) == 1
                            else {}
                        )
                    ),
                    "status": row.get("status"),
                    "receipt_sha256": row.get("receipt_sha256"),
                    "host_replay_status": row.get("host_replay_status"),
                    "witness": (
                        dict(row.get("witness") or {})
                        if isinstance(row.get("witness"), Mapping)
                        else None
                    ),
                }
                for row in countermodels
                if isinstance(row, Mapping)
            ],
        },
        "unrestricted_lean": {
            "candidate_kind": boundary_query.get(
                "candidate_kind", "compact_axiom_pack"
            ),
            "status": governed.get("status"),
            "program_prediction_status": boundary_query.get(
                "program_prediction_status", "not_applicable"
            ),
            "pack_synergy_status": boundary_query.get(
                "pack_synergy_status", "proved_proof_attributed_only"
            ),
            "logical_premise_ablation": dict(
                boundary_query.get("logical_premise_ablation")
                or {"status": "not_available_historical_attempt"}
            ),
            "proof_text": governed.get("proof_text"),
            "refutation": governed.get("refutation"),
            "boundary_disposition": boundary_query.get(
                "program_prediction_status", "not_applicable"
            ),
            "backend_status": {
                "isabelle": (boundary_query.get("isabelle") or {}).get("status"),
                "lean": (boundary_query.get("lean") or {}).get("status"),
                "formal_consensus": (
                    boundary_query.get("formal_consensus") or {}
                ).get("status"),
            },
            "attribution_receipt_sha256": (
                (governed.get("attribution") or {}).get("receipt_sha256")
                if isinstance(governed, Mapping)
                else None
            ),
            "matched_arms": (
                (governed.get("attribution") or {}).get("arms")
                if isinstance(governed, Mapping)
                else None
            ),
        },
        "source_priority": [
            "primary sources for the frozen signature and formula family",
            "official source catalogs named by verifier receipts",
            "secondary sources only as routes to primary sources",
        ],
    }
    return {**core, "packet_sha256": content_hash(core)}


__all__ = [
    "POST_FREEZE_RESULT_PACKET_SCHEMA", "build_post_freeze_result_packet",
    "post_freeze_literature_output_schema",
    "validate_post_freeze_finite_witness_matches",
]
