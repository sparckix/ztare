"""Compiled, revocable memory over accepted investment research."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import timedelta
from functools import lru_cache
from itertools import permutations
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_text, timestamp_key
from .golden_store import (
    GoldenEdge,
    GoldenLeaf,
    GoldenStore,
    research_evidence_admissibility,
    research_evidence_is_admissible,
)


RESEARCH_COVERAGE_SCHEMA = "jaggedthoughts-research-evidence-coverage-v1"
STRATEGY_PHENOTYPE_SCHEMA = "jaggedthoughts-strategy-choice-system-phenotype-v1"
_ACCEPTED_REASSESSMENTS = {"strengthened", "weakened", "unchanged"}
_COVERAGE_ENGINE_VERSION = "2026-08-13.dormant-monitor-v2"
_COVERAGE_ENGINE_AVAILABLE_AT = "2026-08-13T13:27:57Z"


def _coverage_available_at(*values: str) -> str:
    return max(
        (_COVERAGE_ENGINE_AVAILABLE_AT, *values), key=timestamp_key,
    )


@lru_cache(maxsize=2_048)
def _canonical_directed_adjacency(
    node_count: int, edges: tuple[tuple[int, int], ...],
) -> str:
    """Exact legacy-compatible graph identity, memoized by graph shape."""
    edge_set = set(edges)
    return min((
        "".join(
            "1" if (order[left], order[right]) in edge_set else "0"
            for left in range(node_count) for right in range(node_count)
        )
        for order in permutations(range(node_count))
    ), default="")


def strategy_choice_system_phenotype(dossier: Mapping[str, Any]) -> dict[str, Any]:
    """Canonicalize a bounded choice graph up to node renaming.

    The identity is topological only. Matching identities create a transfer
    question; they do not establish shared economics or a causal law.
    """
    strategy = dossier.get("strategy") if isinstance(dossier.get("strategy"), Mapping) else {}
    choices = [row for row in strategy.get("choices") or () if isinstance(row, Mapping)]
    choice_ids = [str(row.get("id") or "") for row in choices]
    index = {choice_id: position for position, choice_id in enumerate(choice_ids) if choice_id}
    raw_edges = [row for row in strategy.get("reinforcing_edges") or () if isinstance(row, Mapping)]
    edges = sorted({
        (index[str(row.get("from") or "")], index[str(row.get("to") or "")])
        for row in raw_edges
        if str(row.get("from") or "") in index and str(row.get("to") or "") in index
    })
    unresolved = len(raw_edges) - len(edges)
    node_count = len(choice_ids)
    if node_count <= 8:
        canonical_adjacency = _canonical_directed_adjacency(
            node_count, tuple(edges),
        )
        identity_method = "exact_directed_graph_canonicalization"
    else:
        indegree = [sum(target == node for _, target in edges) for node in range(node_count)]
        outdegree = [sum(source == node for source, _ in edges) for node in range(node_count)]
        canonical_adjacency = repr(sorted(zip(indegree, outdegree, strict=True)))
        identity_method = "degree_signature_fallback"
    signature = {
        "node_count": node_count,
        "edge_count": len(edges),
        "canonical_adjacency": canonical_adjacency,
        "identity_method": identity_method,
    }
    signature_sha = stable_sha256(signature)
    body = {
        "schema": STRATEGY_PHENOTYPE_SCHEMA,
        "phenotype_id": f"strategy-topology:{signature_sha[:16]}",
        "entity_id": dossier.get("entity_id"),
        "candidate_leaf": dossier.get("candidate_leaf"),
        "dossier_sha256": dossier.get("dossier_sha256"),
        "signature": signature,
        "resolved_edge_count": len(edges),
        "unresolved_edge_count": unresolved,
        "transfer_role": "cross_entity_challenger_only",
        "boundary": (
            "A shared phenotype means the directed choice graphs are structurally compatible; "
            "mechanism meaning, earnings consequences, and return effects remain unsettled."
        ),
    }
    return {**body, "phenotype_sha256": stable_sha256(body)}


def _payload_rows(
    store: GoldenStore, *, owner: str, object_kind: str,
) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    rows = []
    for metadata in store.list_leaves(owner=owner, object_kind=object_kind, limit=10_000):
        leaf_sha = str(metadata["leaf_sha256"])
        leaf = store.get_leaf(leaf_sha)
        payload = leaf.get("payload")
        if isinstance(payload, Mapping):
            rows.append((leaf_sha, dict(payload), leaf))
    return rows


def _latest_row(
    rows: Iterable[tuple[str, dict[str, Any], dict[str, Any]]],
) -> tuple[str, dict[str, Any], dict[str, Any]] | None:
    values = list(rows)
    return max(
        values,
        key=lambda row: (
            timestamp_key(str(row[2]["available_at"])), row[0],
        ),
        default=None,
    )


def compile_research_coverage_index(store: GoldenStore, *, owner: str) -> dict[str, Any]:
    """Materialize the three reusable evidence-coverage indexes in one store pass each."""
    subscriptions_by_entity: dict[str, list[tuple[str, dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for row in _payload_rows(store, owner=owner, object_kind="research_monitor_subscription"):
        subscriptions_by_entity[str(row[1].get("entity_id") or "")].append(row)
    reopens_by_subscription: dict[str, list[tuple[str, dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for row in _payload_rows(store, owner=owner, object_kind="research_reopen_request"):
        reopens_by_subscription[str(row[1].get("subscription_leaf") or "")].append(row)
    reassessments_by_request = {
        str(payload.get("request_sha256") or ""): (leaf_sha, payload, leaf)
        for leaf_sha, payload, leaf in _payload_rows(
            store, owner=owner, object_kind="research_reassessment",
        )
    }
    return {
        "subscriptions_by_entity": subscriptions_by_entity,
        "reopens_by_subscription": reopens_by_subscription,
        "reassessments_by_request": reassessments_by_request,
    }


def _quarantined_coverage(
    *, candidate_sha: str, candidate: Mapping[str, Any],
    candidate_payload: Mapping[str, Any], entity_id: str, dossier_leaf: str,
    quarantine: Mapping[str, Any], required: Iterable[str], max_age_days: int,
    subscription_leaf: str | None = None,
) -> dict[str, Any]:
    body = {
        "schema": RESEARCH_COVERAGE_SCHEMA,
        "engine_version": _COVERAGE_ENGINE_VERSION,
        "status": "research_evidence_quarantined",
        "covered": False,
        "entity_id": entity_id,
        "candidate_leaf": candidate_sha,
        "candidate_sha256": candidate_payload.get("candidate_sha256"),
        "prior_dossier_leaf": dossier_leaf,
        "evidence_quarantine_leaf": quarantine["leaf_sha256"],
        "subscription_leaf": subscription_leaf,
        "accepted_reassessment_leaves": [],
        "source_checks": [],
        "missing_required_source_ids": sorted(set(required)),
        "max_age_days": max_age_days,
        "expires_at": None,
        "deep_research_activation": "request",
        "available_at": _coverage_available_at(
            str(candidate["available_at"]), str(quarantine["available_at"]),
        ),
        "scope": "qualitative_strategy_industry_and_durable_earnings_only",
        "excluded_scope": [
            "current_candidate_metrics", "valuation", "rank", "factor_estimates",
            "portfolio_or_capital_action",
        ],
        "capital_authority": False,
    }
    return {**body, "coverage_sha256": stable_sha256(body)}


def _new_coverage_epoch(
    store: GoldenStore, *, owner: str, candidate_leaf: str,
    coverage: Mapping[str, Any],
) -> dict[str, Any]:
    """Keep a changed coverage head strictly after its predecessor."""
    body = dict(coverage)
    try:
        prior = store.head(owner, "research_evidence_coverage", f"research-coverage:{candidate_leaf}")
    except KeyError:
        return body
    prior_payload = dict(prior.get("payload") or {})
    semantic = lambda value: {
        key: item for key, item in value.items()
        if key not in {"coverage_sha256", "available_at"}
    }
    if semantic(prior_payload) == semantic(body):
        return prior_payload
    if timestamp_key(str(body["available_at"])) <= timestamp_key(str(prior["available_at"])):
        body["available_at"] = (
            timestamp_key(str(prior["available_at"])) + timedelta(seconds=1)
        ).isoformat(timespec="seconds").replace("+00:00", "Z")
        unsigned = {key: value for key, value in body.items() if key != "coverage_sha256"}
        body["coverage_sha256"] = stable_sha256(unsigned)
    return body


def candidate_research_coverage(
    store: GoldenStore, *, owner: str, candidate_leaf: str,
    current_receipts: Mapping[str, Mapping[str, Any]],
    required_source_ids: Iterable[str] = (),
    max_age_days: int = 45,
    coverage_index: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Decide whether monitored qualitative evidence covers one candidate epoch."""
    candidate_sha = require_text(candidate_leaf, "research coverage candidate leaf")
    candidate = store.get_leaf(candidate_sha)
    if candidate.get("owner") != owner or candidate.get("object_kind") != "discovery_candidate":
        raise ValueError("research coverage must target an owned discovery candidate")
    candidate_payload = candidate.get("payload") or {}
    entity_id = require_text(candidate_payload.get("entity_id"), "research coverage entity_id")
    try:
        exact_dossier = store.head(
            owner, "candidate_research_dossier", f"research:{entity_id}:{candidate_sha}",
        )
    except KeyError:
        exact_dossier = None
    quarantined_exact: tuple[str, dict[str, Any]] | None = None
    if exact_dossier is not None:
        dossier_leaf = str(exact_dossier["leaf_sha256"])
        admission = research_evidence_admissibility(
            store, owner=owner, target_leaf=dossier_leaf,
        )
        if not admission["admissible"]:
            quarantined_exact = (dossier_leaf, admission["quarantine"])
            exact_dossier = None
    if exact_dossier is not None:
        dossier_leaf = str(exact_dossier["leaf_sha256"])
        body = {
            "schema": RESEARCH_COVERAGE_SCHEMA,
            "engine_version": _COVERAGE_ENGINE_VERSION,
            "status": "covered_by_exact_dossier", "covered": True,
            "entity_id": entity_id, "candidate_leaf": candidate_sha,
            "candidate_sha256": candidate_payload.get("candidate_sha256"),
            "prior_dossier_leaf": dossier_leaf, "subscription_leaf": None,
            "evidence_quarantine_leaf": None,
            "accepted_reassessment_leaves": [], "source_checks": [],
            "missing_required_source_ids": [], "max_age_days": max_age_days,
            "expires_at": None, "deep_research_activation": "reuse",
            "available_at": _coverage_available_at(str(exact_dossier["available_at"])),
            "scope": "qualitative_strategy_industry_and_durable_earnings_only",
            "excluded_scope": [
                "current_candidate_metrics", "valuation", "rank", "factor_estimates",
                "portfolio_or_capital_action",
            ],
            "capital_authority": False,
        }
        return {**body, "coverage_sha256": stable_sha256(body)}
    index = coverage_index or compile_research_coverage_index(store, owner=owner)
    subscriptions = list(
        (index.get("subscriptions_by_entity") or {}).get(entity_id, ())
    )
    subscription_row = _latest_row(subscriptions)
    required = sorted({str(value) for value in required_source_ids if str(value)})
    if subscription_row is None:
        if quarantined_exact is not None:
            return _new_coverage_epoch(store, owner=owner, candidate_leaf=candidate_sha, coverage=_quarantined_coverage(
                candidate_sha=candidate_sha, candidate=candidate,
                candidate_payload=candidate_payload, entity_id=entity_id,
                dossier_leaf=quarantined_exact[0], quarantine=quarantined_exact[1],
                required=required, max_age_days=max_age_days,
            ))
        body = {
            "schema": RESEARCH_COVERAGE_SCHEMA,
            "engine_version": _COVERAGE_ENGINE_VERSION,
            "status": "no_prior_monitored_dossier",
            "covered": False,
            "entity_id": entity_id,
            "candidate_leaf": candidate_sha,
            "candidate_sha256": candidate_payload.get("candidate_sha256"),
            "prior_dossier_leaf": None,
            "evidence_quarantine_leaf": None,
            "subscription_leaf": None,
            "accepted_reassessment_leaves": [],
            "source_checks": [],
            "missing_required_source_ids": required,
            "max_age_days": max_age_days,
            "expires_at": None,
            "deep_research_activation": "request",
            "available_at": _coverage_available_at(str(candidate["available_at"])),
            "scope": "qualitative_strategy_industry_and_durable_earnings_only",
            "capital_authority": False,
        }
        return {**body, "coverage_sha256": stable_sha256(body)}

    subscription_leaf, subscription, subscription_record = subscription_row
    prior_dossier_leaf = require_text(
        subscription.get("dossier_leaf"), "coverage prior dossier leaf",
    )
    prior_dossier_record = store.get_leaf(prior_dossier_leaf)
    admission = research_evidence_admissibility(
        store, owner=owner, target_leaf=prior_dossier_leaf,
    )
    if not admission["admissible"]:
        return _new_coverage_epoch(store, owner=owner, candidate_leaf=candidate_sha, coverage=_quarantined_coverage(
            candidate_sha=candidate_sha, candidate=candidate,
            candidate_payload=candidate_payload, entity_id=entity_id,
            dossier_leaf=prior_dossier_leaf, quarantine=admission["quarantine"],
            required=required, max_age_days=max_age_days,
            subscription_leaf=subscription_leaf,
        ))
    expires_at = (
        timestamp_key(str(prior_dossier_record["available_at"]))
        + timedelta(days=max_age_days)
    ).isoformat().replace("+00:00", "Z")
    expired = timestamp_key(str(candidate["available_at"])) > timestamp_key(expires_at)
    trigger_by_id = {
        str(row.get("source_id") or ""): dict(row)
        for row in subscription.get("trigger_sources") or () if isinstance(row, Mapping)
    }
    missing_required = sorted(set(required) - set(trigger_by_id))
    reopens = list(
        (index.get("reopens_by_subscription") or {}).get(subscription_leaf, ())
    )
    reassessment_by_request = index.get("reassessments_by_request") or {}
    accepted_reassessments: set[str] = set()
    checks: list[dict[str, Any]] = []
    epochs = [
        str(candidate["available_at"]), str(subscription_record["available_at"]),
    ]
    for source_id, trigger in sorted(trigger_by_id.items()):
        current = dict(current_receipts.get(source_id) or {})
        baseline_digest = str(trigger.get("baseline_content_sha256") or "")
        current_digest = str(current.get("content_sha256") or baseline_digest)
        current_at = str(current.get("retrieved_at") or trigger.get("baseline_retrieved_at") or "")
        if current_at:
            epochs.append(current_at)
        if not baseline_digest and not current_digest:
            checks.append({
                "source_id": source_id, "status": "dormant_until_first_receipt",
                "covered": True, "content_sha256": None,
                "receipt_sha256": None, "reassessment_leaf": None,
            })
            continue
        if baseline_digest and current_digest == baseline_digest:
            checks.append({
                "source_id": source_id, "status": "baseline_current",
                "covered": True, "content_sha256": current_digest,
                "receipt_sha256": current.get("receipt_sha256") or trigger.get("baseline_receipt_sha256"),
                "reassessment_leaf": None,
            })
            continue
        matching: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
        for _, reopen, _ in reopens:
            event_leaf = str(reopen.get("source_change_event_leaf") or "")
            if not event_leaf:
                continue
            event = store.get_leaf(event_leaf).get("payload") or {}
            if (
                str(event.get("source_id") or "") != source_id
                or str(event.get("current_content_sha256") or "") != current_digest
            ):
                continue
            reassessment = reassessment_by_request.get(str(reopen.get("request_sha256") or ""))
            if reassessment:
                matching.append(reassessment)
        latest = _latest_row(matching)
        if latest is None:
            status = "baseline_unobserved" if not baseline_digest else "reassessment_pending"
            checks.append({
                "source_id": source_id, "status": status, "covered": False,
                "content_sha256": current_digest or None,
                "receipt_sha256": current.get("receipt_sha256"),
                "reassessment_leaf": None,
            })
            continue
        reassessment_leaf, reassessment, reassessment_record = latest
        epochs.append(str(reassessment_record["available_at"]))
        accepted = (
            reassessment.get("thesis_status") in _ACCEPTED_REASSESSMENTS
            and reassessment.get("next_activation") == "monitor"
        )
        if accepted:
            accepted_reassessments.add(reassessment_leaf)
        checks.append({
            "source_id": source_id,
            "status": (
                "accepted_reassessment" if accepted else
                "source_gap" if reassessment.get("next_activation") == "source_gap" else
                "re_underwrite"
            ),
            "covered": accepted,
            "content_sha256": current_digest or None,
            "receipt_sha256": current.get("receipt_sha256"),
            "reassessment_leaf": reassessment_leaf,
            "thesis_status": reassessment.get("thesis_status"),
        })
    covered = (
        not expired and bool(checks) and not missing_required
        and all(row["covered"] for row in checks)
    )
    status = (
        "covered_by_monitored_dossier" if covered else
        "coverage_expired" if expired else
        "unmonitored_material_source" if missing_required else
        "reassessment_required"
    )
    deep_research_activation = (
        "reuse" if covered else
        "request" if expired or missing_required or any(
            row["status"] in {"baseline_unobserved", "re_underwrite", "source_gap"}
            for row in checks
        ) else
        "await_reassessment"
    )
    available_at = _coverage_available_at(*(
        canonical_timestamp(value, "research coverage epoch")
        for value in epochs if value
    ))
    body = {
        "schema": RESEARCH_COVERAGE_SCHEMA,
        "engine_version": _COVERAGE_ENGINE_VERSION,
        "status": status,
        "covered": covered,
        "entity_id": entity_id,
        "candidate_leaf": candidate_sha,
        "candidate_sha256": candidate_payload.get("candidate_sha256"),
        "prior_dossier_leaf": prior_dossier_leaf,
        "evidence_quarantine_leaf": None,
        "subscription_leaf": subscription_leaf,
        "accepted_reassessment_leaves": sorted(accepted_reassessments),
        "source_checks": checks,
        "missing_required_source_ids": missing_required,
        "max_age_days": max_age_days,
        "expires_at": expires_at,
        "deep_research_activation": deep_research_activation,
        "available_at": available_at,
        "scope": "qualitative_strategy_industry_and_durable_earnings_only",
        "excluded_scope": [
            "current_candidate_metrics", "valuation", "rank", "factor_estimates",
            "portfolio_or_capital_action",
        ],
        "capital_authority": False,
    }
    return {**body, "coverage_sha256": stable_sha256(body)}


