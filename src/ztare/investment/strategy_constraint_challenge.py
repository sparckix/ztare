"""Compile source-bound additive refinements of a strategy choice space."""

from __future__ import annotations

from copy import deepcopy
from itertools import combinations
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_finite, require_text, timestamp_key
from .strategy_options import (
    RESULT_SCHEMA as FRONTIER_RESULT_SCHEMA,
    compile_company_strategy_frontier,
)


REQUEST_SCHEMA = "jaggedthoughts-strategy-constraint-challenge-request-v1"
RESULT_SCHEMA = "jaggedthoughts-strategy-constraint-challenge-result-v1"
MAX_CANDIDATE_PREDICATES = 12
GATE_SCHEMA = "jaggedthoughts-strategy-constraint-frontier-gate-v1"
INDEPENDENCE_SCHEMA = "jaggedthoughts-strategy-constraint-independence-certificate-v1"
RUNTIME_PROVENANCE_SCHEMA = "jaggedthoughts-strategy-constraint-runtime-provenance-v1"
CANDIDATE_FREEZE_SCHEMA = "jaggedthoughts-strategy-constraint-candidate-freeze-v1"


def _content_hash(row: Mapping[str, Any], field: str) -> bool:
    return row.get(field) == stable_sha256({
        key: value for key, value in row.items() if key != field
    })


def _bundle(raw: Iterable[Any], option_ids: set[str], label: str) -> list[str]:
    values = sorted({require_text(value, label) for value in raw})
    if not values or not set(values) <= option_ids:
        raise ValueError(f"{label} crosses the parent option vocabulary")
    return values


def _examples(raw: Mapping[str, Any], option_ids: set[str]) -> dict[str, Any]:
    admitted = sorted({
        tuple(_bundle(row, option_ids, "admitted bundle option"))
        for row in raw.get("admitted_bundles") or ()
    })
    excluded = sorted({
        tuple(_bundle(row, option_ids, "excluded bundle option"))
        for row in raw.get("excluded_bundles") or ()
    })
    if set(admitted) & set(excluded):
        raise ValueError("a challenge bundle cannot be both admitted and excluded")
    implications = []
    for row in raw.get("implication_pairs") or ():
        if not isinstance(row, Mapping):
            raise ValueError("constraint implication pairs must be objects")
        antecedent = _bundle(
            row.get("antecedent_option_ids") or (), option_ids,
            "implication antecedent option",
        )
        required = _bundle(
            row.get("required_option_ids") or (), option_ids,
            "implication required option",
        )
        if set(antecedent) & set(required):
            raise ValueError("constraint implication sides must be disjoint")
        implications.append({
            "antecedent_option_ids": antecedent,
            "required_option_ids": required,
        })
    implications.sort(key=stable_sha256)
    if not excluded and not implications:
        raise ValueError("constraint challenge examples contain no exclusion pressure")
    return {
        "admitted_bundles": [list(row) for row in admitted],
        "excluded_bundles": [list(row) for row in excluded],
        "implication_pairs": implications,
    }


def _predicate(
    raw: Mapping[str, Any], option_ids: set[str], source_ids: set[str],
) -> dict[str, Any]:
    kind = require_text(raw.get("predicate_kind"), "candidate predicate kind")
    constraint_id = require_text(raw.get("constraint_id"), "candidate constraint id")
    refs = sorted({
        require_text(value, "candidate predicate evidence ref")
        for value in raw.get("evidence_refs") or ()
    })
    if not refs or not set(refs) <= source_ids:
        raise ValueError(f"candidate predicate {constraint_id} has unbound evidence")
    body: dict[str, Any] = {
        "predicate_kind": kind, "constraint_id": constraint_id,
        "evidence_refs": refs,
    }
    if kind == "incompatibility":
        option_pair = _bundle(
            raw.get("option_ids") or (), option_ids,
            f"candidate predicate {constraint_id} option",
        )
        if len(option_pair) != 2:
            raise ValueError("an incompatibility requires exactly two options")
        body["option_ids"] = option_pair
    elif kind == "prerequisite":
        option_id = require_text(raw.get("option_id"), "prerequisite option")
        required = _bundle(
            raw.get("requires") or (), option_ids,
            f"candidate predicate {constraint_id} required option",
        )
        if option_id not in option_ids or option_id in required:
            raise ValueError("a prerequisite crosses its option vocabulary")
        body.update({"option_id": option_id, "requires": required})
    elif kind == "resource_limit":
        uses_raw = raw.get("uses")
        if not isinstance(uses_raw, Mapping) or not uses_raw:
            raise ValueError("a resource predicate requires typed option uses")
        uses = {
            str(option_id): require_finite(amount, "candidate resource use")
            for option_id, amount in uses_raw.items()
        }
        limit = require_finite(raw.get("limit"), "candidate resource limit")
        if not set(uses) <= option_ids or limit < 0 or any(value < 0 for value in uses.values()):
            raise ValueError("a resource predicate has invalid uses or limit")
        body.update({
            "resource_id": require_text(raw.get("resource_id"), "candidate resource id"),
            "unit": require_text(raw.get("unit"), "candidate resource unit"),
            "limit": limit, "uses": dict(sorted(uses.items())),
        })
    else:
        raise ValueError(f"unsupported candidate predicate kind: {kind}")
    return {**body, "predicate_sha256": stable_sha256(body)}


