import json
from copy import deepcopy

from ztare.common.equivariance import stable_sha256
from ztare.investment.research_decision_impact import (
    compile_research_decision_impact_receipt,
    compile_research_decision_snapshot,
)
from ztare.investment.research_budget_tournament import (
    advance_research_budget_tournament,
    compile_research_budget_review,
    freeze_research_budget_tournament,
    research_budget_tournament_status,
    settle_research_budget_block,
)
from ztare.investment.learning_scheduler import LEARNING_SCHEDULE_SCHEMA


def _schedule(block: int):
    def action(name, rank, created, proximity, information):
        return {
            "work_id": f"{name}-{block}", "rank": rank,
            "ranking_score": 1 / rank, "queue_created_at_epoch": created,
            "components": {
                "decision_proximity_prior": proximity,
                "law_scope_separation_upper_bound": information,
                "law_scope_compression_upper_bound": information,
                "unseen_entity_context": information,
                "cohort_sampling_gap_upper_bound": information,
            },
        }

    body = {
        "schema": LEARNING_SCHEDULE_SCHEMA,
        "generated_at": f"2026-08-{block + 1:02d}T00:00:00Z",
        "actions": [
            action("current", 1, 4, 0.1, 0.1),
            action("decision", 2, 3, 1.0, 0.2),
            action("information", 3, 2, 0.2, 1.0),
            action("fifo", 4, 1, 0.1, 0.1),
        ],
    }
    return {**body, "schedule_sha256": stable_sha256(body)}


def _impact_receipt(freeze, work_id, day, *, changed=True):
    choice = {"disposition": "monitor", "selected_ids": [work_id]}
    before = compile_research_decision_snapshot(
        decision_kind="candidate_disposition", subject_id=work_id,
        decision_surface_id=f"candidate:{work_id}", source_artifact_ref="book:before",
        source_artifact_sha256="a" * 64, choice=choice,
        captured_at=f"2026-08-{day:02d}T00:30:00Z",
    )
    after = compile_research_decision_snapshot(
        decision_kind="candidate_disposition", subject_id=work_id,
        decision_surface_id=f"candidate:{work_id}", source_artifact_ref="book:after",
        source_artifact_sha256="b" * 64,
        choice={**choice, "disposition": "paper_watch"} if changed else choice,
        captured_at=f"2026-08-{day:02d}T01:50:00Z",
    )
    evidence_ref = f"evidence:{work_id}"
    return compile_research_decision_impact_receipt(
        research_budget_freeze=freeze, work_id=work_id,
        evidence_ref=evidence_ref, evidence_sha256=stable_sha256(evidence_ref),
        evidence_available_at=f"2026-08-{day:02d}T01:30:00Z",
        decision_before=before, decision_after=after,
        consumed_at=f"2026-08-{day:02d}T01:45:00Z",
    )


def test_shadow_budget_freeze_and_multiplicity_gate(tmp_path):
    settlements = []
    for block in range(8):
        schedule = _schedule(block)
        original = deepcopy(schedule)
        freeze = freeze_research_budget_tournament(
            schedule, frozen_at=f"2026-08-{block + 1:02d}T01:00:00Z",
            inference_block_id=f"block-{block}", capacity=1,
        )
        assert schedule == original
        assert freeze["queue_mutation_authority"] is False
        chosen = {row["policy_id"]: row["selected_work_ids"][0] for row in freeze["arms"]}
        assert chosen == {
            "current_priority": f"current-{block}", "fifo": f"fifo-{block}",
            "decision_proximity": f"decision-{block}",
            "information_value_per_cost": f"information-{block}",
        }
        outcomes = []
        for policy, work_id in chosen.items():
            changed = policy == "information_value_per_cost"
            outcomes.append({
                "work_id": work_id,
                "observed_at": f"2026-08-{block + 1:02d}T02:00:00Z",
                "dispatch_cost_units": 1,
                "research_yield_observed": changed,
                "decision_changed": changed,
                "evidence_ref": f"evidence:{work_id}",
                "evidence_sha256": stable_sha256(f"evidence:{work_id}"),
                "decision_ref": f"decision:{work_id}" if changed else None,
                "decision_impact_receipt": (
                    _impact_receipt(freeze, work_id, block + 1) if changed else None
                ),
            })
        settlements.append(settle_research_budget_block(
            freeze, outcomes, settled_at=f"2026-08-{block + 1:02d}T03:00:00Z",
        ))

    early = compile_research_budget_review(settlements[:7], generated_at="2026-08-12T00:00:00Z")
    assert early["recommended_policy_id"] is None
    review = compile_research_budget_review(settlements, generated_at="2026-08-12T00:00:00Z")
    assert review["recommended_policy_id"] == "information_value_per_cost"
    assert review["queue_mutation_authority"] is False
    current = tmp_path / "institutional_learning/research_budget_tournament/current"
    current.mkdir(parents=True)
    for name, payload in (
        ("freeze.json", freeze),
        ("settlement.json", settlements[-1]),
        ("latest.json", review),
    ):
        (current / name).write_text(json.dumps(payload), encoding="utf-8")
    status = research_budget_tournament_status(tmp_path)
    assert status["enabled"] is True
    assert status["recommended_policy_id"] == "information_value_per_cost"


