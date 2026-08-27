"""Prospective paired evaluation of valuation-grammar revision conjectures."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_text, timestamp_key
from .valuation import valuation_grammar_contract
from .valuation_grammar_residual_learning import (
    VALUATION_GRAMMAR_CONJECTURE_SCHEMA,
    VALUATION_GRAMMAR_LEARNING_SCHEMA,
)


EVALUATION_SCHEDULE_SCHEMA = "jaggedthoughts-valuation-grammar-evaluation-schedule-v1"
REVISION_MANIFEST_SCHEMA = "jaggedthoughts-valuation-grammar-revision-manifest-v1"
PAIRED_RESULT_SCHEMA = "jaggedthoughts-valuation-grammar-paired-result-v1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _verified(raw: Mapping[str, Any], schema: str, digest_field: str) -> dict[str, Any]:
    row = dict(raw)
    if row.get("schema") != schema:
        raise ValueError(f"artifact requires {schema}")
    claimed = require_text(row.get(digest_field), digest_field)
    if claimed != stable_sha256({key: value for key, value in row.items() if key != digest_field}):
        raise ValueError(f"{digest_field} does not match its payload")
    return row


def _candidate_shas(conjectures: Iterable[Mapping[str, Any]]) -> set[str]:
    return {
        require_text(candidate.get("candidate_sha256"), "selection candidate_sha256")
        for conjecture in conjectures
        for field in ("supporting_candidates", "counterexamples")
        for candidate in conjecture.get(field) or ()
        if isinstance(candidate, Mapping)
    }


def _verified_discovery(raw: Mapping[str, Any]) -> dict[str, Any]:
    discovery = _verified(raw, "jaggedthoughts-discovery-run-v1", "run_sha256")
    canonical_timestamp(discovery.get("as_of"), "discovery as_of")
    require_text(discovery.get("source_run_sha256"), "discovery source_run_sha256")
    for candidate in discovery.get("candidates") or ():
        if not isinstance(candidate, Mapping):
            raise ValueError("discovery candidates must be objects")
        _verified(candidate, "jaggedthoughts-discovery-candidate-v1", "candidate_sha256")
    return discovery


def _result_contract() -> dict[str, Any]:
    return {
        "schema": PAIRED_RESULT_SCHEMA,
        "identity_fields": [
            "evaluation_id", "conjecture_sha256", "control_grammar_contract_sha256",
            "revision_manifest_sha256", "future_discovery_run_sha256",
            "future_source_run_sha256", "common_candidate_cohort_sha256",
        ],
        "paired_arm_metrics": {
            "coverage": {
                "fields": ["eligible_candidate_count", "evaluated_candidate_count", "coverage_ratio"],
                "formula": "evaluated_candidate_count / eligible_candidate_count",
            },
            "positive_state_price_feasibility": {
                "fields": ["feasible_candidate_count", "feasibility_ratio"],
                "formula": "feasible_candidate_count / evaluated_candidate_count",
            },
            "identification_width": {
                "field": "mean_common_projection_width",
                "formula": (
                    "mean candidate width after projecting each arm's feasible state-price set "
                    "onto the frozen control payoff coordinates"
                ),
                "null_when": "a common payoff-coordinate projection cannot be compiled",
            },
        },
        "out_of_sample_settlement": {
            "nullable_until_due": True,
            "status_values": ["not_due", "settled", "source_gap"],
            "required_when_settled": [
                "settled_at", "horizon_days", "settled_candidate_count", "metric_id",
                "control_error", "revision_error", "source_refs",
            ],
        },
        "comparison_rule": "compare arms only on identical candidate, source, and payoff-input identities",
        "automatic_revision_activation": False,
        "security_ranking_use": False,
        "capital_authority": False,
    }


def schedule_valuation_grammar_evaluations(
    learning: Mapping[str, Any],
    selection_discovery: Mapping[str, Any],
    *,
    future_discovery: Mapping[str, Any] | None = None,
    revision_manifests: Iterable[Mapping[str, Any]] = (),
    scheduled_at: str | None = None,
) -> dict[str, Any]:
    """Schedule, and when inputs exist activate, one paired trial per conjecture."""

    at = canonical_timestamp(scheduled_at or _now(), "scheduled_at")
    learned = _verified(learning, VALUATION_GRAMMAR_LEARNING_SCHEMA, "learning_sha256")
    selection = _verified_discovery(selection_discovery)
    grammar = valuation_grammar_contract()
    if learned.get("valuation_grammar_contract_sha256") != grammar["contract_sha256"]:
        raise ValueError("learning artifact is not bound to the current control grammar")
    conjectures = [dict(row) for row in learned.get("conjectures") or ()]
    for conjecture in conjectures:
        _verified(conjecture, VALUATION_GRAMMAR_CONJECTURE_SCHEMA, "conjecture_sha256")
    selection_candidates = _candidate_shas(conjectures)
    discovery_candidates = {
        str(candidate.get("candidate_sha256") or "") for candidate in selection.get("candidates") or ()
    }
    if not selection_candidates <= discovery_candidates:
        raise ValueError("selection discovery does not contain the learning cohort candidates")

    manifests = {}
    for raw in revision_manifests:
        manifest = _verified(raw, REVISION_MANIFEST_SCHEMA, "revision_manifest_sha256")
        conjecture_id = require_text(manifest.get("conjecture_id"), "revision conjecture_id")
        if conjecture_id in manifests:
            raise ValueError("at most one revision manifest is allowed per conjecture")
        manifests[conjecture_id] = manifest

    future = _verified_discovery(future_discovery) if future_discovery is not None else None
    future_cohort = None
    if future is not None:
        threshold = max(
            [timestamp_key(str(selection["as_of"])), timestamp_key(at)]
            + [timestamp_key(str(row["future_evaluation_contract"]["not_before"])) for row in conjectures]
        )
        if timestamp_key(str(future["as_of"])) <= threshold:
            raise ValueError("future discovery must be strictly later than selection and scheduling epochs")
        if future["run_sha256"] == selection["run_sha256"]:
            raise ValueError("future discovery cannot reuse the selection run")
        if future["source_run_sha256"] == selection["source_run_sha256"]:
            raise ValueError("future discovery must use a new source epoch")
        candidates = sorted(
            str(row["candidate_sha256"])
            for row in future.get("candidates") or ()
            if row.get("entity_kind") == "public_equity"
            and isinstance(row.get("valuation"), Mapping)
            and row["valuation"].get("envelope_sha256")
            and str(row.get("candidate_sha256") or "") not in selection_candidates
        )
        cohort_body = {
            "future_discovery_run_sha256": future["run_sha256"],
            "future_source_run_sha256": future["source_run_sha256"],
            "future_as_of": future["as_of"],
            "candidate_sha256s": candidates,
        }
        future_cohort = {**cohort_body, "common_candidate_cohort_sha256": stable_sha256(cohort_body)}

    result_contract = _result_contract()
    result_contract = {
        **result_contract,
        "result_contract_sha256": stable_sha256(result_contract),
    }
    evaluations = []
    for conjecture in conjectures:
        manifest = manifests.get(str(conjecture["conjecture_id"]))
        gaps = []
        if future_cohort is None:
            gaps.append("strictly_new_discovery_and_source_epoch")
        elif len(future_cohort["candidate_sha256s"]) < int(
            conjecture["future_evaluation_contract"]["minimum_future_candidates"]
        ):
            gaps.append("minimum_common_future_candidate_count")
        if manifest is None:
            gaps.append("one_versioned_revision_manifest")
        else:
            require_text(manifest.get("implementation_ref"), "revision implementation_ref")
            require_text(manifest.get("implementation_sha256"), "revision implementation_sha256")
            require_text(manifest.get("revision_delta_sha256"), "revision revision_delta_sha256")
            expected = {
                "revision_count": 1,
                "conjecture_sha256": conjecture["conjecture_sha256"],
                "revision_kind": conjecture["revision_kind"],
                "base_grammar_contract_sha256": grammar["contract_sha256"],
                "affected_ast_operators": conjecture["affected_ast_operators"],
                "affected_ast_terminals": conjecture["affected_ast_terminals"],
                "automatic_revision_activation": False,
                "security_ranking_use": False,
                "capital_authority": False,
            }
            if any(manifest.get(key) != value for key, value in expected.items()):
                raise ValueError("revision manifest does not match its conjecture boundary")
        identity = {
            "learning_sha256": learned["learning_sha256"],
            "conjecture_sha256": conjecture["conjecture_sha256"],
            "control_grammar_contract_sha256": grammar["contract_sha256"],
            "revision_manifest_sha256": manifest.get("revision_manifest_sha256") if manifest else None,
            "common_candidate_cohort_sha256": (
                future_cohort.get("common_candidate_cohort_sha256") if future_cohort else None
            ),
        }
        evaluations.append({
            "evaluation_id": f"valuation-grammar-eval:{stable_sha256(identity)[:20]}",
            "conjecture_id": conjecture["conjecture_id"],
            "conjecture_sha256": conjecture["conjecture_sha256"],
            "revision_kind": conjecture["revision_kind"],
            "status": "ready_for_paired_execution" if not gaps else "awaiting_activation_inputs",
            "control_arm": {"grammar_contract_sha256": grammar["contract_sha256"]},
            "revision_arm": {
                "exactly_one_revision": True,
                "manifest": manifest,
                "required_revision_kind": conjecture["revision_kind"],
            },
            "common_candidate_cohort_sha256": (
                future_cohort.get("common_candidate_cohort_sha256") if future_cohort else None
            ),
            "paired_input_contract": {
                "same_candidate_sha256": True,
                "same_source_run_sha256": True,
                "same_valuation_envelope_sha256": True,
                "same_spot_observation": True,
                "same_payoff_state_scope": True,
                "same_numeraire_contract": True,
                "same_near_zero_threshold": True,
            },
            "activation_requirements": gaps,
            "paired_result_contract_sha256": result_contract["result_contract_sha256"],
            "historical_retrofit_allowed": False,
            "automatic_revision_activation": False,
            "security_ranking_use": False,
            "capital_authority": False,
        })

    body = {
        "schema": EVALUATION_SCHEDULE_SCHEMA,
        "scheduled_at": at,
        "learning_sha256": learned["learning_sha256"],
        "selection_discovery_run_sha256": selection["run_sha256"],
        "selection_source_run_sha256": selection["source_run_sha256"],
        "control_grammar_contract": grammar,
        "common_future_cohort": future_cohort,
        "paired_result_contract": result_contract,
        "evaluation_count": len(evaluations),
        "ready_count": sum(row["status"] == "ready_for_paired_execution" for row in evaluations),
        "evaluations": evaluations,
        "historical_retrofit_allowed": False,
        "automatic_revision_activation": False,
        "security_ranking_use": False,
        "capital_authority": False,
    }
    return {**body, "schedule_sha256": stable_sha256(body)}


__all__ = [
    "EVALUATION_SCHEDULE_SCHEMA", "PAIRED_RESULT_SCHEMA", "REVISION_MANIFEST_SCHEMA",
    "schedule_valuation_grammar_evaluations",
]