def normalize_strategy_constraint_candidates(
    parent: Mapping[str, Any], candidate_constraints: Mapping[str, Any],
    source_ids: Iterable[str],
) -> list[dict[str, Any]]:
    """Normalize typed candidate rows without observing challenge examples."""
    if parent.get("schema") != FRONTIER_RESULT_SCHEMA or not _content_hash(
        parent, "strategy_frontier_sha256",
    ):
        raise ValueError("constraint candidates require an intact parent frontier")
    option_ids = set(map(str, (parent.get("choice_space_certificate") or {}).get("option_ids") or ()))
    sources = {require_text(value, "constraint candidate source id") for value in source_ids}
    candidates = []
    for key, predicate_kind in zip(
        ("incompatibilities", "prerequisites", "resources"),
        ("incompatibility", "prerequisite", "resource_limit"), strict=True,
    ):
        candidates.extend(
            _predicate({"predicate_kind": predicate_kind, **dict(row)}, option_ids, sources)
            for row in candidate_constraints.get(key) or ()
        )
    candidates.sort(key=lambda row: row["predicate_sha256"])
    if len(candidates) > MAX_CANDIDATE_PREDICATES:
        raise ValueError("constraint candidate set exceeds twelve predicates")
    if len({row["constraint_id"] for row in candidates}) != len(candidates):
        raise ValueError("candidate constraint ids must be unique")
    feasible = {
        frozenset(map(str, row.get("option_ids") or ()))
        for row in (parent.get("choice_space_certificate") or {}).get("feasible_bundles") or ()
    }
    decorated = []
    for predicate in candidates:
        semantic_body = {
            key: value for key, value in predicate.items()
            if key not in {"constraint_id", "evidence_refs", "predicate_sha256"}
        }
        rejected = sorted(
            "|".join(sorted(bundle)) for bundle in feasible if not _permits(predicate, bundle)
        )
        if not rejected or len(rejected) == len(feasible):
            raise ValueError("candidate predicate is vacuous or rejects the entire parent space")
        decorated.append({
            **predicate,
            "predicate_semantics_sha256": stable_sha256(semantic_body),
            "predicate_effect_sha256": stable_sha256(rejected),
            "rejected_parent_bundle_count": len(rejected),
        })
    if len({row["predicate_semantics_sha256"] for row in decorated}) != len(decorated):
        raise ValueError("candidate predicates contain duplicate semantics")
    if len({row["predicate_effect_sha256"] for row in decorated}) != len(decorated):
        raise ValueError("candidate predicates are not behaviorally distinct on the parent space")
    return decorated