def test_terminal_block_advances_to_the_next_queue_epoch(tmp_path):
    old, new = _schedule(0), _schedule(1)
    freeze = freeze_research_budget_tournament(
        old, frozen_at="2026-08-01T01:00:00Z", inference_block_id="block-0",
    )
    current = tmp_path / "institutional_learning/research_budget_tournament/current"
    current.mkdir(parents=True)
    (current / "freeze.json").write_text(json.dumps(freeze), encoding="utf-8")
    terminal = []
    for work_id in {item for arm in freeze["arms"] for item in arm["selected_work_ids"]}:
        yielded = work_id.startswith("information-")
        terminal.append({
            "work_id": work_id, "status": "done",
            "payload": {
                "stage": "researched" if yielded else "superseded",
                "completed_at": "2026-08-01T02:00:00Z",
                "result_path": "evidence/result.json" if yielded else None,
                "result_sha256": "a" * 64 if yielded else None,
                "decision_ref": "decision:changed" if yielded else None,
            },
        })
    queued = [{"work_id": row["work_id"], "status": "queued", "payload": {}}
              for row in new["actions"]]
    status = advance_research_budget_tournament(
        tmp_path, new, terminal + queued, advanced_at="2026-08-02T03:00:00Z",
    )
    assert status["source_schedule_sha256"] == new["schedule_sha256"]
    assert status["settlement_status"] == "censored_pending_outcomes"
    settled = json.loads((
        tmp_path / "institutional_learning/research_budget_tournament/runs"
        / old["schedule_sha256"] / "settlement.json"
    ).read_text(encoding="utf-8"))
    assert settled["status"] == "complete_block"
    assert all(row["decision_impact_per_cost"] == 0 for row in settled["arm_results"])


def test_decision_ref_and_administrative_churn_cannot_earn_impact():
    schedule = _schedule(0)
    freeze = freeze_research_budget_tournament(
        schedule, frozen_at="2026-08-01T01:00:00Z", inference_block_id="block-impact",
    )
    work_id = freeze["arms"][0]["selected_work_ids"][0]
    unchanged = _impact_receipt(freeze, work_id, 1, changed=False)
    assert unchanged["decision_changed"] is False
    result = settle_research_budget_block(freeze, [{
            "work_id": work_id, "observed_at": "2026-08-01T02:00:00Z",
            "dispatch_cost_units": 1, "research_yield_observed": True,
            "decision_changed": True, "evidence_ref": f"evidence:{work_id}",
            "evidence_sha256": stable_sha256(f"evidence:{work_id}"),
            "decision_ref": f"decision:{work_id}",
            "decision_impact_receipt": unchanged,
        }], settled_at="2026-08-01T03:00:00Z")
    outcome = result["outcomes"][0]
    assert outcome["research_yield_observed"] is True
    assert outcome["decision_changed"] is False
    assert outcome["decision_impact_status"] == "verified_unchanged_decision"


def test_future_dossier_earns_impact_only_through_its_proposal(tmp_path):
    leaf, dossier_sha = "c" * 64, "d" * 64
    proposal_dir = tmp_path / "paper_proposals/equities"
    proposal_dir.mkdir(parents=True)

    def write_audit(row, compiled_at):
        body = {
            "schema": "jaggedthoughts-public-equity-paper-proposal-audit-v1",
            "compiled_at": compiled_at, "rows": [row],
        }
        (proposal_dir / "latest.json").write_text(json.dumps({
            **body, "audit_sha256": stable_sha256(body),
        }), encoding="utf-8")

    write_audit({
        "candidate_leaf": leaf, "status": "evidence_blocked",
        "blockers": ["candidate_bound_dossier_absent"], "proposal": None,
    }, "2026-08-01T00:30:00Z")
    action = {
        "work_id": "research-one", "kind": "jaggedthoughts_subscription_research",
        "rank": 1, "ranking_score": 1.0, "queue_created_at_epoch": 1,
        "components": {"decision_proximity_prior": 1.0},
    }
    schedule_body = {
        "schema": LEARNING_SCHEDULE_SCHEMA,
        "generated_at": "2026-08-01T00:45:00Z", "actions": [action],
    }
    schedule = {**schedule_body, "schedule_sha256": stable_sha256(schedule_body)}
    queued = [{
        "work_id": "research-one", "kind": "jaggedthoughts_subscription_research",
        "status": "queued", "payload": {
            "candidate_leaf": leaf, "entity_kind": "public_equity",
        },
    }]
    advance_research_budget_tournament(
        tmp_path, schedule, queued, advanced_at="2026-08-01T01:00:00Z",
    )
    proposal_body = {
        "schema": "jaggedthoughts-public-equity-paper-proposal-v1",
        "proposal_id": "equity-paper:ONE", "activation_eligible": True,
        "activation_blockers": [],
        "next_activation": "operator_activate_zero_weight_paper_watch",
        "evidence": {"dossier_sha256": dossier_sha},
    }
    proposal = {**proposal_body, "proposal_sha256": stable_sha256(proposal_body)}
    write_audit({
        "candidate_leaf": leaf, "status": "eligible_proposal",
        "blockers": [], "proposal": proposal,
    }, "2026-08-01T02:10:00Z")
    queued[0].update(status="done", payload={
        **queued[0]["payload"], "stage": "researched",
        "completed_at": "2026-08-01T02:00:00Z",
        "dossier_path": "research/dossiers/one.json", "dossier_sha256": dossier_sha,
    })
    advance_research_budget_tournament(
        tmp_path, schedule, queued, advanced_at="2026-08-01T03:00:00Z",
    )
    settlement = json.loads((
        tmp_path / "institutional_learning/research_budget_tournament/current/settlement.json"
    ).read_text(encoding="utf-8"))
    outcome = settlement["outcomes"][0]
    assert outcome["decision_impact_status"] == "verified_changed_decision"
    assert outcome["decision_impact_receipt"]["capital_authority"] is False
