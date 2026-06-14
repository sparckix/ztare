"""Shared cognitive-worker metadata helpers.

These fields make the worker shape explicit in run artifacts without changing
the autoresearch loop's control path. They distinguish capability, state,
identity, and transport so downstream projections do not infer those categories
from vague labels like "API" or "agent".
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class WorkerMetadata:
    worker_archetype: str
    worker_capability: str
    worker_state: str
    worker_identity: str
    transport: str
    worker_metadata_source: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


AUTORESEARCH_WORKER_CALL_SITES: tuple[str, ...] = (
    "mutator",
    "judge",
    "committee",
    "inverter_review",
)


def autoresearch_worker_metadata(
    rubric_data: dict[str, Any] | None = None,
    *,
    call_site: str = "mutator",
    default_capability: str = "llm",
    default_transport: str = "api",
) -> WorkerMetadata:
    """Resolve metadata for an autoresearch in-loop worker.

    The current autoresearch path is a fungible, stateless LLM call with state
    supplied by workspace artifacts and the MutatorBriefing. Rubric/env
    overrides let future flag-gated agent workers record their real shape
    without changing projection code.
    """
    rubric = rubric_data or {}
    scoped = rubric.get("worker_metadata")
    if isinstance(scoped, dict):
        per_site = scoped.get(call_site)
        if isinstance(per_site, dict):
            scoped = per_site
    else:
        scoped = {}

    capability = _pick(
        scoped.get("worker_capability"),
        scoped.get("capability"),
        rubric.get(f"{call_site}_worker_capability"),
        rubric.get("worker_capability"),
        _env_agent_capability(call_site, default_capability),
    )
    transport = _pick(
        scoped.get("transport"),
        scoped.get("worker_transport"),
        rubric.get(f"{call_site}_worker_transport"),
        rubric.get("worker_transport"),
        rubric.get("transport"),
        _env_agent_transport(default_transport, capability),
    )
    state = _pick(
        scoped.get("worker_state"),
        rubric.get(f"{call_site}_worker_state"),
        rubric.get("worker_state"),
        "stateless_externalized_briefing",
    )
    identity = _pick(
        scoped.get("worker_identity"),
        rubric.get(f"{call_site}_worker_identity"),
        rubric.get("worker_identity"),
        "fungible",
    )
    archetype = _pick(
        scoped.get("worker_archetype"),
        rubric.get(f"{call_site}_worker_archetype"),
        rubric.get("worker_archetype"),
        _default_archetype(capability, identity),
    )
    source = "rubric_worker_metadata" if scoped else "autoresearch_loop_default"
    return WorkerMetadata(
        worker_archetype=archetype,
        worker_capability=capability,
        worker_state=state,
        worker_identity=identity,
        transport=transport,
        worker_metadata_source=source,
    )


def autoresearch_worker_metadata_by_call_site(
    rubric_data: dict[str, Any] | None = None,
    *,
    call_sites: tuple[str, ...] = AUTORESEARCH_WORKER_CALL_SITES,
) -> dict[str, dict[str, str]]:
    """Return explicit worker metadata for each in-loop worker family."""

    return {
        call_site: autoresearch_worker_metadata(rubric_data, call_site=call_site).to_dict()
        for call_site in call_sites
    }


def aggregate_autoresearch_worker_metadata(
    by_call_site: dict[str, dict[str, str]],
    *,
    primary_call_site: str = "mutator",
) -> dict[str, Any]:
    """Summarize per-call-site metadata into backward-compatible flat fields.

    Historical projection consumers read flat ``transport`` and
    ``worker_archetype`` fields. New rows also carry the full per-call-site
    object; the flat fields are an aggregate that makes "any subscription-backed
    in-loop worker" visible to run-history outcome audits.
    """

    primary = by_call_site.get(primary_call_site) or {}
    transports = sorted(
        {
            str(meta.get("transport") or "").strip()
            for meta in by_call_site.values()
            if isinstance(meta, dict) and str(meta.get("transport") or "").strip()
        }
    )
    capabilities = sorted(
        {
            str(meta.get("worker_capability") or "").strip()
            for meta in by_call_site.values()
            if isinstance(meta, dict) and str(meta.get("worker_capability") or "").strip()
        }
    )
    has_subscription = "subscription_cli" in transports
    transport = "subscription_cli" if has_subscription else (primary.get("transport") or "api")
    capability = "agent" if has_subscription else (primary.get("worker_capability") or "llm")
    archetype = (
        "mixed_subscription_worker_set"
        if has_subscription and len(set(transports)) > 1
        else primary.get("worker_archetype") or _default_archetype(str(capability), "fungible")
    )
    return {
        "worker_archetype": str(archetype),
        "worker_capability": str(capability),
        "worker_state": str(primary.get("worker_state") or "stateless_externalized_briefing"),
        "worker_identity": str(primary.get("worker_identity") or "fungible"),
        "transport": str(transport),
        "worker_metadata_source": "autoresearch_loop_call_site_aggregate",
        "worker_transport_set": transports,
        "worker_capability_set": capabilities,
        "worker_metadata_by_call_site": by_call_site,
    }


def _pick(*values: Any) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _env_agent_capability(call_site: str, default: str) -> str:
    site_key = "".join(ch if ch.isalnum() else "_" for ch in call_site.upper()).strip("_")
    flag = (
        os.environ.get(f"ZTARE_AGENT_DISPATCH_{site_key}")
        or os.environ.get("ZTARE_AGENT_DISPATCH")
        or "off"
    ).strip().lower()
    if flag in {"1", "true", "on", "agent"}:
        return "agent"
    return default


def _env_agent_transport(default: str, capability: str) -> str:
    if capability == "agent":
        return "subscription_cli"
    return default


def _default_archetype(capability: str, identity: str) -> str:
    if capability == "agent" and identity == "fungible":
        return "fungible_agent_worker"
    if capability == "llm" and identity == "fungible":
        return "fungible_llm_call"
    return f"{identity}_{capability}_worker"
