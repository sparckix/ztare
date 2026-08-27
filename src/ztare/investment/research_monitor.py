"""Event-driven reopening of accepted investment research.

An accepted dossier owns a monitor subscription.  When a configured material
public source changes content, this module records the source-change event,
computes the dossier-local dependency frontier, and enqueues one immutable
reassessment request.  Fetching, event detection, and interpretation remain
separate identities.
"""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
import json
from pathlib import Path
from typing import Any, Mapping

import yaml

from ztare.common.equivariance import stable_sha256
from ztare.leanmill import work_queue

from .contracts import canonical_timestamp, require_text, timestamp_key
from .golden_store import GoldenEdge, GoldenLeaf, GoldenStore
from .research_jobs import research_rank_priority
from .sources import load_source_manifest


MONITOR_SUBSCRIPTION_SCHEMA = "jaggedthoughts-research-monitor-subscription-v1"
SOURCE_CHANGE_EVENT_SCHEMA = "jaggedthoughts-public-source-change-event-v1"
REOPEN_REQUEST_SCHEMA = "jaggedthoughts-research-reopen-request-v1"
REASSESSMENT_JOB_SCHEMA = "jaggedthoughts-subscription-reassessment-job-v1"
REASSESSMENT_JOB_KIND = "jaggedthoughts_subscription_reassessment"

