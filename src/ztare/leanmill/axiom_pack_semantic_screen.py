"""Policy-owned fixed-size SMT screening for typed AxiomPack candidates.

The screen asks whether ``base ∧ other_candidates ∧ ¬target`` has a
model on one uniform finite carrier-size vector.  SAT witnesses are replayed
with the deterministic finite evaluator.  UNSAT remains scoped to the one
queried size vector and never grants theorem credit.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from ztare.leanmill.finite_model import FiniteModel, evaluate_axiom, validate_model
from ztare.leanmill.theory_ir import (
    AxiomFormula,
    TheorySignature,
    content_hash,
    relative_theory_content_hash,
)


AXIOM_PACK_FIXED_SIZE_SMT_QUERY_SCHEMA = (
    "leanmill.axiom_pack_fixed_size_smt_query.v1"
)
AXIOM_PACK_FIXED_SIZE_SMT_SCREEN_SCHEMA = (
    "leanmill.axiom_pack_fixed_size_smt_screen.v1"
)
AXIOM_PACK_SMT_FINDER_UNAVAILABLE_SCHEMA = (
    "leanmill.axiom_pack_smt_finder_unavailable.v1"
)
DEFAULT_FIXED_SIZE_SMT_TIMEOUT_MS = 5_000

SAT = "SAT"
UNSAT = "UNSAT"
UNKNOWN = "UNKNOWN"


def _strict_positive_int(value: Any, name: str) -> int:
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def normalize_fixed_size_smt_policy(policy: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and retain the controls owned by the fixed-size screen."""

    if not isinstance(policy, Mapping):
        raise ValueError("cheap filter policy must be an object")
    maximum = _strict_positive_int(
        policy.get("max_finite_carrier_size"), "max_finite_carrier_size"
    )
    budget = _strict_positive_int(policy.get("filter_budget_k"), "filter_budget_k")
    enumerative_maximum = _strict_positive_int(
        policy.get("semantic_max_carrier_size"), "semantic_max_carrier_size"
    )
    timeout_ms = _strict_positive_int(
        policy.get("fixed_size_smt_timeout_ms", DEFAULT_FIXED_SIZE_SMT_TIMEOUT_MS),
        "fixed_size_smt_timeout_ms",
    )
    if maximum < enumerative_maximum:
        raise ValueError(
            "max_finite_carrier_size must be at least semantic_max_carrier_size"
        )
    return {
        "max_finite_carrier_size": maximum,
        "filter_budget_k": budget,
        "semantic_max_carrier_size": enumerative_maximum,
        "fixed_size_smt_timeout_ms": timeout_ms,
        "require_countermodel_strata": policy.get("require_countermodel_strata")
        is True,
        "budget_unit": "one_target_at_one_uniform_fixed_size",
        "schedule_order": "carrier_size_descending_then_candidate_declaration_order",
    }


def _formula_id(axiom: AxiomFormula) -> str:
    return "formula:" + axiom.semantic_hash


def _receipt_hash_valid(receipt: Mapping[str, Any]) -> bool:
    unsigned = dict(receipt)
    expected = unsigned.pop("receipt_sha256", None)
    return isinstance(expected, str) and expected == content_hash(unsigned)


def _query_schedule(
    candidate_count: int,
    policy: Mapping[str, Any],
) -> list[tuple[int, int]]:
    schedule: list[tuple[int, int]] = []
    for carrier_size in range(
        int(policy["max_finite_carrier_size"]),
        int(policy["semantic_max_carrier_size"]),
        -1,
    ):
        for candidate_index in range(candidate_count):
            schedule.append((carrier_size, candidate_index))
    return schedule[: int(policy["filter_budget_k"])]


def _finder_binding(
    *,
    signature: TheorySignature,
    base_axioms: Sequence[AxiomFormula],
    premises: Sequence[AxiomFormula],
    target: AxiomFormula,
    sort_sizes: Mapping[str, int],
) -> dict[str, Any]:
    return {
        "signature_sha256": signature.content_hash,
        "sort_sizes": dict(sorted(sort_sizes.items())),
        "base_formula_ids": [_formula_id(row) for row in base_axioms],
        "premise_formula_ids": [_formula_id(row) for row in premises],
        "target_formula_id": _formula_id(target),
    }


