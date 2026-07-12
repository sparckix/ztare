from __future__ import annotations

import json

from ztare.leanmill.axiompack_leaf_workbench import AXIOMPACK_LEAF_WORKBENCH_CONTRACT
from ztare.leanmill.common import write_json_atomic, write_text_atomic
from ztare.leanmill.exploration_budget import ExplorationBudgetLedger, budget_preset
from ztare.leanmill.finite_model_census import enumerate_magma_model_universe
from ztare.leanmill.finite_theory_context import (
    build_formal_theory_context,
    save_formal_theory_context,
)
from ztare.leanmill.formal_verification_provider import generate_keypair
from ztare.leanmill.frontier_campaign import packet_for_exact_context, sign_frontier_campaign
from ztare.leanmill.magma_law_universe import anonymous_magma_signature, magma_laws_through_order
from ztare.leanmill.run_observability import (
    build_observability_bundle,
    summarize_frontier_attempt,
)
from ztare.leanmill.theory_campaign_journal import TheoryCampaignEvent, TheoryCampaignJournal


def _frontier_attempt(tmp_path):
    attempt = tmp_path / "attempt-observability"
    signature = anonymous_magma_signature()
    context = build_formal_theory_context(
        signature=signature,
        formulas=tuple(row.axiom for row in magma_laws_through_order(1)),
        universe=enumerate_magma_model_universe(signature, carrier_sizes=(2,)),
    )
    save_formal_theory_context(context, attempt / "formal_context.json")
    packet = packet_for_exact_context(
        campaign_id="campaign:observability",
        blueprint_id="blueprint:observability",
        eigenquestion="Which anonymous presentations survive a held-out boundary?",
        context=context,
        formula_grammar={"schema": "magma-law-grammar-v1", "max_total_order": 1},
        pack_arity=2,
        navigator_contract=AXIOMPACK_LEAF_WORKBENCH_CONTRACT,
        sealed_context_manifest_digest="sha256:" + "0" * 64,
        query_budget={"countermodels": 2, "lean_consequences": 1},
        stop_rule={"max_finalists": 2, "freeze_before_interpretation": True},
    )
    private, public = generate_keypair()
    campaign = sign_frontier_campaign(
        packet, private_key_pem=private, signer_ref="test-authority"
    ).to_json()
    write_json_atomic(attempt / "campaign.json", campaign)
    write_text_atomic(attempt / "campaign_signer_public.pem", public)
    write_json_atomic(
        attempt / "blueprint.json",
        {
            "blueprint_id": packet.blueprint_id,
            "adapter_id": "axiompack",
            "navigator_contract": {"host_isolated_lineages": 2},
        },
    )
    budget = budget_preset("smoke_20m")
    write_json_atomic(attempt / "budget.json", budget.to_json())
    ledger = ExplorationBudgetLedger(
        attempt / "budget.events.jsonl", budget, attempt_id=attempt.name
    )
    reservation = ledger.reserve(
        "navigator:0", "navigation", {"provider_calls": 1, "agent_turns": 1}
    )
    ledger.commit(reservation)
    ledger.freeze_wall_clock(reason="test")
    for index in range(2):
        journal = TheoryCampaignJournal(
            attempt / "lineage_journals" / f"lineage-{index:03d}.events.jsonl"
        )
        journal.append(
            TheoryCampaignEvent(
                attempt_id=f"{attempt.name}:lineage:{index}",
                campaign_id=packet.campaign_id,
                epoch=0,
                context_hash=context.context_hash,
                event_type="theory_presentation_submitted",
                subject_ids=(f"presentation:{index}",),
                authority="test-lineage",
            )
        )
    root = TheoryCampaignJournal(attempt / "events.jsonl")
    root.append(
        TheoryCampaignEvent(
            attempt_id=attempt.name,
            campaign_id=packet.campaign_id,
            epoch=0,
            context_hash=context.context_hash,
            event_type="finalist_frozen",
            subject_ids=("finalist:0",),
            evidence_status="frozen",
            authority="test-host",
        )
    )
    lineages = ["lineage:0", "lineage:1"]
    write_json_atomic(
        attempt / "run.json",
        {
            "schema": "leanmill.frontier_exploration_run.v1",
            "status": "frontier_candidates_frozen_awaiting_boundary_approval",
            "attempt_dir": str(attempt),
            "run_digest": "run:test",
            "packet_digest": campaign["packet_digest"],
            "blueprint_id": packet.blueprint_id,
            "context_hash": context.context_hash,
            "budget_digest": budget.digest,
            "navigation": {
                "context_hash": context.context_hash,
                "context_epoch": 0,
                "finalists": [
                    {"theory_program": {"lineage_id": lineage}}
                    for lineage in lineages
                ],
                "isolation_receipt": {"lineage_ids": lineages},
            },
        },
    )
    write_json_atomic(
        attempt / "boundary_result.json",
        {
            "schema": "leanmill.frontier_boundary_result.v1",
            "status": "boundary_completed",
            "context_hash": context.context_hash,
            "query_results": [{"target_formula_id": "target:0"}],
            "result_sha256": "result:test",
        },
    )
    write_json_atomic(
        attempt / "boundary_completion.json",
        {"status": "boundary_complete", "completion_sha256": "completion:test"},
    )
    write_json_atomic(
        attempt / "boundary_governance_recheck.json",
        {"status": "recheck_completed", "proved_attributed_count": 1},
    )
    write_json_atomic(
        attempt / "lease.json",
        {
            "owner": "vps-worker-a",
            "work_id": "work:frontier-observability",
            "lease_until": 1234567890,
            "heartbeat_at": 1234567000,
            "stale": True,
        },
    )
    return attempt