def record_candidate_research_coverage(
    store: GoldenStore, *, owner: str, coverage: Mapping[str, Any],
) -> str:
    """Record a candidate-bound bridge without mutating either evidence epoch."""
    if coverage.get("schema") != RESEARCH_COVERAGE_SCHEMA:
        raise ValueError("unsupported research coverage schema")
    declared = require_text(coverage.get("coverage_sha256"), "research coverage hash")
    body = {key: value for key, value in coverage.items() if key != "coverage_sha256"}
    if stable_sha256(body) != declared:
        raise ValueError("research coverage content hash mismatch")
    candidate_leaf = require_text(coverage.get("candidate_leaf"), "coverage candidate leaf")
    dependencies = [candidate_leaf]
    source_refs = [f"candidate:{candidate_leaf}"]
    for field in ("prior_dossier_leaf", "evidence_quarantine_leaf", "subscription_leaf"):
        value = str(coverage.get(field) or "")
        if value:
            dependencies.append(value)
            source_refs.append(f"{field}:{value}")
    dependencies.extend(
        str(value) for value in coverage.get("accepted_reassessment_leaves") or ()
    )
    leaf = GoldenLeaf(
        owner=owner,
        object_kind="research_evidence_coverage",
        object_id=f"research-coverage:{candidate_leaf}",
        epoch=declared,
        occurred_at=str(coverage["available_at"]),
        available_at=str(coverage["available_at"]),
        payload=dict(coverage),
        source_refs=tuple(source_refs),
    )
    store.append_bundle(
        (leaf,), tuple(GoldenEdge(leaf.leaf_sha256, value, "based_on") for value in dependencies),
    )
    return leaf.leaf_sha256


