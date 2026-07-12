"""Evidence-bound interpretation of a verified theory candidate."""
from __future__ import annotations

from typing import Any, Mapping

from ztare.common.constraint_isomorphism import ConstraintFingerprint
from ztare.leanmill.theory_ir import content_hash


THEORY_INTERPRETATION_SCHEMA = "leanmill.theory_interpretation.v1"

_EXTERNAL_STATUS = {
    "known_implication": "catalogued",
    "likely_elementary_or_known": "likely_catalogued",
    "not_located_in_bounded_review": "unresolved",
    "conflicting_evidence": "conflicting",
}


def _receipt_refs(value: Any) -> set[str]:
    refs: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            if "sha256" in str(key).lower() and isinstance(child, str) and child:
                refs.add(child)
            refs.update(_receipt_refs(child))
    elif isinstance(value, (list, tuple)):
        for child in value:
            refs.update(_receipt_refs(child))
    return refs


def interpretation_isomorphism_fingerprint(
    interpretation: Mapping[str, Any],
) -> ConstraintFingerprint | None:
    """Project a grounded key-idea analysis onto the shared isomorphism engine."""

    mechanism = interpretation.get("mechanism_characterization")
    if (
        not isinstance(mechanism, Mapping)
        or mechanism.get("status") != "proposed_grounded"
        or mechanism.get("transport_authority")
        != "advisory_pending_destination_replay"
    ):
        return None
    transport = mechanism.get("transportable_constraint")
    if not isinstance(transport, Mapping):
        return None
    invariants = dict(transport.get("invariants") or {})
    invariants.update(
        {
            "presentation_arity": mechanism.get("presentation_arity"),
            "premise_attributed": bool(mechanism.get("premise_roles")),
        }
    )
    return ConstraintFingerprint(
        constraint_class=str(transport.get("constraint_class") or "").strip(),
        abstract_form=str(transport.get("abstract_form") or "").strip(),
        invariants=invariants,
        forbidden_domain=str(transport.get("home_field") or "").strip() or None,
    )