def test_frontier_attempt_projection_joins_durable_campaign_artifacts(tmp_path):
    attempt = _frontier_attempt(tmp_path)
    legacy_packs = tmp_path / "axiom_pack_candidates.jsonl"
    write_text_atomic(
        legacy_packs,
        json.dumps(
            {
                "pack": {
                    "promotion_status": "quarantined",
                    "domain": "priority",
                    "candidate_axioms": [{"name": "candidate"}],
                }
            }
        ) + "\n",
    )
    bundle = build_observability_bundle(
        attempts_db=tmp_path / "missing-attempts.db",
        verdicts_path=tmp_path / "verdicts.jsonl",
        bank_attempts_path=tmp_path / "bank.jsonl",
        formalize_attempts_path=tmp_path / "formalize.jsonl",
        notes_trace_path=tmp_path / "notes.jsonl",
        cot_traces_path=tmp_path / "cot.jsonl",
        proof_cache_path=tmp_path / "cache.jsonl",
        no_good_path=tmp_path / "no-good.jsonl",
        faithfulness_path=tmp_path / "faithfulness.jsonl",
        decomposition_cache_path=tmp_path / "decomposition.jsonl",
        axiom_packs_path=legacy_packs,
        frontier_attempt_dir=attempt,
    )

    frontier = bundle["frontier_attempt"]
    assert frontier["projection_status"] == "available"
    assert frontier["attempt_identity"]["campaign_id"] == "campaign:observability"
    assert frontier["frozen_packet"]["binding_status"] == "valid"
    assert frontier["frozen_packet"]["signature_status"] == "verified"
    assert frontier["context"]["packet_matches_snapshot"] is True
    assert frontier["context"]["run_matches_snapshot"] is True
    assert frontier["lineages"]["configured_count"] == 2
    assert frontier["lineages"]["lineage_journal_count"] == 2
    assert frontier["budget"]["ledger"]["usage"]["provider_calls"] == 1
    assert frontier["budget"]["ledger"]["outstanding_reservation_count"] == 0
    assert frontier["ownership"]["status"] == "observational"
    assert frontier["ownership"]["authority"] == "derived_heartbeat_non_authoritative"
    assert frontier["ownership"]["owner"] == "vps-worker-a"
    assert frontier["ownership"]["work_id"] == "work:frontier-observability"
    assert frontier["ownership"]["lease_state"] == "stale"
    assert frontier["ownership"]["lease_until"] == 1234567890
    assert frontier["ownership"]["heartbeat"] == 1234567000
    assert frontier["ownership"]["source"] == "lease"
    assert frontier["boundary"]["status"] == "boundary_complete"
    assert frontier["boundary"]["context_matches_snapshot"] is True
    assert bundle["axiom_packs"]["total"] == 1


def test_frontier_attempt_projection_never_creates_a_missing_budget_ledger(tmp_path):
    attempt = tmp_path / "attempt-no-ledger"
    write_json_atomic(attempt / "budget.json", budget_preset("smoke_20m").to_json())

    projected = summarize_frontier_attempt(attempt)

    assert projected["budget"]["ledger"]["status"] == "missing"
    assert not (attempt / "budget.events.jsonl").exists()