def candidate_strategy_phenotype(
    store: GoldenStore, *, owner: str, candidate_leaf: str, as_of: str | None = None,
) -> tuple[dict[str, Any] | None, tuple[str, ...]]:
    """Resolve an exact or covered dossier to the candidate's strategy phenotype."""
    cutoff = canonical_timestamp(as_of, "strategy phenotype as_of") if as_of else None
    dossier_rows = (
        [
            (str(row["leaf_sha256"]), dict(row.get("payload") or {}), row)
            for row in store.heads_as_of(owner, "candidate_research_dossier", cutoff)
            if isinstance(row.get("payload"), Mapping)
        ]
        if cutoff else _payload_rows(
            store, owner=owner, object_kind="candidate_research_dossier",
        )
    )
    dossier_row = _latest_row(
        row for row in dossier_rows
        if (
            str(row[1].get("candidate_leaf") or "") == candidate_leaf
            and research_evidence_is_admissible(
                store, owner=owner, target_leaf=row[0], as_of=cutoff,
            )
        )
    )
    refs: list[str] = []
    if dossier_row is None:
        object_id = f"research-coverage:{candidate_leaf}"
        if cutoff:
            bridge_rows = store.heads_as_of(
                owner, "research_evidence_coverage", cutoff, object_ids=(object_id,),
            )
            if not bridge_rows:
                return None, ()
            bridge = bridge_rows[0]
        else:
            try:
                bridge = store.head(owner, "research_evidence_coverage", object_id)
            except KeyError:
                return None, ()
        payload = bridge.get("payload") or {}
        if not payload.get("covered"):
            return None, ()
        dossier_leaf = str(payload.get("prior_dossier_leaf") or "")
        admission = research_evidence_admissibility(
            store, owner=owner, target_leaf=dossier_leaf, as_of=cutoff,
        )
        if not admission["admissible"]:
            return None, (
                str(bridge["leaf_sha256"]), dossier_leaf,
                str(admission["quarantine_leaf"]),
            )
        dossier_record = store.get_leaf(dossier_leaf)
        dossier_payload = dossier_record.get("payload")
        if not isinstance(dossier_payload, Mapping):
            return None, ()
        refs.extend((str(bridge["leaf_sha256"]), dossier_leaf))
        return strategy_choice_system_phenotype(dossier_payload), tuple(refs)
    dossier_leaf, dossier_payload, _ = dossier_row
    return strategy_choice_system_phenotype(dossier_payload), (dossier_leaf,)