def compile_strategy_constraint_candidate_freeze(
    parent: Mapping[str, Any], *, candidate_constraints: Mapping[str, Any],
    source_ids: Iterable[str], observed_at: str, available_at: str,
    runtime_provenance: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Freeze candidates before any blind holdout examples are acquired."""
    candidates = normalize_strategy_constraint_candidates(
        parent, candidate_constraints, source_ids,
    )
    if not candidates:
        raise ValueError("constraint candidate freeze requires a predicate")
    runtime = dict(runtime_provenance or {})
    runtime_sha = runtime.pop("provenance_sha256", "")
    if (
        runtime.get("schema") != RUNTIME_PROVENANCE_SCHEMA
        or runtime.get("authority") != "worker_verified_subscription_receipts"
        or runtime_sha != stable_sha256(runtime)
    ):
        raise ValueError("constraint candidate freeze requires verified runtime provenance")
    receipt = require_text(
        runtime.get("candidate_call_receipt_sha256"), "candidate call receipt",
    )
    if len(receipt) != 64 or any(
        character not in "0123456789abcdef" for character in receipt
    ):
        raise ValueError("candidate call receipt must be a sha256")
    observed = canonical_timestamp(observed_at, "candidate freeze observed_at")
    available = canonical_timestamp(available_at, "candidate freeze available_at")
    if timestamp_key(available) < timestamp_key(observed):
        raise ValueError("candidate freeze predates its observation")
    parent_constraints = parent.get("feasibility_constraints") or {}
    existing_ids = {
        str(row.get("constraint_id"))
        for key in ("incompatibilities", "prerequisites", "resources")
        for row in parent_constraints.get(key) or ()
    }
    if existing_ids & {row["constraint_id"] for row in candidates}:
        raise ValueError("constraint candidate freeze must be additive to its parent")
    body = {
        "schema": CANDIDATE_FREEZE_SCHEMA,
        "parent_strategy_frontier_sha256": parent["strategy_frontier_sha256"],
        "parent_choice_space_sha256": (parent.get("choice_space_certificate") or {})[
            "choice_space_sha256"
        ],
        "candidate_predicates": candidates,
        "candidate_predicate_sha256s": [row["predicate_sha256"] for row in candidates],
        "candidate_semantics_set_sha256": stable_sha256(sorted(
            row["predicate_semantics_sha256"] for row in candidates
        )),
        "candidate_effect_set_sha256": stable_sha256(sorted(
            row["predicate_effect_sha256"] for row in candidates
        )),
        "source_ids": sorted({require_text(value, "candidate source id") for value in source_ids}),
        "candidate_source_family_ids": sorted({
            require_text(value, "candidate source family id")
            for value in runtime.get("candidate_source_family_ids") or ()
        }),
        "candidate_call_receipt_sha256": receipt,
        "candidate_runtime_provenance_sha256": runtime_sha,
        "observed_at": observed, "available_at": available,
        "holdout_examples_observed": False,
        "capital_authority": False,
    }
    return {**body, "candidate_freeze_sha256": stable_sha256(body)}


def _independence_certificate(
    predicates: Iterable[Mapping[str, Any]], provenance: Mapping[str, Any],
    source_ids: set[str], runtime_provenance: Mapping[str, Any] | None,
) -> dict[str, Any]:
    candidates = list(predicates)
    candidate_sources = sorted({
        str(value) for row in candidates for value in row.get("evidence_refs") or ()
    })
    example_sources = sorted({
        require_text(value, "constraint example source id")
        for value in provenance.get("example_source_ids") or ()
    })
    if not set(example_sources) <= source_ids:
        raise ValueError("constraint example provenance crosses the source vocabulary")
    runtime = dict(runtime_provenance or {})
    runtime_sha = runtime.pop("provenance_sha256", "")
    runtime_verified = bool(runtime) and (
        runtime.get("schema") == RUNTIME_PROVENANCE_SCHEMA
        and runtime.get("authority") == "worker_verified_subscription_receipts"
        and runtime_sha == stable_sha256(runtime)
    )
    if runtime and not runtime_verified:
        raise ValueError("constraint runtime provenance is not worker-verifiable")
    candidate_receipt = str(runtime.get("candidate_call_receipt_sha256") or "")
    example_receipt = str(runtime.get("example_call_receipt_sha256") or "")
    receipt_hash = lambda value: len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )
    if runtime_verified and not (
        receipt_hash(candidate_receipt) and receipt_hash(example_receipt)
    ):
        raise ValueError("constraint runtime provenance lacks call receipts")
    candidate_authors = [f"subscription-receipt:{candidate_receipt}"] if runtime_verified else []
    example_authors = [f"subscription-receipt:{example_receipt}"] if runtime_verified else []
    candidate_families = sorted({
        str(value) for value in runtime.get("candidate_source_family_ids") or ()
    }) if runtime_verified else []
    example_families = sorted({
        str(value) for value in runtime.get("example_source_family_ids") or ()
    }) if runtime_verified else []
    expected_semantics_set = stable_sha256(sorted(
        str(row.get("predicate_semantics_sha256") or "") for row in candidates
    ))
    semantics_bound = bool(runtime_verified) and (
        runtime.get("candidate_semantics_set_sha256") == expected_semantics_set
    )
    blind_holdout = bool(runtime_verified and runtime.get("holdout_predicates_hidden") is True)
    source_receipts_verified = bool(
        runtime_verified and runtime.get("example_source_receipts_verified") is True
    )
    frozen_before_holdout = bool(runtime_verified) and timestamp_key(str(
        runtime.get("candidate_frozen_at") or "1970-01-01T00:00:00Z"
    )) < timestamp_key(str(
        runtime.get("holdout_completed_at") or "1970-01-01T00:00:00Z"
    ))
    reasons = []
    source_ref_disjoint = bool(candidate_sources and example_sources) and set(
        candidate_sources
    ).isdisjoint(example_sources)
    information_family_independent = bool(candidate_families and example_families) and set(
        candidate_families
    ).isdisjoint(example_families)
    role_separated = bool(candidate_authors and example_authors) and set(
        candidate_authors
    ).isdisjoint(example_authors)
    if not source_ref_disjoint:
        reasons.append(
            "candidate_example_source_overlap" if candidate_sources and example_sources
            else "source_provenance_absent"
        )
    if not information_family_independent:
        reasons.append(
            "candidate_example_information_family_overlap"
            if candidate_families and example_families
            else "verified_information_family_provenance_absent"
        )
    if not role_separated:
        reasons.append(
            "candidate_example_role_overlap" if runtime_verified
            else "verified_role_provenance_absent"
        )
    if not blind_holdout:
        reasons.append("holdout_visibility_not_verified")
    if not source_receipts_verified:
        reasons.append("example_source_receipts_unverified")
    if not frozen_before_holdout:
        reasons.append("candidate_not_frozen_before_holdout")
    if not semantics_bound:
        reasons.append("candidate_semantics_set_not_bound")
    effect_count = len({str(row.get("predicate_effect_sha256") or "") for row in candidates})
    if effect_count < 2:
        reasons.append("no_behaviorally_competing_predicate")
    body = {
        "schema": INDEPENDENCE_SCHEMA,
        "candidate_source_ids": candidate_sources,
        "example_source_ids": example_sources,
        "candidate_author_ids": candidate_authors,
        "example_author_ids": example_authors,
        "candidate_source_family_ids": candidate_families,
        "example_source_family_ids": example_families,
        "source_independent": information_family_independent,
        "source_ref_disjoint": source_ref_disjoint,
        "author_independent": role_separated,
        "role_separated": role_separated,
        "holdout_predicates_hidden": blind_holdout,
        "example_source_receipts_verified": source_receipts_verified,
        "candidate_frozen_before_holdout": frozen_before_holdout,
        "candidate_semantics_set_bound": semantics_bound,
        "candidate_predicate_count": len(candidates),
        "candidate_effect_count": effect_count,
        "has_competing_predicates": effect_count >= 2,
        "runtime_provenance_sha256": runtime_sha or None,
        "evidence_grade": (
            "candidate_blind_source_disjoint_replay" if not reasons else "diagnostic"
        ),
        "diagnostic_reasons": reasons,
        "capital_authority": False,
    }
    return {**body, "independence_sha256": stable_sha256(body)}


def compile_strategy_constraint_challenge_request(
    parent: Mapping[str, Any], *, examples: Mapping[str, Any],
    candidate_predicates: Iterable[Mapping[str, Any]], source_ids: Iterable[str],
    observed_at: str, available_at: str,
    runtime_provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Freeze a bounded additive-predicate discrimination question."""
    if parent.get("schema") != FRONTIER_RESULT_SCHEMA or not _content_hash(
        parent, "strategy_frontier_sha256",
    ):
        raise ValueError("constraint challenge requires an intact parent frontier")
    parent_sha = str(parent["strategy_frontier_sha256"])
    certificate = parent.get("choice_space_certificate") or {}
    option_ids = set(map(str, certificate.get("option_ids") or ()))
    sources = sorted({require_text(value, "constraint challenge source id") for value in source_ids})
    observed = canonical_timestamp(observed_at, "constraint challenge observed_at")
    available = canonical_timestamp(available_at, "constraint challenge available_at")
    if timestamp_key(available) < timestamp_key(observed):
        raise ValueError("constraint challenge evidence cannot be available before observation")
    normalized_examples = _examples(examples, option_ids)
    admitted_examples = [set(row) for row in normalized_examples["admitted_bundles"]]
    if not admitted_examples:
        raise ValueError("constraint challenge requires an admitted example")
    for implication in normalized_examples["implication_pairs"]:
        positive = set(implication["antecedent_option_ids"]) | set(
            implication["required_option_ids"]
        )
        if not any(positive <= bundle for bundle in admitted_examples):
            raise ValueError("an implication requires a non-vacuous admitted witness")
    grouped = {"incompatibilities": [], "prerequisites": [], "resources": []}
    for raw in candidate_predicates:
        row = dict(raw)
        key = {
            "incompatibility": "incompatibilities",
            "prerequisite": "prerequisites",
            "resource_limit": "resources",
        }.get(str(row.pop("predicate_kind", "")))
        if key is None:
            raise ValueError("unsupported candidate predicate kind")
        grouped[key].append(row)
    predicates = normalize_strategy_constraint_candidates(parent, grouped, sources)
    if not predicates or len(predicates) > MAX_CANDIDATE_PREDICATES:
        raise ValueError("constraint challenge requires 1-12 candidate predicates")
    if len({row["constraint_id"] for row in predicates}) != len(predicates):
        raise ValueError("candidate constraint ids must be unique")
    parent_constraints = parent.get("feasibility_constraints") or {}
    existing_ids = {
        str(row.get("constraint_id"))
        for kind in ("incompatibilities", "prerequisites", "resources")
        for row in parent_constraints.get(kind) or ()
    }
    if existing_ids & {row["constraint_id"] for row in predicates}:
        raise ValueError("candidate predicates must be additive to the parent")
    provenance = examples.get("evidence_provenance")
    if provenance is not None and not isinstance(provenance, Mapping):
        raise ValueError("constraint evidence provenance must be an object")
    independence = _independence_certificate(
        predicates, provenance or {}, set(sources), runtime_provenance,
    )
    feasible = {
        tuple(sorted(map(str, row.get("option_ids") or ())))
        for row in certificate.get("feasible_bundles") or ()
    }
    admitted = {tuple(row) for row in normalized_examples["admitted_bundles"]}
    excluded = {tuple(row) for row in normalized_examples["excluded_bundles"]}
    if not admitted <= feasible:
        raise ValueError("an admitted example is infeasible in the immutable parent")
    if not excluded <= feasible:
        raise ValueError("an excluded example is already excluded by the immutable parent")
    challenge_identity = stable_sha256({
        "examples": normalized_examples,
        "candidate_predicate_sha256s": [row["predicate_sha256"] for row in predicates],
        "available_at": available,
    })
    body = {
        "schema": REQUEST_SCHEMA,
        "request_id": (
            f"strategy-constraint-challenge:{parent_sha[:16]}:{challenge_identity[:16]}"
        ),
        "parent_strategy_frontier_sha256": parent_sha,
        "parent_choice_space_sha256": require_text(
            certificate.get("choice_space_sha256"), "parent choice-space hash",
        ),
        "parent_feasibility_constraints_sha256": require_text(
            parent_constraints.get("feasibility_constraints_sha256"),
            "parent feasibility-constraint hash",
        ),
        "parent_evidence_epoch": canonical_timestamp(
            parent.get("evidence_epoch"), "parent strategy evidence epoch",
        ),
        "option_ids": sorted(option_ids), "constraint_challenge_examples": normalized_examples,
        "candidate_predicates": predicates, "source_ids": sources,
        "independence_certificate": independence,
        "observed_at": observed, "available_at": available,
        "additive_only": True, "capital_authority": False,
    }
    return {**body, "request_sha256": stable_sha256(body)}


def _permits(predicate: Mapping[str, Any], bundle: frozenset[str]) -> bool:
    kind = predicate["predicate_kind"]
    if kind == "incompatibility":
        return not set(predicate["option_ids"]) <= bundle
    if kind == "prerequisite":
        return predicate["option_id"] not in bundle or set(predicate["requires"]) <= bundle
    total = sum(
        float(amount) for option_id, amount in predicate["uses"].items()
        if option_id in bundle
    )
    return total <= float(predicate["limit"])


def strategy_constraint_predicate_permits(
    predicate: Mapping[str, Any], option_ids: Iterable[str],
) -> bool:
    """Evaluate one normalized predicate on a declared option bundle."""
    return _permits(predicate, frozenset(map(str, option_ids)))


def _replay(request: Mapping[str, Any], parent: Mapping[str, Any]) -> dict[str, Any]:
    feasible = {
        frozenset(map(str, row.get("option_ids") or ()))
        for row in (parent.get("choice_space_certificate") or {}).get("feasible_bundles") or ()
    }
    examples = request["constraint_challenge_examples"]
    admitted = {frozenset(row) for row in examples["admitted_bundles"]}
    excluded = {frozenset(row) for row in examples["excluded_bundles"]}
    implications = [
        (frozenset(row["antecedent_option_ids"]), frozenset(row["required_option_ids"]))
        for row in examples["implication_pairs"]
    ]

    def satisfies(predicates: tuple[Mapping[str, Any], ...]) -> bool:
        remaining = {
            bundle for bundle in feasible
            if all(_permits(predicate, bundle) for predicate in predicates)
        }
        return (
            admitted <= remaining and not excluded & remaining
            and all(
                all(not antecedent <= bundle or required <= bundle for bundle in remaining)
                for antecedent, required in implications
            )
        )

    candidates = tuple(request["candidate_predicates"])
    passing: list[tuple[Mapping[str, Any], ...]] = []
    for size in range(1, len(candidates) + 1):
        passing.extend(rows for rows in combinations(candidates, size) if satisfies(rows))
    passing_ids = [
        frozenset(row["predicate_sha256"] for row in candidate_set)
        for candidate_set in passing
    ]
    minimal = [
        candidate_set for candidate_set, candidate_ids in zip(
            passing, passing_ids, strict=True,
        )
        if not any(other < candidate_ids for other in passing_ids)
    ]
    accepted = minimal[0] if len(minimal) == 1 else ()
    body = {
        "status": (
            "accepted" if accepted else "ambiguous" if minimal else "insufficient"
        ),
        "minimal_candidate_set_count": len(minimal),
        "minimal_candidate_set_size": len(accepted) if accepted else None,
        "minimal_candidate_set_sizes": sorted(len(row) for row in minimal),
        "accepted_predicate_sha256s": [row["predicate_sha256"] for row in accepted],
        "candidate_set_sha256s": sorted(stable_sha256([
            row["predicate_sha256"] for row in candidate_set
        ]) for candidate_set in minimal),
    }
    return {**body, "replay_sha256": stable_sha256(body)}


def compile_strategy_constraint_challenge_result(
    raw: Mapping[str, Any], request: Mapping[str, Any], parent: Mapping[str, Any],
) -> dict[str, Any]:
    """Settle a challenge only when deterministic replay selects one minimal set."""
    if request.get("schema") != REQUEST_SCHEMA or not _content_hash(request, "request_sha256"):
        raise ValueError("constraint challenge result requires an intact request")
    parent_constraints = parent.get("feasibility_constraints") or {}
    if (
        parent.get("schema") != FRONTIER_RESULT_SCHEMA
        or not _content_hash(parent, "strategy_frontier_sha256")
        or parent.get("strategy_frontier_sha256")
        != request.get("parent_strategy_frontier_sha256")
        or (parent.get("choice_space_certificate") or {}).get("choice_space_sha256")
        != request.get("parent_choice_space_sha256")
        or parent_constraints.get("feasibility_constraints_sha256")
        != request.get("parent_feasibility_constraints_sha256")
    ):
        raise ValueError("constraint challenge crossed its parent frontier identity")
    if raw.get("schema") != RESULT_SCHEMA or raw.get("request_sha256") != request["request_sha256"]:
        raise ValueError("constraint challenge result crossed its request identity")
    assessed_at = canonical_timestamp(raw.get("assessed_at"), "constraint challenge assessed_at")
    if timestamp_key(assessed_at) < timestamp_key(str(request["available_at"])):
        raise ValueError("constraint challenge was assessed before its evidence was available")
    replay = _replay(request, parent)
    independence = request.get("independence_certificate") or {}
    if (
        independence.get("schema") != INDEPENDENCE_SCHEMA
        or not _content_hash(independence, "independence_sha256")
    ):
        raise ValueError("constraint challenge lacks an intact independence certificate")
    selected = sorted({
        require_text(value, "selected candidate predicate hash")
        for value in raw.get("selected_predicate_sha256s") or ()
    })
    if selected != sorted(replay["accepted_predicate_sha256s"]):
        raise ValueError("constraint challenge selection differs from deterministic replay")
    body = {
        "schema": RESULT_SCHEMA, "request_sha256": request["request_sha256"],
        "parent_strategy_frontier_sha256": request["parent_strategy_frontier_sha256"],
        "assessed_at": assessed_at, "status": replay["status"], "replay": replay,
        "selected_predicate_sha256s": selected,
        "accepted_predicates": [
            row for row in request["candidate_predicates"]
            if row["predicate_sha256"] in set(selected)
        ],
        "successor_eligible": replay["status"] == "accepted",
        "evidence_grade": independence["evidence_grade"],
        "research_claim_eligible": (
            replay["status"] == "accepted"
            and independence["evidence_grade"]
            == "candidate_blind_source_disjoint_replay"
        ),
        "capital_authority": False,
    }
    return {**body, "result_sha256": stable_sha256(body)}


def settle_strategy_constraint_challenge(
    request: Mapping[str, Any], parent: Mapping[str, Any], *, assessed_at: str,
) -> dict[str, Any]:
    """Settle the deterministic replay without asking an agent to select predicates."""
    replay = _replay(request, parent)
    return compile_strategy_constraint_challenge_result({
        "schema": RESULT_SCHEMA,
        "request_sha256": request["request_sha256"],
        "assessed_at": assessed_at,
        "selected_predicate_sha256s": replay["accepted_predicate_sha256s"],
    }, request, parent)


def compile_strategy_constraint_frontier_gate(
    parent: Mapping[str, Any], *, candidate_constraints: Mapping[str, Any],
    examples: Mapping[str, Any], source_ids: Iterable[str],
    observed_at: str, available_at: str,
    runtime_provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Admit only uniquely discriminated additive constraints to a successor request."""
    parent_constraints = parent.get("feasibility_constraints") or {}

    def clean(row: Mapping[str, Any]) -> dict[str, Any]:
        return {
            key: value for key, value in row.items()
            if key not in {"authority", "predicate_kind", "predicate_sha256"}
        }

    keys = ("incompatibilities", "prerequisites", "resources")
    retained = {
        key: [clean(row) for row in parent_constraints.get(key) or ()]
        for key in keys
    }
    parent_by_id = {
        str(row["constraint_id"]): (key, row)
        for key in keys for row in retained[key]
    }
    additive = []
    identity_conflicts = []
    for key, predicate_kind in zip(
        keys, ("incompatibility", "prerequisite", "resource_limit"), strict=True,
    ):
        for raw in candidate_constraints.get(key) or ():
            row = clean(raw)
            constraint_id = require_text(row.get("constraint_id"), "candidate constraint id")
            prior = parent_by_id.get(constraint_id)
            if prior:
                if prior != (key, row):
                    identity_conflicts.append(constraint_id)
                continue
            additive.append({"predicate_kind": predicate_kind, **row})

    candidate_freeze = challenge_request = challenge_result = None
    candidate_error = None
    status = "identity_conflict" if identity_conflicts else "unchanged"
    has_examples = bool(
        examples.get("excluded_bundles") or examples.get("implication_pairs")
    )
    if identity_conflicts:
        additive = []
    elif additive:
        grouped_additive = {"incompatibilities": [], "prerequisites": [], "resources": []}
        for predicate in additive:
            key = {
                "incompatibility": "incompatibilities",
                "prerequisite": "prerequisites",
                "resource_limit": "resources",
            }[str(predicate["predicate_kind"])]
            grouped_additive[key].append({
                field: value for field, value in predicate.items()
                if field != "predicate_kind"
            })
        if runtime_provenance:
            try:
                candidate_freeze = compile_strategy_constraint_candidate_freeze(
                    parent, candidate_constraints=grouped_additive,
                    source_ids=source_ids, observed_at=observed_at,
                    available_at=available_at, runtime_provenance=runtime_provenance,
                )
            except ValueError as error:
                candidate_error = str(error)
                status = "invalid_candidates"
                additive = []
    if additive and not has_examples:
        status = "missing_examples"
    elif additive:
        challenge_request = compile_strategy_constraint_challenge_request(
            parent, examples=examples, candidate_predicates=additive,
            source_ids=source_ids, observed_at=observed_at, available_at=available_at,
            runtime_provenance=runtime_provenance,
        )
        challenge_result = settle_strategy_constraint_challenge(
            challenge_request, parent, assessed_at=available_at,
        )
        status = str(challenge_result["status"])
        if challenge_result["successor_eligible"]:
            selected = set(challenge_result["selected_predicate_sha256s"])
            for predicate in challenge_request["candidate_predicates"]:
                if predicate["predicate_sha256"] not in selected:
                    continue
                key = {
                    "incompatibility": "incompatibilities",
                    "prerequisite": "prerequisites",
                    "resource_limit": "resources",
                }[str(predicate["predicate_kind"])]
                retained[key].append(clean(predicate))
    accepted_constraints = {
        key: sorted(retained[key], key=lambda row: str(row["constraint_id"]))
        for key in keys
    }
    body = {
        "schema": GATE_SCHEMA,
        "parent_strategy_frontier_sha256": parent.get("strategy_frontier_sha256"),
        "status": status,
        "identity_conflict_ids": sorted(identity_conflicts),
        "candidate_constraint_count": len(additive),
        "candidate_error": candidate_error,
        "accepted_constraint_count": sum(len(rows) for rows in accepted_constraints.values()),
        "accepted_constraints": accepted_constraints,
        "candidate_freeze": candidate_freeze,
        "challenge_request": challenge_request,
        "challenge_result": challenge_result,
        "independence_certificate": (
            (challenge_request or {}).get("independence_certificate")
        ),
        "evidence_grade": (
            (challenge_result or {}).get("evidence_grade", "not_applicable")
        ),
        "research_claim_eligible": bool(
            (challenge_result or {}).get("research_claim_eligible")
        ),
        "additive_only": True,
        "capital_authority": False,
    }
    return {**body, "gate_sha256": stable_sha256(body)}


def compile_strategy_constraint_successor(
    parent_profile: Mapping[str, Any], parent: Mapping[str, Any],
    request: Mapping[str, Any], result: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Add the replay-selected predicates and invoke the existing frontier compiler."""
    verified = compile_strategy_constraint_challenge_result(result, request, parent)
    if result.get("result_sha256") != verified["result_sha256"]:
        raise ValueError("constraint challenge result content hash mismatch")
    if not verified["successor_eligible"]:
        raise ValueError("ambiguous or insufficient challenge cannot create a successor")
    compiled_parent = compile_company_strategy_frontier(parent_profile)
    if compiled_parent.get("strategy_frontier_sha256") != parent.get("strategy_frontier_sha256"):
        raise ValueError("constraint successor profile differs from its parent frontier")
    profile = deepcopy(dict(parent_profile))
    constraints = profile.setdefault("feasibility_constraints", {
        "incompatibilities": [], "prerequisites": [], "resources": [],
    })
    for key in ("incompatibilities", "prerequisites", "resources"):
        constraints.setdefault(key, [])
    for predicate in verified["accepted_predicates"]:
        row = {
            key: value for key, value in predicate.items()
            if key not in {"predicate_kind", "predicate_sha256"}
        }
        key = {
            "incompatibility": "incompatibilities",
            "prerequisite": "prerequisites",
            "resource_limit": "resources",
        }[predicate["predicate_kind"]]
        constraints[key].append(row)
    profile["evidence_epoch"] = max(
        str(parent["evidence_epoch"]), str(request["available_at"]), key=timestamp_key,
    )
    company = dict(profile.get("company") or {})
    company.update({
        "parent_strategy_frontier_sha256": parent["strategy_frontier_sha256"],
        "strategy_constraint_challenge_request_sha256": request["request_sha256"],
        "strategy_constraint_challenge_result_sha256": result["result_sha256"],
        "strategy_constraint_independence_sha256": request[
            "independence_certificate"
        ]["independence_sha256"],
        "strategy_constraint_evidence_grade": verified["evidence_grade"],
        "strategy_constraint_research_claim_eligible": verified[
            "research_claim_eligible"
        ],
    })
    profile["company"] = company
    frontier = compile_company_strategy_frontier(profile)
    return profile, frontier


__all__ = [
    "CANDIDATE_FREEZE_SCHEMA", "GATE_SCHEMA", "INDEPENDENCE_SCHEMA",
    "RUNTIME_PROVENANCE_SCHEMA",
    "REQUEST_SCHEMA", "RESULT_SCHEMA",
    "compile_strategy_constraint_challenge_request",
    "compile_strategy_constraint_challenge_result",
    "compile_strategy_constraint_candidate_freeze",
    "compile_strategy_constraint_frontier_gate",
    "compile_strategy_constraint_successor", "settle_strategy_constraint_challenge",
    "normalize_strategy_constraint_candidates",
    "strategy_constraint_predicate_permits",
]