# Market prices update frequently and are already handled by the quantitative
# compiler.  These adapters can change the thesis evidence or portfolio
# fundamentals and therefore justify qualitative reassessment.
MATERIAL_MONITOR_ADAPTERS = frozenset({
    "sec_companyfacts",
    "sec_submissions",
    "ishares_fundamentals",
    "vanguard_fundamentals",
    "harbor_fundamentals",
    "avantis_fundamentals",
    "first_trust_fundamentals",
    "first_trust_holdings",
})


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(dict(payload), indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


@lru_cache(maxsize=8)
def _read_source_configuration(
    manifest_path: str, modified_ns: int, size: int,
) -> tuple[dict[str, Any], ...]:
    del modified_ns, size
    manifest = load_source_manifest(manifest_path)
    if not isinstance(manifest, Mapping):
        raise ValueError("investment source manifest must be an object")
    return tuple(
        dict(row) for row in manifest.get("sources") or () if isinstance(row, Mapping)
    )


@lru_cache(maxsize=8)
def _configured_manifest_path(
    root_path: str, modified_ns: int, size: int,
) -> str:
    del modified_ns, size
    root = Path(root_path)
    workspace = yaml.safe_load((root / "workspace.yaml").read_text(encoding="utf-8"))
    if not isinstance(workspace, Mapping):
        raise ValueError("investment workspace configuration must be an object")
    return str((root / str(workspace.get("source_manifest") or "sources.yaml")).resolve())


def _source_configuration(root: Path) -> list[dict[str, Any]]:
    workspace_path = root / "workspace.yaml"
    workspace_stat = workspace_path.stat()
    manifest_path = Path(_configured_manifest_path(
        str(root.resolve()), workspace_stat.st_mtime_ns, workspace_stat.st_size,
    ))
    stat = manifest_path.stat()
    return list(_read_source_configuration(
        str(manifest_path.resolve()), stat.st_mtime_ns, stat.st_size,
    ))


def _current_receipts(root: Path) -> dict[str, dict[str, Any]]:
    receipts: dict[str, dict[str, Any]] = {}
    heads = _read_json(root / "data" / "source_receipt_heads.json") or {}
    run = _read_json(root / "data" / "latest_source_run.json") or {}
    for row in [*(heads.get("receipts") or ()), *(run.get("source_receipts") or ())]:
        if not isinstance(row, Mapping) or not row.get("source_id"):
            continue
        source_id = str(row["source_id"])
        current = receipts.get(source_id)
        if current is None or str(row.get("retrieved_at") or "") >= str(current.get("retrieved_at") or ""):
            receipts[source_id] = dict(row)
    return receipts


def current_monitor_receipts(root: Path) -> dict[str, dict[str, Any]]:
    """Return the latest fetched receipt known for each source identity."""
    return _current_receipts(root)


@lru_cache(maxsize=4096)
def _material_monitor_source_ids_cached(
    manifest_path: str, modified_ns: int, size: int, entity_id: str,
) -> tuple[str, ...]:
    return tuple(sorted(
        require_text(row.get("id"), "monitor source id")
        for row in _read_source_configuration(manifest_path, modified_ns, size)
        if str(row.get("entity_id") or "") == entity_id
        and str(row.get("adapter") or "") in MATERIAL_MONITOR_ADAPTERS
        and bool(row.get("enabled", True))
    ))


def material_monitor_source_ids(root: Path, entity_id: str) -> tuple[str, ...]:
    """Return the configured material source identities for one entity."""
    workspace_path = root / "workspace.yaml"
    workspace_stat = workspace_path.stat()
    manifest_path = Path(_configured_manifest_path(
        str(root.resolve()), workspace_stat.st_mtime_ns, workspace_stat.st_size,
    ))
    manifest_stat = manifest_path.stat()
    return _material_monitor_source_ids_cached(
        str(manifest_path), manifest_stat.st_mtime_ns, manifest_stat.st_size,
        str(entity_id),
    )


def record_monitor_subscription(
    store: GoldenStore, *, root: Path, owner: str, dossier_leaf: str,
    dossier: Mapping[str, Any], subscribed_at: str | None = None,
    baseline_receipts: Mapping[str, Mapping[str, Any]] | None = None,
) -> str:
    """Create the one monitor identity owned by an accepted dossier."""
    owner_id = require_text(owner, "monitor owner")
    dossier_sha = require_text(dossier_leaf, "monitor dossier leaf")
    dossier_record = store.get_leaf(dossier_sha)
    if dossier_record.get("owner") != owner_id or dossier_record.get("object_kind") != "candidate_research_dossier":
        raise ValueError("monitor subscription must target an owned research dossier")
    object_id = f"research-monitor:{dossier_sha}"
    try:
        return str(store.head(owner_id, "research_monitor_subscription", object_id)["leaf_sha256"])
    except KeyError:
        pass

    entity_id = require_text(dossier.get("entity_id"), "monitor entity_id")
    receipt_by_id = (
        {str(source_id): dict(receipt) for source_id, receipt in baseline_receipts.items()}
        if baseline_receipts is not None else _current_receipts(root)
    )
    trigger_sources: list[dict[str, Any]] = []
    for source in _source_configuration(root):
        if str(source.get("entity_id") or "") != entity_id:
            continue
        adapter = str(source.get("adapter") or "")
        if adapter not in MATERIAL_MONITOR_ADAPTERS or not bool(source.get("enabled", True)):
            continue
        source_id = require_text(source.get("id"), "monitor source id")
        receipt = receipt_by_id.get(source_id) or {}
        trigger_sources.append({
            "source_id": source_id,
            "adapter": adapter,
            "canonical_url": receipt.get("canonical_url") or source.get("url"),
            "baseline_content_sha256": receipt.get("content_sha256"),
            "baseline_receipt_sha256": receipt.get("receipt_sha256"),
            "baseline_retrieved_at": receipt.get("retrieved_at"),
        })
    trigger_sources.sort(key=lambda row: row["source_id"])
    observed_at = canonical_timestamp(subscribed_at or _utc_now(), "monitor subscribed_at")
    body = {
        "schema": MONITOR_SUBSCRIPTION_SCHEMA,
        "subscription_id": object_id,
        "subscribed_at": observed_at,
        "entity_id": entity_id,
        "candidate_leaf": dossier.get("candidate_leaf"),
        "dossier_leaf": dossier_sha,
        "dossier_sha256": dossier.get("dossier_sha256"),
        "trigger_sources": trigger_sources,
        "decisive_observation": dossier.get("decisive_observation"),
        "falsifiers": list(dossier.get("falsifiers") or ()),
        "authority": "research_reassessment_only",
        "residuals": ([] if trigger_sources else [
            "No configured material source adapter can currently activate this subscription."
        ]),
    }
    leaf = GoldenLeaf(
        owner=owner_id,
        object_kind="research_monitor_subscription",
        object_id=object_id,
        epoch=stable_sha256(body),
        occurred_at=observed_at,
        available_at=observed_at,
        payload=body,
        source_refs=(f"dossier_leaf:{dossier_sha}",) + tuple(
            f"source_id:{row['source_id']}" for row in trigger_sources
        ),
    )
    store.append_bundle(
        (leaf,), (GoldenEdge(leaf.leaf_sha256, dossier_sha, "based_on"),),
    )
    return leaf.leaf_sha256


def _affected_claims(store: GoldenStore, dossier_leaf: str) -> list[str]:
    return sorted(
        str(edge["dst_leaf_sha256"])
        for edge in store.list_edges(
            relation="contains", src_leaf_sha256=dossier_leaf, limit=10_000,
        )
    )


def enqueue_changed_source_research(
    workspace: str | Path, *, max_attempts: int = 3,
) -> dict[str, Any]:
    """Compile changed material receipts into local reassessment jobs."""
    root = Path(workspace).expanduser().resolve()
    config = yaml.safe_load((root / "workspace.yaml").read_text(encoding="utf-8"))
    if not isinstance(config, Mapping):
        raise ValueError("investment workspace configuration must be an object")
    owner = require_text(config.get("owner"), "investment workspace owner")
    store = GoldenStore(root / str(config.get("golden_store") or "state/golden_store.sqlite3"))
    receipts = _current_receipts(root)
    discovery = _read_json(root / "discovery" / "latest.json") or {}
    current_candidates = {
        str(row.get("entity_id") or "").upper(): dict(row)
        for row in discovery.get("candidates") or ()
        if (
            isinstance(row, Mapping) and row.get("entity_id")
            and row.get("screen_status") == "qualified"
        )
    }
    subscriptions = store.list_leaves(
        owner=owner, object_kind="research_monitor_subscription", limit=10_000,
    )
    queued: list[dict[str, Any]] = []
    unchanged = 0
    already_enqueued = 0
    connection = work_queue.connect(str(root / "state" / "research_jobs.sqlite3"))
    try:
        existing_work_ids = {
            str(row["work_id"])
            for row in work_queue.list_items(connection, limit=10_000)
        }
        for metadata in subscriptions:
            subscription_leaf = str(metadata["leaf_sha256"])
            subscription = store.get_leaf(subscription_leaf).get("payload") or {}
            subscribed_at = canonical_timestamp(
                subscription.get("subscribed_at"), "monitor subscribed_at",
            )
            dossier_leaf = require_text(subscription.get("dossier_leaf"), "monitor dossier leaf")
            claims = _affected_claims(store, dossier_leaf)
            for trigger in subscription.get("trigger_sources") or ():
                if not isinstance(trigger, Mapping):
                    continue
                source_id = str(trigger.get("source_id") or "")
                receipt = receipts.get(source_id)
                if not receipt:
                    continue
                current_digest = str(receipt.get("content_sha256") or "")
                baseline_digest = str(trigger.get("baseline_content_sha256") or "")
                retrieved_at = canonical_timestamp(
                    receipt.get("retrieved_at"), "source receipt retrieved_at",
                )
                if (
                    not current_digest
                    or current_digest == baseline_digest
                    or timestamp_key(retrieved_at) <= timestamp_key(subscribed_at)
                ):
                    unchanged += 1
                    continue
                receipt_sha = require_text(receipt.get("receipt_sha256"), "source receipt hash")
                # One fetched receipt may differ from several dossier-local
                # baselines. The baseline is part of the event identity; using
                # receipt_sha alone aliases distinct transitions.
                transition_sha = stable_sha256({
                    "source_id": source_id,
                    "previous_content_sha256": baseline_digest or None,
                    "current_content_sha256": current_digest,
                    "receipt_sha256": receipt_sha,
                })
                event_payload = {
                    "schema": SOURCE_CHANGE_EVENT_SCHEMA,
                    # Different subscriptions may hold different baselines for
                    # the same fetched receipt, so the transition is shared only
                    # when both endpoints match.
                    "event_id": f"source-change-v3:{source_id}:{transition_sha}",
                    "source_id": source_id,
                    "adapter": trigger.get("adapter"),
                    "previous_content_sha256": trigger.get("baseline_content_sha256"),
                    "current_content_sha256": current_digest,
                    "receipt_sha256": receipt_sha,
                    "retrieved_at": retrieved_at,
                    "canonical_url": receipt.get("canonical_url"),
                    "raw_path": receipt.get("raw_path"),
                }
                event_leaf = GoldenLeaf(
                    owner=owner,
                    object_kind="public_source_change_event",
                    object_id=str(event_payload["event_id"]),
                    epoch=current_digest,
                    occurred_at=retrieved_at,
                    available_at=retrieved_at,
                    payload=event_payload,
                    source_refs=tuple(filter(None, (
                        str(receipt.get("canonical_url") or ""),
                        str(receipt.get("raw_path") or ""),
                    ))),
                )
                reopen_payload = {
                    "schema": REOPEN_REQUEST_SCHEMA,
                    "request_id": f"research-reopen:{subscription_leaf}:{receipt_sha}",
                    "created_at": retrieved_at,
                    "entity_id": subscription.get("entity_id"),
                    "subscription_leaf": subscription_leaf,
                    "prior_dossier_leaf": dossier_leaf,
                    "source_change_event_leaf": event_leaf.leaf_sha256,
                    "trigger_receipt": dict(receipt),
                    "affected_mechanism_claim_leaves": claims,
                    "expected_exit": "validated_reassessment_or_typed_failure",
                    "capital_authority": False,
                }
                request_sha = stable_sha256(reopen_payload)
                reopen_payload = {**reopen_payload, "request_sha256": request_sha}
                reopen_leaf = GoldenLeaf(
                    owner=owner,
                    object_kind="research_reopen_request",
                    object_id=str(reopen_payload["request_id"]),
                    epoch=request_sha,
                    occurred_at=retrieved_at,
                    available_at=retrieved_at,
                    payload=reopen_payload,
                    source_refs=(f"receipt:{receipt_sha}", f"subscription:{subscription_leaf}"),
                )
                edges = [
                    GoldenEdge(reopen_leaf.leaf_sha256, event_leaf.leaf_sha256, "based_on"),
                    GoldenEdge(reopen_leaf.leaf_sha256, subscription_leaf, "based_on"),
                    GoldenEdge(reopen_leaf.leaf_sha256, dossier_leaf, "based_on"),
                    *(GoldenEdge(reopen_leaf.leaf_sha256, claim, "based_on") for claim in claims),
                ]
                try:
                    store.append_bundle((event_leaf, reopen_leaf), tuple(edges))
                    reopen_leaf_sha = reopen_leaf.leaf_sha256
                except ValueError as error:
                    # Reuse a v1 request already recorded for this exact
                    # subscription and receipt; its queue transition may still
                    # need recovery below.
                    try:
                        prior = store.head(
                            owner, "research_reopen_request", str(reopen_payload["request_id"]),
                        )
                    except KeyError:
                        raise error
                    prior_payload = prior.get("payload") or {}
                    prior_receipt = prior_payload.get("trigger_receipt") or {}
                    if (
                        prior_payload.get("subscription_leaf") != subscription_leaf
                        or prior_receipt.get("receipt_sha256") != receipt_sha
                    ):
                        raise error
                    reopen_payload = dict(prior_payload)
                    request_sha = require_text(
                        reopen_payload.get("request_sha256"), "existing reopen request hash",
                    )
                    reopen_leaf_sha = str(prior["leaf_sha256"])
                relative = Path("research_jobs") / "reopen" / (
                    f"{str(subscription.get('entity_id')).lower()}-{request_sha[:16]}.json"
                )
                _atomic_json(root / relative, reopen_payload)
                work_id = f"investment-reassessment:{request_sha[:24]}"
                if work_id in existing_work_ids:
                    already_enqueued += 1
                    continue
                current_candidate = current_candidates.get(
                    str(subscription.get("entity_id") or "").upper(), {}
                )
                job_body = {
                    "schema": REASSESSMENT_JOB_SCHEMA,
                    "work_id": work_id,
                    "request_sha256": request_sha,
                    "request_path": relative.as_posix(),
                    "reopen_request_leaf": reopen_leaf_sha,
                    "subscription_leaf": subscription_leaf,
                    "prior_dossier_leaf": dossier_leaf,
                    "entity_id": subscription.get("entity_id"),
                    "candidate_id": current_candidate.get("candidate_id"),
                    "candidate_sha256": current_candidate.get("candidate_sha256"),
                    "rank": current_candidate.get("rank"),
                    "research_rank": current_candidate.get("research_rank"),
                    "potential_rank": current_candidate.get("potential_rank"),
                    "stage": "queued",
                    "required_capability": "subscription_web_research",
                    "expected_exit": "validated_reassessment_or_typed_failure",
                    "capital_authority": False,
                }
                job = {**job_body, "job_sha256": stable_sha256(job_body)}
                work_queue.enqueue(
                    connection, kind=REASSESSMENT_JOB_KIND,
                    priority=research_rank_priority(current_candidate) or 200_000,
                    max_attempts=max_attempts, payload=job,
                )
                queued.append({
                    "work_id": work_id,
                    "entity_id": subscription.get("entity_id"),
                    "source_id": source_id,
                    "reopen_request_leaf": reopen_leaf_sha,
                })
                existing_work_ids.add(work_id)
    finally:
        connection.close()
    return {
        "schema": "jaggedthoughts-research-reopen-enqueue-v1",
        "subscription_count": len(subscriptions),
        "queued_count": len(queued),
        "unchanged_checks": unchanged,
        "already_enqueued_count": already_enqueued,
        "queued": queued,
        "authority": "research_reassessment_only",
    }


__all__ = [
    "MONITOR_SUBSCRIPTION_SCHEMA",
    "REASSESSMENT_JOB_KIND",
    "REASSESSMENT_JOB_SCHEMA",
    "REOPEN_REQUEST_SCHEMA",
    "SOURCE_CHANGE_EVENT_SCHEMA",
    "current_monitor_receipts",
    "enqueue_changed_source_research",
    "material_monitor_source_ids",
    "record_monitor_subscription",
]
