"""Post-freeze literature packet and strict result contract for AxiomPack."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from ztare.leanmill.common import read_json
from ztare.leanmill.frontier_blueprint import (
    FrontierTheoryBlueprint,
    presentation_size_bounds,
)
from ztare.leanmill.finite_theory_context import load_formal_theory_context
from ztare.leanmill.theory_ir import content_hash, render_formula_plain


def post_freeze_literature_output_schema(*, formula_count: int = 3) -> dict[str, Any]:
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
        },
    }
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
                "maxItems": formula_count - 1,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["formula_id", "role"],
                    "properties": {
                        "formula_id": {"type": "string", "minLength": 1},
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
            "recognized_theory_connections", "novelty_assessment",
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
        isinstance(row, Mapping) and row
        for row in (boundary, recheck, blueprint_row)
    ):
        raise ValueError(
            "post-freeze interpretation requires boundary and governance receipts"
        )
    boundary_core = {
        key: value for key, value in boundary.items() if key != "result_sha256"
    }
    if boundary.get("result_sha256") != content_hash(boundary_core):
        raise ValueError("post-freeze boundary result digest mismatch")
    recheck_core = {
        key: value for key, value in recheck.items() if key != "receipt_sha256"
    }
    if recheck.get("receipt_sha256") != content_hash(recheck_core):
        raise ValueError("post-freeze governance recheck digest mismatch")
    if recheck.get("boundary_result_sha256") != boundary.get("result_sha256"):
        raise ValueError("governance recheck is not bound to the boundary result")
    blueprint = FrontierTheoryBlueprint.from_json(blueprint_row)
    context = load_formal_theory_context(directory / "formal_context.json")
    if context.context_hash != boundary.get("context_hash"):
        raise ValueError("post-freeze context differs from the boundary result")
    formulas = {row.formula_id: row.axiom for row in context.formula_profiles}
    rows = tuple(recheck.get("query_rechecks") or ())
    if (
        type(query_index) is not int
        or query_index < 0
        or query_index >= len(rows)
        or not isinstance(rows[query_index], Mapping)
    ):
        raise ValueError("post-freeze query index is outside governed boundary rows")
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
    governed = query.get("recheck") or {}
    boundary_queries = [
        row
        for row in boundary.get("query_results") or ()
        if isinstance(row, Mapping)
        and tuple(row.get("premise_formula_ids") or ()) == premise_ids
        and row.get("target_formula_id") == target_id
    ]
    if len(boundary_queries) != 1:
        raise ValueError("governance recheck does not identify one boundary query")
    boundary_query = boundary_queries[0]
    countermodels = boundary_query.get("countermodel_searches", [])
    core = {
        "schema": "leanmill.post_freeze_result_packet.v3",
        "context_hash": boundary.get("context_hash"),
        "boundary_result_sha256": boundary.get("result_sha256"),
        "governance_recheck_sha256": recheck.get("receipt_sha256"),
        "query_selection": {
            "query_index": query_index,
            "governed_query_count": len(rows),
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
    "build_post_freeze_result_packet", "post_freeze_literature_output_schema",
]
