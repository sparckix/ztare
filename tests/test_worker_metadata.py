from __future__ import annotations

from ztare.common.worker_metadata import (
    aggregate_autoresearch_worker_metadata,
    autoresearch_worker_metadata,
    autoresearch_worker_metadata_by_call_site,
)


def test_autoresearch_worker_metadata_defaults_to_fungible_api_llm() -> None:
    meta = autoresearch_worker_metadata({})

    assert meta.worker_archetype == "fungible_llm_call"
    assert meta.worker_capability == "llm"
    assert meta.worker_state == "stateless_externalized_briefing"
    assert meta.worker_identity == "fungible"
    assert meta.transport == "api"


def test_autoresearch_worker_metadata_accepts_scoped_overrides() -> None:
    meta = autoresearch_worker_metadata(
        {
            "worker_metadata": {
                "mutator": {
                    "worker_capability": "agent",
                    "worker_archetype": "fungible_agent_worker",
                    "transport": "subscription_cli",
                }
            }
        },
        call_site="mutator",
    )

    assert meta.worker_capability == "agent"
    assert meta.worker_archetype == "fungible_agent_worker"
    assert meta.transport == "subscription_cli"
    assert meta.worker_metadata_source == "rubric_worker_metadata"


def test_autoresearch_worker_metadata_reads_call_site_env(monkeypatch) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH_MUTATOR", "agent")

    meta = autoresearch_worker_metadata({}, call_site="mutator")

    assert meta.worker_capability == "agent"
    assert meta.worker_archetype == "fungible_agent_worker"
    assert meta.transport == "subscription_cli"


def test_autoresearch_worker_metadata_by_call_site_records_each_worker(monkeypatch) -> None:
    monkeypatch.setenv("ZTARE_AGENT_DISPATCH_JUDGE", "agent")

    by_site = autoresearch_worker_metadata_by_call_site({})

    assert by_site["mutator"]["transport"] == "api"
    assert by_site["judge"]["transport"] == "subscription_cli"
    assert by_site["committee"]["transport"] == "api"
    assert by_site["inverter_review"]["transport"] == "api"


def test_aggregate_autoresearch_worker_metadata_promotes_any_subscription_worker() -> None:
    by_site = {
        "mutator": {
            "worker_archetype": "fungible_llm_call",
            "worker_capability": "llm",
            "worker_state": "stateless_externalized_briefing",
            "worker_identity": "fungible",
            "transport": "api",
            "worker_metadata_source": "autoresearch_loop_default",
        },
        "judge": {
            "worker_archetype": "fungible_agent_worker",
            "worker_capability": "agent",
            "worker_state": "stateless_externalized_briefing",
            "worker_identity": "fungible",
            "transport": "subscription_cli",
            "worker_metadata_source": "autoresearch_loop_default",
        },
    }

    meta = aggregate_autoresearch_worker_metadata(by_site)

    assert meta["transport"] == "subscription_cli"
    assert meta["worker_capability"] == "agent"
    assert meta["worker_archetype"] == "mixed_subscription_worker_set"
    assert meta["worker_transport_set"] == ["api", "subscription_cli"]
    assert meta["worker_metadata_by_call_site"] == by_site