def compile_research_memory(store: GoldenStore) -> dict[str, Any]:
    """Expose exact evidence reuse, coverage bridges, and strategy phenotypes."""
    source_meta = store.list_leaves(object_kind="research_source_evidence", limit=10_000)
    claim_meta = store.list_leaves(object_kind="strategy_mechanism_claim", limit=10_000)
    dossier_meta = store.list_leaves(object_kind="candidate_research_dossier", limit=10_000)
    coverage_meta = store.list_leaves(object_kind="research_evidence_coverage", limit=10_000)
    subscription_meta = store.list_leaves(object_kind="research_monitor_subscription", limit=10_000)
    source_event_meta = store.list_leaves(object_kind="public_source_change_event", limit=10_000)
    reopen_meta = store.list_leaves(object_kind="research_reopen_request", limit=10_000)
    reassessment_meta = store.list_leaves(object_kind="research_reassessment", limit=10_000)
    model_result_meta = store.list_leaves(
        object_kind="mechanism_research_result", limit=10_000,
    )
    citations = store.list_edges(relation="cites", limit=100_000)
    support_edges = store.list_edges(relation="supported_by", limit=100_000)
    source_records = store.get_leaves(
        str(row["leaf_sha256"]) for row in source_meta
    )
    dossier_records = store.get_leaves(
        str(row["leaf_sha256"]) for row in dossier_meta
    )
    coverage_records = store.get_leaves(
        str(row["leaf_sha256"]) for row in coverage_meta
    )
    model_result_records = store.get_leaves(
        str(row["leaf_sha256"]) for row in model_result_meta
    )
    dossier_by_source: dict[str, set[str]] = defaultdict(set)
    claims_by_source: dict[str, set[str]] = defaultdict(set)
    for edge in citations:
        dossier_by_source[str(edge["dst_leaf_sha256"])].add(str(edge["src_leaf_sha256"]))
    for edge in support_edges:
        claims_by_source[str(edge["dst_leaf_sha256"])].add(str(edge["src_leaf_sha256"]))

    rows: list[dict[str, Any]] = []
    for metadata in source_meta:
        leaf_sha = str(metadata["leaf_sha256"])
        payload = source_records[leaf_sha].get("payload") or {}
        dossiers = sorted(dossier_by_source.get(leaf_sha, set()))
        claims = sorted(claims_by_source.get(leaf_sha, set()))
        rows.append({
            "source_leaf": leaf_sha,
            "document_id": payload.get("document_id"),
            "title": payload.get("title"), "url": payload.get("url"),
            "publisher": payload.get("publisher"),
            "published_at": payload.get("published_at"),
            "source_kind": payload.get("source_kind"),
            "dossier_count": len(dossiers),
            "mechanism_claim_count": len(claims),
            "affected_dossier_leaves": dossiers,
            "affected_mechanism_claim_leaves": claims,
            "reused": len(dossiers) > 1,
        })
    rows.sort(key=lambda row: (
        -int(row["dossier_count"]), -int(row["mechanism_claim_count"]),
        str(row.get("title") or ""),
    ))

    phenotypes: dict[str, dict[str, Any]] = {}
    for metadata in dossier_meta:
        dossier_leaf = str(metadata["leaf_sha256"])
        if not research_evidence_is_admissible(
            store, owner=str(metadata["owner"]), target_leaf=dossier_leaf,
        ):
            continue
        dossier = dossier_records[dossier_leaf].get("payload") or {}
        phenotype = strategy_choice_system_phenotype(dossier)
        cohort = phenotypes.setdefault(phenotype["phenotype_id"], {
            "phenotype_id": phenotype["phenotype_id"],
            "signature": phenotype["signature"],
            "entity_ids": set(), "dossier_leaves": [],
            "unresolved_edge_count": 0,
        })
        cohort["entity_ids"].add(str(dossier.get("entity_id") or ""))
        cohort["dossier_leaves"].append(dossier_leaf)
        cohort["unresolved_edge_count"] += int(phenotype["unresolved_edge_count"])
    phenotype_rows = [
        {
            **row,
            "entity_ids": sorted(row["entity_ids"] - {""}),
            "dossier_leaves": sorted(row["dossier_leaves"]),
            "cross_entity": len(row["entity_ids"] - {""}) > 1,
            "next_question": (
                "Test whether the matching choice topology carries the same earnings mechanism "
                "across these entities or is only a structural resemblance."
            ),
        }
        for row in phenotypes.values()
    ]
    phenotype_rows.sort(key=lambda row: (-len(row["entity_ids"]), row["phenotype_id"]))
    coverage_heads: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {}
    for metadata in coverage_meta:
        leaf_sha = str(metadata["leaf_sha256"])
        payload = coverage_records[leaf_sha].get("payload") or {}
        candidate_leaf = str(payload.get("candidate_leaf") or "")
        prior = coverage_heads.get(candidate_leaf)
        if prior is not None and (
            str(metadata["available_at"]), leaf_sha
        ) <= (str(prior[0]["available_at"]), str(prior[0]["leaf_sha256"])):
            continue
        coverage_heads[candidate_leaf] = (metadata, payload)
    coverage_rows = []
    for metadata, payload in coverage_heads.values():
        leaf_sha = str(metadata["leaf_sha256"])
        coverage_rows.append({
            "coverage_leaf": leaf_sha,
            "entity_id": payload.get("entity_id"),
            "candidate_leaf": payload.get("candidate_leaf"),
            "prior_dossier_leaf": payload.get("prior_dossier_leaf"),
            "accepted_reassessment_count": len(payload.get("accepted_reassessment_leaves") or ()),
            "status": payload.get("status"),
            "covered": bool(payload.get("covered")),
            "scope": payload.get("scope"),
            "expires_at": payload.get("expires_at"),
        })
    model_results = []
    family_rows: dict[str, dict[str, Any]] = {}
    for metadata in model_result_meta:
        leaf_sha = str(metadata["leaf_sha256"])
        payload = model_result_records[leaf_sha].get("payload") or {}
        source_schema = str(payload.get("source_result_schema") or "")
        row = {
            "research_result_leaf": leaf_sha,
            "project_id": payload.get("project_id"),
            "mode": payload.get("mode"),
            "evaluated_at": payload.get("evaluated_at"),
            "status": payload.get("status"),
            "source_result_schema": source_schema or None,
            "source_successor_result_sha256": payload.get(
                "source_successor_result_sha256"
            ),
            "trial_family_id": payload.get("trial_family_id"),
            "model_bundle_sha256": payload.get("model_bundle_sha256"),
            "source_candidate_sha256": payload.get("source_candidate_sha256"),
            "candidate_sha256": payload.get("candidate_sha256"),
            "failed_gate_names": list(payload.get("failed_gate_names") or ()),
            "learning_interpretation": payload.get("learning_interpretation"),
            "promotion_eligible": bool(payload.get("promotion_eligible")),
            "family_retirement_authority": bool(
                payload.get("family_retirement_authority")
            ),
            "capital_authority": False,
        }
        model_results.append(row)
        if source_schema != "jaggedthoughts-market-flow-successor-result-v1":
            continue
        family_id = str(payload.get("trial_family_id") or "unidentified")
        family = family_rows.setdefault(family_id, {
            "trial_family_id": family_id,
            "result_count": 0,
            "typed_failure_count": 0,
            "exact_candidate_rejection_count": 0,
            "prospective_shadow_candidate_count": 0,
            "failed_gate_counts": Counter(),
            "model_bundle_sha256s": set(),
            "candidate_sha256s": set(),
        })
        family["result_count"] += 1
        status = str(payload.get("terminal_status") or payload.get("status") or "")
        if status == "typed_failure":
            family["typed_failure_count"] += 1
        elif status == "screen_rejected":
            family["exact_candidate_rejection_count"] += 1
        elif status == "admission_candidate":
            family["prospective_shadow_candidate_count"] += 1
        family["failed_gate_counts"].update(payload.get("failed_gate_names") or ())
        if payload.get("model_bundle_sha256"):
            family["model_bundle_sha256s"].add(str(payload["model_bundle_sha256"]))
        if payload.get("candidate_sha256"):
            family["candidate_sha256s"].add(str(payload["candidate_sha256"]))
    model_results.sort(key=lambda row: (
        str(row.get("evaluated_at") or ""), str(row["research_result_leaf"]),
    ), reverse=True)
    mechanism_families = []
    for family_id, family in sorted(family_rows.items()):
        if family["prospective_shadow_candidate_count"]:
            status = "prospective_shadow_candidate_present"
        elif family["exact_candidate_rejection_count"]:
            status = "exact_candidates_rejected"
        else:
            status = "search_process_failures_only"
        mechanism_families.append({
            **{key: value for key, value in family.items() if key not in {
                "failed_gate_counts", "model_bundle_sha256s", "candidate_sha256s",
            }},
            "status": status,
            "failed_gate_counts": dict(sorted(family["failed_gate_counts"].items())),
            "model_bundle_sha256s": sorted(family["model_bundle_sha256s"]),
            "candidate_sha256s": sorted(family["candidate_sha256s"]),
            "family_retired": False,
            "retirement_rule": "requires_later_prospective_tournament_evidence",
            "predictive_law_authority": False,
            "capital_authority": False,
        })
    body = {
        "schema": "jaggedthoughts-research-memory-v2",
        "identity": "source_claim_coverage_choice_system_and_model_result_graph",
        "source_count": len(source_meta),
        "mechanism_claim_count": len(claim_meta),
        "dossier_count": len(dossier_meta),
        "research_coverage_assessment_count": len(coverage_meta),
        "research_coverage_count": sum(bool(row["covered"]) for row in coverage_rows),
        "monitor_subscription_count": len(subscription_meta),
        "source_change_event_count": len(source_event_meta),
        "reopen_request_count": len(reopen_meta),
        "reassessment_count": len(reassessment_meta),
        "reused_source_count": sum(bool(row["reused"]) for row in rows),
        "strategy_phenotype_count": len(phenotype_rows),
        "cross_entity_strategy_phenotype_count": sum(bool(row["cross_entity"]) for row in phenotype_rows),
        "mechanism_research_result_count": len(model_results),
        "market_flow_successor_result_count": sum(
            row["source_result_schema"]
            == "jaggedthoughts-market-flow-successor-result-v1"
            for row in model_results
        ),
        "mechanism_family_count": len(mechanism_families),
        "sources": rows,
        "research_coverage": sorted(coverage_rows, key=lambda row: (
            str(row.get("entity_id") or ""), str(row.get("candidate_leaf") or ""),
        )),
        "strategy_phenotypes": phenotype_rows,
        "model_research_results": model_results,
        "mechanism_families": mechanism_families,
        "activation": (
            "A changed configured material source reopens the dossier-local dependency frontier. "
            "An unchanged or accepted reassessment may cover a later candidate's qualitative "
            "coordinates; its quantitative identity remains candidate-local."
        ),
    }
    return {**body, "research_memory_sha256": stable_sha256(body)}


__all__ = [
    "RESEARCH_COVERAGE_SCHEMA",
    "STRATEGY_PHENOTYPE_SCHEMA",
    "candidate_research_coverage",
    "candidate_strategy_phenotype",
    "compile_research_coverage_index",
    "compile_research_memory",
    "record_candidate_research_coverage",
    "strategy_choice_system_phenotype",
]