def interpretation_isomorphism_failure_state(
    interpretation: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Return the input shape accepted by research_isomorphism surfacing."""

    fingerprint = interpretation_isomorphism_fingerprint(interpretation)
    if fingerprint is None:
        return None
    return {
        "constraint_class": fingerprint.constraint_class,
        "abstract_form": fingerprint.abstract_form,
        "home_field": fingerprint.forbidden_domain,
        **fingerprint.invariants,
    }


def compose_theory_interpretation(
    result_packet: Mapping[str, Any],
    literature_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    """Compose verifier facts and a source-bound review without inventing meaning."""

    packet_sha = str(result_packet.get("packet_sha256") or "")
    if not packet_sha or literature_receipt.get("packet_sha256") != packet_sha:
        raise ValueError("interpretation inputs are not bound to the same frozen packet")
    literature_sha = str(literature_receipt.get("receipt_sha256") or "")
    review = literature_receipt.get("review")
    if not literature_sha or not isinstance(review, Mapping):
        raise ValueError("interpretation requires a receipted source review")

    lean = result_packet.get("unrestricted_lean")
    lean = dict(lean) if isinstance(lean, Mapping) else {}
    bounded = result_packet.get("bounded_context")
    bounded = dict(bounded) if isinstance(bounded, Mapping) else {}
    novelty = str(review.get("novelty_assessment") or "")
    external_status = _EXTERNAL_STATUS.get(novelty, "unavailable")
    if external_status in {"catalogued", "likely_catalogued"}:
        interpretation_status = "mapped_to_recorded_knowledge"
    elif lean.get("status") == "proved_attributed":
        interpretation_status = "mechanically_characterized_unmapped"
    else:
        interpretation_status = "inconclusive"

    source_rows = [
        dict(row)
        for row in review.get("implication_prior_art") or ()
        if isinstance(row, Mapping)
    ]
    formula_matches = [
        dict(row)
        for row in (
            review.get("formula_matches")
            or review.get("equation_matches")
            or ()
        )
        if isinstance(row, Mapping)
    ]
    recorded_components = bool(
        source_rows
        or review.get("recognized_theory_connections")
        or any(
            row.get("match_status") in {"exact", "equivalent"}
            for row in formula_matches
        )
    )
    origin_disposition = (
        "catalogued_recovery"
        if external_status == "catalogued"
        else "likely_routine_reconstruction"
        if external_status == "likely_catalogued"
        else "recorded_components_unmapped_recombination"
        if external_status == "unresolved" and recorded_components
        else "unmapped_candidate"
        if external_status == "unresolved"
        else "unresolved"
    )
    mechanism_raw = review.get("mechanism_analysis")
    mechanism = dict(mechanism_raw) if isinstance(mechanism_raw, Mapping) else {}
    premise_ids = {
        str(row.get("formula_id"))
        for row in result_packet.get("formulas") or ()
        if isinstance(row, Mapping) and row.get("role") == "premise"
    }
    premise_roles = [
        dict(row)
        for row in mechanism.get("premise_roles") or ()
        if isinstance(row, Mapping)
    ]
    if premise_roles and {str(row.get("formula_id")) for row in premise_roles} != premise_ids:
        raise ValueError("mechanism premise roles do not cover the frozen presentation")
    evidence_refs = [str(row) for row in mechanism.get("evidence_refs") or ()]
    if evidence_refs and not set(evidence_refs) <= _receipt_refs(result_packet):
        raise ValueError("mechanism cites evidence outside the frozen verifier packet")
    transport_raw = mechanism.get("transportable_constraint")
    transport = dict(transport_raw) if isinstance(transport_raw, Mapping) else {}
    invariants_raw = transport.get("invariants")
    if isinstance(invariants_raw, Mapping):
        invariants = dict(invariants_raw)
    elif isinstance(invariants_raw, list):
        invariants = {}
        for row in invariants_raw:
            if not isinstance(row, Mapping):
                raise ValueError("transport invariant must be a name/value object")
            name = str(row.get("name") or "").strip()
            value = str(row.get("value") or "").strip()
            if not name or not value or name in invariants:
                raise ValueError("transport invariants require unique names and values")
            invariants[name] = value
    else:
        invariants = {}
    transport["invariants"] = invariants
    candidate_kind = str(lean.get("candidate_kind") or "compact_axiom_pack")
    pack_dependency_proved = lean.get("pack_synergy_status") in {
        "proved_exact_two_synergy",
        "proved_no_singleton_suffices",
    }
    program_prediction_proved = (
        candidate_kind == "theory_program"
        and lean.get("program_prediction_status") == "kernel_verified_attributed"
    )
    if program_prediction_proved:
        mechanism_claim_boundary = "verified_theory_program_prediction"
    elif candidate_kind == "theory_program":
        mechanism_claim_boundary = "unverified_theory_program_prediction"
    elif pack_dependency_proved:
        mechanism_claim_boundary = "logical_pack_synergy"
    else:
        mechanism_claim_boundary = "saved_proof_dependency_only"
    transport_admissible = program_prediction_proved or pack_dependency_proved
    mechanism_characterization = {
        "status": "proposed_grounded" if mechanism and evidence_refs else "not_emitted",
        "key_idea": str(mechanism.get("key_idea") or "").strip(),
        "recombination": str(mechanism.get("recombination") or "").strip(),
        "invariant_or_obstruction": str(
            mechanism.get("invariant_or_obstruction") or ""
        ).strip(),
        "premise_roles": premise_roles,
        "presentation_arity": len(premise_ids),
        "evidence_refs": evidence_refs,
        "transportable_constraint": transport,
        "claim_boundary": mechanism_claim_boundary,
        "transport_authority": (
            "advisory_pending_destination_replay"
            if transport_admissible
            else "withheld_logical_premise_ablation_missing"
        ),
    }
    core = {
        "schema": THEORY_INTERPRETATION_SCHEMA,
        "status": interpretation_status,
        "context_hash": result_packet.get("context_hash"),
        "packet_sha256": packet_sha,
        "literature_receipt_sha256": literature_sha,
        "operational_characterization": {
            "formulas": [
                dict(row)
                for row in result_packet.get("formulas") or ()
                if isinstance(row, Mapping)
            ],
            "bounded_context": bounded,
            "boundary_result_sha256": result_packet.get("boundary_result_sha256"),
        },
        "dependency_characterization": {
            "candidate_kind": candidate_kind,
            "lean_status": lean.get("status"),
            "program_prediction_status": lean.get(
                "program_prediction_status", "not_applicable"
            ),
            "attribution_receipt_sha256": lean.get(
                "attribution_receipt_sha256"
            ),
            "matched_arms": lean.get("matched_arms"),
            "pack_synergy_status": lean.get(
                "pack_synergy_status", "proved_proof_attributed_only"
            ),
            "logical_premise_ablation": dict(
                lean.get("logical_premise_ablation") or {
                    "status": "not_available_historical_attempt"
                }
            ),
            "governance_recheck_sha256": result_packet.get(
                "governance_recheck_sha256"
            ),
        },
        "mechanism_characterization": mechanism_characterization,
        "external_alignment": {
            "status": external_status,
            "assessment": novelty or "unavailable",
            "origin_disposition": origin_disposition,
            "origin_claim_boundary": (
                "source-bound classification of recovery versus recombination; "
                "unmapped never certifies novelty"
            ),
            "formula_matches": formula_matches,
            "source_rows": source_rows,
            "recognized_connections": [
                str(row) for row in review.get("recognized_theory_connections") or ()
            ],
        },
        "human_gloss": {
            "summary": str(review.get("summary") or "").strip(),
            "limitations": [str(row) for row in review.get("limitations") or ()],
            "next_checks": [str(row) for row in review.get("next_checks") or ()],
            "authority": "source_review_constrained_by_verifier_receipts",
        },
    }
    return {**core, "receipt_sha256": content_hash(core)}


__all__ = [
    "THEORY_INTERPRETATION_SCHEMA",
    "compose_theory_interpretation",
    "interpretation_isomorphism_failure_state",
    "interpretation_isomorphism_fingerprint",
]