def _finder_receipt_valid(
    receipt: Mapping[str, Any],
    *,
    expected_binding: Mapping[str, Any],
) -> bool:
    if receipt.get("schema") not in {
        "leanmill.finite_model_search.v1",
        AXIOM_PACK_SMT_FINDER_UNAVAILABLE_SCHEMA,
    }:
        return False
    if not _receipt_hash_valid(receipt):
        return False
    return all(receipt.get(key) == value for key, value in expected_binding.items())


def _unavailable_finder_receipt(
    *,
    binding: Mapping[str, Any],
    timeout_ms: int,
    reason_class: str,
    reason: str,
) -> dict[str, Any]:
    core = {
        "schema": AXIOM_PACK_SMT_FINDER_UNAVAILABLE_SCHEMA,
        "status": "unknown",
        **dict(binding),
        "solver": "unavailable",
        "timeout_ms": timeout_ms,
        "witness": None,
        "reason_class": reason_class,
        "reason": reason,
        "claim_boundary": "no solver result was admitted",
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _as_finder_receipt(
    value: Any,
    *,
    binding: Mapping[str, Any],
    timeout_ms: int,
) -> dict[str, Any]:
    try:
        row = value.to_json() if hasattr(value, "to_json") else dict(value)
    except (TypeError, ValueError) as exc:
        return _unavailable_finder_receipt(
            binding=binding,
            timeout_ms=timeout_ms,
            reason_class="invalid_finder_receipt",
            reason=f"{type(exc).__name__}: {exc}",
        )
    if not isinstance(row, dict) or not _finder_receipt_valid(
        row, expected_binding=binding
    ):
        return _unavailable_finder_receipt(
            binding=binding,
            timeout_ms=timeout_ms,
            reason_class="invalid_finder_receipt",
            reason="finder output failed schema, hash, or query-binding validation",
        )
    return row


def _not_applicable_replay() -> dict[str, Any]:
    return {
        "status": "not_applicable",
        "model_sha256": "",
        "sort_sizes_match": None,
        "base_axioms_hold": None,
        "premises_hold": None,
        "target_holds": None,
        "countermodel_confirmed": None,
        "reason": "",
    }


def _replay_countermodel(
    witness: Any,
    *,
    signature: TheorySignature,
    base_axioms: Sequence[AxiomFormula],
    premises: Sequence[AxiomFormula],
    target: AxiomFormula,
    sort_sizes: Mapping[str, int],
) -> dict[str, Any]:
    try:
        if not isinstance(witness, Mapping):
            raise ValueError("countermodel witness must be an object")
        model = FiniteModel.from_json(witness)
        validate_model(signature, model)
        sort_sizes_match = model.sort_size_map == dict(sort_sizes)
        base_hold = all(evaluate_axiom(signature, row, model) for row in base_axioms)
        premises_hold = all(evaluate_axiom(signature, row, model) for row in premises)
        target_holds = evaluate_axiom(signature, target, model)
        confirmed = sort_sizes_match and base_hold and premises_hold and not target_holds
        return {
            "status": "passed" if confirmed else "failed",
            "model_sha256": model.content_hash(signature),
            "sort_sizes_match": sort_sizes_match,
            "base_axioms_hold": base_hold,
            "premises_hold": premises_hold,
            "target_holds": target_holds,
            "countermodel_confirmed": confirmed,
            "reason": "" if confirmed else "witness does not satisfy the countermodel query",
        }
    except (TypeError, ValueError) as exc:
        return {
            "status": "failed",
            "model_sha256": "",
            "sort_sizes_match": False,
            "base_axioms_hold": False,
            "premises_hold": False,
            "target_holds": None,
            "countermodel_confirmed": False,
            "reason": f"{type(exc).__name__}: {exc}",
        }


def _interpret_finder_receipt(
    finder_receipt: Mapping[str, Any],
    *,
    signature: TheorySignature,
    base_axioms: Sequence[AxiomFormula],
    premises: Sequence[AxiomFormula],
    target: AxiomFormula,
    sort_sizes: Mapping[str, int],
) -> dict[str, Any]:
    status = str(finder_receipt.get("status") or "unknown")
    if status == "countermodel_found":
        replay = _replay_countermodel(
            finder_receipt.get("witness"),
            signature=signature,
            base_axioms=base_axioms,
            premises=premises,
            target=target,
            sort_sizes=sort_sizes,
        )
        if replay["status"] == "passed":
            return {
                "smt_verdict": SAT,
                "outcome": "countermodel_found",
                "premise_model_status": SAT,
                "host_replay": replay,
            }
        return {
            "smt_verdict": UNKNOWN,
            "outcome": "countermodel_witness_replay_failed",
            "premise_model_status": UNKNOWN,
            "host_replay": replay,
        }
    if status == "no_countermodel_at_fixed_size":
        return {
            "smt_verdict": UNSAT,
            "outcome": "no_countermodel_at_fixed_size",
            "premise_model_status": SAT,
            "host_replay": _not_applicable_replay(),
        }
    if status == "no_premise_model_at_fixed_size":
        return {
            "smt_verdict": UNSAT,
            "outcome": "no_premise_model_at_fixed_size",
            "premise_model_status": UNSAT,
            "host_replay": _not_applicable_replay(),
        }
    return {
        "smt_verdict": UNKNOWN,
        "outcome": "solver_unknown",
        "premise_model_status": UNKNOWN,
        "host_replay": _not_applicable_replay(),
    }


def _target_descriptor(index: int, axiom: AxiomFormula) -> dict[str, Any]:
    return {
        "candidate_index": index,
        "name": axiom.name,
        "axiom_sha256": axiom.content_hash,
        "formula_id": _formula_id(axiom),
    }


def _build_query_receipt(
    *,
    query_index: int,
    carrier_size: int,
    candidate_index: int,
    maximum_carrier_size: int,
    signature: TheorySignature,
    base_axioms: Sequence[AxiomFormula],
    candidate_axioms: Sequence[AxiomFormula],
    finder_receipt: Mapping[str, Any],
) -> dict[str, Any]:
    target = candidate_axioms[candidate_index]
    premises = tuple(
        row for index, row in enumerate(candidate_axioms) if index != candidate_index
    )
    sort_sizes = {sort.name: carrier_size for sort in signature.sorts}
    interpreted = _interpret_finder_receipt(
        finder_receipt,
        signature=signature,
        base_axioms=base_axioms,
        premises=premises,
        target=target,
        sort_sizes=sort_sizes,
    )
    countermodel_found = interpreted["smt_verdict"] == SAT
    core = {
        "schema": AXIOM_PACK_FIXED_SIZE_SMT_QUERY_SCHEMA,
        "query_index": query_index,
        "query_kind": "candidate_independence_countermodel",
        "target_axiom": _target_descriptor(candidate_index, target),
        "premise_axioms": [
            _target_descriptor(index, row)
            for index, row in enumerate(candidate_axioms)
            if index != candidate_index
        ],
        "signature_sha256": signature.content_hash,
        "sort_sizes": sort_sizes,
        "carrier_size_policy": "uniform_all_sorts",
        "countermodel_size": carrier_size if countermodel_found else None,
        "countermodel_size_bound": maximum_carrier_size,
        "countermodel_stratum": (
            f"uniform_fixed_size_{carrier_size}" if countermodel_found else ""
        ),
        "uses_partial_or_undefined_value": False,
        **interpreted,
        "finder_receipt": dict(finder_receipt),
        "claim_boundary": (
            "one replayed finite countermodel at one fixed uniform size"
            if countermodel_found
            else "one fixed uniform size; UNSAT grants no unbounded implication credit"
        ),
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": False,
    }
    return {**core, "receipt_sha256": content_hash(core)}


def _screen_summary(
    queries: Sequence[Mapping[str, Any]],
    *,
    candidate_axioms: Sequence[AxiomFormula],
    require_countermodel_strata: bool,
) -> dict[str, Any]:
    verdict_counts = Counter(str(row.get("smt_verdict") or UNKNOWN) for row in queries)
    outcome_counts = Counter(str(row.get("outcome") or "") for row in queries)
    by_candidate: dict[int, list[Mapping[str, Any]]] = {
        index: [] for index in range(len(candidate_axioms))
    }
    for row in queries:
        target = row.get("target_axiom") or {}
        index = target.get("candidate_index")
        if type(index) is int and index in by_candidate:
            by_candidate[index].append(row)

    candidate_outcomes: list[dict[str, Any]] = []
    all_candidates_classified = bool(candidate_axioms)
    for index, axiom in enumerate(candidate_axioms):
        rows = by_candidate[index]
        if any(row.get("smt_verdict") == SAT for row in rows):
            classification = "countermodel_found"
        elif rows and all(
            row.get("outcome") == "no_countermodel_at_fixed_size" for row in rows
        ):
            classification = "no_countermodel_on_queried_fixed_sizes"
        elif any(row.get("outcome") == "no_premise_model_at_fixed_size" for row in rows):
            classification = "premises_unsatisfiable_on_queried_fixed_size"
            all_candidates_classified = False
        else:
            classification = "unknown"
            all_candidates_classified = False
        candidate_outcomes.append(
            {
                "candidate_index": index,
                "name": axiom.name,
                "axiom_sha256": axiom.content_hash,
                "classification": classification,
                "query_receipt_sha256s": [row.get("receipt_sha256") for row in rows],
                "queried_carrier_sizes": sorted(
                    {
                        next(iter((row.get("sort_sizes") or {}).values()))
                        for row in rows
                        if row.get("sort_sizes")
                    },
                    reverse=True,
                ),
            }
        )

    countermodel_edges = [
        {
            "background_axioms": [
                item.get("name") for item in row.get("premise_axioms") or []
            ],
            "does_not_imply": (row.get("target_axiom") or {}).get("name"),
            "countermodel_size": row.get("countermodel_size"),
            "witness_model_sha256": (row.get("host_replay") or {}).get(
                "model_sha256"
            ),
            "query_receipt_sha256": row.get("receipt_sha256"),
        }
        for row in queries
        if row.get("smt_verdict") == SAT
    ]
    fixed_size_implication_edges = [
        {
            "background_axioms": [
                item.get("name") for item in row.get("premise_axioms") or []
            ],
            "implies_at_fixed_size": (row.get("target_axiom") or {}).get("name"),
            "sort_sizes": row.get("sort_sizes"),
            "query_receipt_sha256": row.get("receipt_sha256"),
            "proof_credit_eligible": False,
        }
        for row in queries
        if row.get("outcome") == "no_countermodel_at_fixed_size"
    ]
    countermodel_requirement_satisfied = (
        not require_countermodel_strata or bool(countermodel_edges)
    )
    return {
        "verdict_counts": {
            SAT: verdict_counts[SAT],
            UNSAT: verdict_counts[UNSAT],
            UNKNOWN: verdict_counts[UNKNOWN],
        },
        "outcome_counts": dict(sorted(outcome_counts.items())),
        "candidate_outcomes": candidate_outcomes,
        "all_candidates_classified": all_candidates_classified,
        "countermodel_requirement_satisfied": countermodel_requirement_satisfied,
        "countermodel_edges": countermodel_edges,
        "fixed_size_implication_edges": fixed_size_implication_edges,
    }


def _assemble_screen_receipt(
    *,
    pack: Any,
    signature: TheorySignature,
    base_axioms: Sequence[AxiomFormula],
    candidate_axioms: Sequence[AxiomFormula],
    policy: Mapping[str, Any],
    queries: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    from ztare.leanmill.axiom_authority import pack_digest

    schedule = _query_schedule(len(candidate_axioms), policy)
    summary = _screen_summary(
        queries,
        candidate_axioms=candidate_axioms,
        require_countermodel_strata=bool(policy["require_countermodel_strata"]),
    )
    if not schedule:
        status = "not_applicable"
    elif (
        summary["all_candidates_classified"]
        and summary["countermodel_requirement_satisfied"]
    ):
        status = "pass"
    else:
        status = "inconclusive"
    available = (
        int(policy["max_finite_carrier_size"])
        - int(policy["semantic_max_carrier_size"])
    ) * len(candidate_axioms)
    core = {
        "schema": AXIOM_PACK_FIXED_SIZE_SMT_SCREEN_SCHEMA,
        "status": status,
        "pack_digest": pack_digest(pack),
        "theory_digest": relative_theory_content_hash(
            signature, candidate_axioms, base_axioms=base_axioms
        ),
        "signature_sha256": signature.content_hash,
        "policy": dict(policy),
        "candidate_count": len(candidate_axioms),
        "available_query_count": available,
        "scheduled_query_count": len(schedule),
        "filter_budget_k": int(policy["filter_budget_k"]),
        "filter_budget_used": len(schedule),
        "budget_exhausted": len(schedule) < available,
        "queries": [dict(row) for row in queries],
        "summary": summary,
        "claim_boundary": (
            "fixed finite size vectors above the enumerative head; SAT witnesses are "
            "replayed, while UNSAT is size-local"
        ),
        "proof_credit_eligible": False,
        "theorem_campaign_admissible": False,
    }
    return {**core, "receipt_sha256": content_hash(core)}


def run_fixed_size_smt_screen(
    *,
    pack: Any,
    signature: TheorySignature,
    base_axioms: Sequence[AxiomFormula],
    candidate_axioms: Sequence[AxiomFormula],
    policy: Mapping[str, Any],
    countermodel_finder: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Run the deterministic boundary-first SMT query schedule."""

    from ztare.leanmill.finite_table_model_finder import find_finite_countermodel

    normalized = normalize_fixed_size_smt_policy(policy)
    finder = countermodel_finder or find_finite_countermodel
    schedule = _query_schedule(len(candidate_axioms), normalized)
    timeout_ms = int(normalized["fixed_size_smt_timeout_ms"])
    queries: list[dict[str, Any]] = []
    for query_index, (carrier_size, candidate_index) in enumerate(schedule):
        target = candidate_axioms[candidate_index]
        premises = tuple(
            row
            for index, row in enumerate(candidate_axioms)
            if index != candidate_index
        )
        sort_sizes = {sort.name: carrier_size for sort in signature.sorts}
        binding = _finder_binding(
            signature=signature,
            base_axioms=base_axioms,
            premises=premises,
            target=target,
            sort_sizes=sort_sizes,
        )
        try:
            result = finder(
                signature,
                premises,
                target,
                sort_sizes=sort_sizes,
                base_axioms=base_axioms,
                timeout_ms=timeout_ms,
            )
            finder_receipt = _as_finder_receipt(
                result, binding=binding, timeout_ms=timeout_ms
            )
        except Exception as exc:  # noqa: BLE001 - runtime gaps become typed UNKNOWN
            finder_receipt = _unavailable_finder_receipt(
                binding=binding,
                timeout_ms=timeout_ms,
                reason_class="finder_runtime_unavailable",
                reason=f"{type(exc).__name__}: {exc}",
            )
        queries.append(
            _build_query_receipt(
                query_index=query_index,
                carrier_size=carrier_size,
                candidate_index=candidate_index,
                maximum_carrier_size=int(normalized["max_finite_carrier_size"]),
                signature=signature,
                base_axioms=base_axioms,
                candidate_axioms=candidate_axioms,
                finder_receipt=finder_receipt,
            )
        )

    return _assemble_screen_receipt(
        pack=pack,
        signature=signature,
        base_axioms=base_axioms,
        candidate_axioms=candidate_axioms,
        policy=normalized,
        queries=queries,
    )


def verify_fixed_size_smt_screen(
    *,
    pack: Any,
    signature: TheorySignature,
    base_axioms: Sequence[AxiomFormula],
    candidate_axioms: Sequence[AxiomFormula],
    receipt: Mapping[str, Any],
) -> tuple[bool, list[str]]:
    """Replay screen bindings, schedule, hashes, and every SAT witness."""

    from ztare.leanmill.axiom_authority import pack_digest

    failures: list[str] = []
    if not isinstance(receipt, Mapping):
        return False, ["screen_receipt_missing"]
    if receipt.get("schema") != AXIOM_PACK_FIXED_SIZE_SMT_SCREEN_SCHEMA:
        failures.append("screen_schema")
    if not _receipt_hash_valid(receipt):
        failures.append("screen_receipt_hash")
    if receipt.get("pack_digest") != pack_digest(pack):
        failures.append("screen_pack_digest")
    expected_theory = relative_theory_content_hash(
        signature, candidate_axioms, base_axioms=base_axioms
    )
    if receipt.get("theory_digest") != expected_theory:
        failures.append("screen_theory_digest")
    if receipt.get("signature_sha256") != signature.content_hash:
        failures.append("screen_signature")
    try:
        normalized = normalize_fixed_size_smt_policy(receipt.get("policy") or {})
    except (TypeError, ValueError) as exc:
        return False, [*failures, f"screen_policy:{exc}"]
    if receipt.get("policy") != normalized:
        failures.append("screen_policy_not_normalized")
    expected_schedule = _query_schedule(len(candidate_axioms), normalized)
    queries = receipt.get("queries")
    if not isinstance(queries, list):
        return False, [*failures, "screen_queries_missing"]
    if len(queries) != len(expected_schedule):
        failures.append("screen_query_count")

    replayed_queries: list[dict[str, Any]] = []
    for query_index, expected in enumerate(expected_schedule):
        if query_index >= len(queries) or not isinstance(queries[query_index], Mapping):
            failures.append(f"query_{query_index}:missing")
            continue
        query = dict(queries[query_index])
        carrier_size, candidate_index = expected
        target = candidate_axioms[candidate_index]
        premises = tuple(
            row
            for index, row in enumerate(candidate_axioms)
            if index != candidate_index
        )
        sort_sizes = {sort.name: carrier_size for sort in signature.sorts}
        binding = _finder_binding(
            signature=signature,
            base_axioms=base_axioms,
            premises=premises,
            target=target,
            sort_sizes=sort_sizes,
        )
        if query.get("schema") != AXIOM_PACK_FIXED_SIZE_SMT_QUERY_SCHEMA:
            failures.append(f"query_{query_index}:schema")
        if not _receipt_hash_valid(query):
            failures.append(f"query_{query_index}:receipt_hash")
        if query.get("query_index") != query_index:
            failures.append(f"query_{query_index}:index")
        if query.get("target_axiom") != _target_descriptor(candidate_index, target):
            failures.append(f"query_{query_index}:target")
        expected_premises = [
            _target_descriptor(index, row)
            for index, row in enumerate(candidate_axioms)
            if index != candidate_index
        ]
        if query.get("premise_axioms") != expected_premises:
            failures.append(f"query_{query_index}:premises")
        finder_receipt = query.get("finder_receipt")
        if not isinstance(finder_receipt, Mapping) or not _finder_receipt_valid(
            finder_receipt, expected_binding=binding
        ):
            failures.append(f"query_{query_index}:finder_receipt")
            continue
        rebuilt = _build_query_receipt(
            query_index=query_index,
            carrier_size=carrier_size,
            candidate_index=candidate_index,
            maximum_carrier_size=int(normalized["max_finite_carrier_size"]),
            signature=signature,
            base_axioms=base_axioms,
            candidate_axioms=candidate_axioms,
            finder_receipt=finder_receipt,
        )
        if query != rebuilt:
            failures.append(f"query_{query_index}:deterministic_replay")
        replayed_queries.append(rebuilt)

    expected_receipt = _assemble_screen_receipt(
        pack=pack,
        signature=signature,
        base_axioms=base_axioms,
        candidate_axioms=candidate_axioms,
        policy=normalized,
        queries=replayed_queries,
    )
    if dict(receipt) != expected_receipt:
        failures.append("screen_deterministic_replay")
    return not failures, failures


__all__ = [
    "AXIOM_PACK_FIXED_SIZE_SMT_QUERY_SCHEMA",
    "AXIOM_PACK_FIXED_SIZE_SMT_SCREEN_SCHEMA",
    "DEFAULT_FIXED_SIZE_SMT_TIMEOUT_MS",
    "SAT",
    "UNKNOWN",
    "UNSAT",
    "normalize_fixed_size_smt_policy",
    "run_fixed_size_smt_screen",
    "verify_fixed_size_smt_screen",
]
