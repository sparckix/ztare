import json

from ztare.common.equivariance import stable_sha256
from ztare.investment.business_fingerprint_acquisition import (
    BUSINESS_FINGERPRINT_ACQUISITION_SCHEMA,
)
from ztare.investment.equity_activation_research import (
    ACTIVATION_RESEARCH_JOB_KIND,
    _matrix_policy_assignments,
    compile_equity_activation_research,
    enqueue_workspace_equity_activation_research,
)
from ztare.investment.equity_paper import AUDIT_SCHEMA
from ztare.investment.golden_store import GoldenLeaf, GoldenStore
from ztare.investment.learning_credit import compile_learning_credit_assignment
from ztare.investment.research_memory import RESEARCH_COVERAGE_SCHEMA
from ztare.investment.research_agent import _canonical_evidence_timestamp
from ztare.investment.prospective_response_matrix import _scheduled_review_pairs
from ztare.leanmill import work_queue


def _signed(body, field):
    return {**body, field: stable_sha256(body)}


def test_matrix_policy_randomizes_each_matched_pair_independently():
    rows = [
        {"entity_id": f"E{index}", "candidate_identity": {"rank": index + 1}}
        for index in range(4)
    ]
    assignments = _matrix_policy_assignments(
        rows, audit_sha256=stable_sha256("audit"), batch_id="batch",
        question_frontiers={
            row["entity_id"]: {"frontier_programs": [{"program_id": "q"}]}
            for row in rows
        },
    )
    pairs = [
        [assignments[f"E{index}"], assignments[f"E{index + 1}"]]
        for index in (0, 2)
    ]
    assert all({row["arm_id"] for row in pair} == {
        "incumbent_question", "stochastic_matrix_selected_question",
    } for pair in pairs)
    assert pairs[0][0]["pair_randomization_sha256"] != pairs[1][0][
        "pair_randomization_sha256"
    ]


def test_matrix_policy_winner_requires_exact_component_credit():
    rows = [
        {"entity_id": f"E{index}", "candidate_identity": {"rank": index + 1}}
        for index in range(20)
    ]
    frontiers = {
        row["entity_id"]: {"frontier_programs": [{"program_id": "q"}]}
        for row in rows
    }
    policy_body = {
        "schema": "jaggedthoughts-activation-matrix-policy-learning-v2",
        "complete_pair_count": 20,
        "eligible_pair_set_sha256": stable_sha256("pairs"),
        "routing_change_allowed": True,
        "preferred_arm": "stochastic_matrix_selected_question",
    }
    policy = _signed(policy_body, "policy_learning_sha256")
    without_credit = _matrix_policy_assignments(
        rows, audit_sha256=stable_sha256("audit"), batch_id="batch",
        question_frontiers=frontiers, policy_learning=policy,
    )
    assert all(row["eligible"] for row in without_credit.values())

    credit = compile_learning_credit_assignment(
        research_learning={}, closed_book={}, institutional_learning={},
        fund_sleeve_comparison={}, portfolio_policy={},
        activation_matrix_policy_learning=policy,
    )
    admitted = _matrix_policy_assignments(
        rows, audit_sha256=stable_sha256("audit"), batch_id="batch",
        question_frontiers=frontiers, policy_learning=policy,
        learning_credit_assignment=credit,
        current_eligible_pair_set_sha256=policy["eligible_pair_set_sha256"],
    )
    assert any(
        not row["eligible"]
        and row["arm_id"] == "stochastic_matrix_selected_question"
        for row in admitted.values()
    )
    stale = _matrix_policy_assignments(
        rows, audit_sha256=stable_sha256("audit"), batch_id="batch",
        question_frontiers=frontiers, policy_learning=policy,
        learning_credit_assignment=credit,
        current_eligible_pair_set_sha256=stable_sha256("later-pairs"),
    )
    assert all(row["eligible"] for row in stale.values())


def test_scheduled_review_does_not_replace_a_closed_look_with_a_late_pair():
    first = [
        {"pair_id": "a", "completed_at": "2026-01-02T00:00:00Z"},
        {"pair_id": "b", "completed_at": "2026-01-03T00:00:00Z"},
    ]
    reviewed, _, _ = _scheduled_review_pairs(first, 2)
    late = {"pair_id": "older-assignment", "completed_at": "2026-01-04T00:00:00Z"}
    reviewed_later, _, _ = _scheduled_review_pairs([late, *first], 2)
    assert [row["pair_id"] for row in reviewed_later] == [
        row["pair_id"] for row in reviewed
    ]


def test_date_only_evidence_uses_conservative_utc_close():
    assert _canonical_evidence_timestamp("2026-05-08", "available_at") == "2026-05-08T23:59:59Z"
    assert _canonical_evidence_timestamp("2026-05-08T14:30:00-04:00", "available_at") == "2026-05-08T18:30:00Z"


def test_activation_research_selects_shared_batch_and_joins_covering_work():
    at = "2026-08-13T04:00:00Z"
    entities = ("ALPHA", "BETA")
    leaves = {entity: stable_sha256(f"candidate:{entity}") for entity in entities}
    prior_leaves = {entity: stable_sha256(f"dossier-leaf:{entity}") for entity in entities}
    rows, plans, coverages, dossiers, epochs = [], {}, {}, {}, {}
    for rank, entity in enumerate(entities, 1):
        rows.append({
            "entity_id": entity, "candidate_leaf": leaves[entity],
            "candidate_sha256": stable_sha256(f"candidate-body:{entity}"),
            "candidate_identity": {"as_of": at, "rank": rank},
            "status": "proposed_blocked", "activation_eligible": False,
            "blockers": [
                "candidate_bound_research_dossier_absent",
                "business_fingerprint_unknowns_present",
                "strategy_frontier_scope_open",
                "underwriting:factor_expected_return_unavailable_beta_only",
            ],
            "proposal": {
                "proposal_id": f"proposal:{entity}",
                "proposal_sha256": stable_sha256(f"proposal:{entity}"),
            },
        })
        plan_body = {
            "schema": BUSINESS_FINGERPRINT_ACQUISITION_SCHEMA,
            "entity_id": entity,
            "coordinates": [
                {"coordinate_id": "segment_economics", "batch_id": "filing_disaggregation"},
                {"coordinate_id": "pricing_power", "batch_id": "commercial_kpi_disclosure"},
            ],
            "acquisition_batches": [
                {
                    "batch_id": "filing_disaggregation", "acquisition_rank": 1,
                    "information_yield_class": "primary_filing_multi_coordinate",
                    "coordinate_ids": ["segment_economics"],
                    "document_families": ["SEC annual report"],
                    "configured_source_ids": [f"sec_{entity.lower()}_submissions"],
                    "downstream_contracts": [
                        "research_dossier.durable_earnings_bridge",
                        "business_fingerprint.durability",
                        "strategy_frontier.option_economic_bridge",
                    ],
                },
                {
                    "batch_id": "commercial_kpi_disclosure", "acquisition_rank": 2,
                    "coordinate_ids": ["pricing_power"], "downstream_contracts": [],
                },
            ],
        }
        plans[entity] = _signed(plan_body, "source_plan_sha256")
        coverage_body = {
            "schema": RESEARCH_COVERAGE_SCHEMA, "entity_id": entity,
            "candidate_leaf": leaves[entity], "candidate_sha256": rows[-1]["candidate_sha256"],
            "prior_dossier_leaf": prior_leaves[entity], "subscription_leaf": None,
            "accepted_reassessment_leaves": [], "source_checks": [],
            "missing_required_source_ids": [], "max_age_days": 45, "expires_at": None,
            "status": "reassessment_required", "covered": False,
            "deep_research_activation": "await_reassessment", "available_at": at,
            "scope": "qualitative_strategy_industry_and_durable_earnings_only",
            "capital_authority": False,
        }
        coverages[entity] = {
            **_signed(coverage_body, "coverage_sha256"),
            "coverage_leaf": stable_sha256(f"coverage-leaf:{entity}"),
        }
        dossiers[entity] = {
            "entity_id": entity, "candidate_leaf": stable_sha256(f"prior-candidate:{entity}"),
            "dossier_sha256": stable_sha256(f"dossier:{entity}"), "generated_at": at,
        }
        epochs[entity] = [{
            "source_id": f"sec_{entity.lower()}_submissions",
            "status": "success", "content_sha256": stable_sha256(f"filing:{entity}"),
            "receipt_sha256": stable_sha256(f"receipt:{entity}"),
            "retrieved_at": at,
        }]
    audit_body = {
        "schema": AUDIT_SCHEMA, "compiled_at": at,
        "discovery_run_sha256": stable_sha256("run"), "qualified_candidate_count": 2,
        "proposal_count": 2, "eligible_count": 0, "blocked_count": 2, "rows": rows,
        "authority": "paper_research_proposal_audit_only", "capital_authority": False,
        "portfolio_authority": False, "brokerage_authority": False,
    }
    alpha_epoch = stable_sha256({
        "candidate_leaf": leaves["ALPHA"], "candidate_as_of": at,
        "sources": [{
            "source_id": "sec_alpha_submissions",
            "content_sha256": stable_sha256("filing:ALPHA"),
        }],
    })
    queue = [
        {
            "work_id": work_id, "status": "queued",
            "payload": {
                "candidate_leaf": leaves["ALPHA"],
                "prior_dossier_leaf": prior_leaves["ALPHA"],
                "source_batch_id": "filing_disaggregation",
                "coordinate_ids": ["segment_economics"],
                hash_field: alpha_epoch,
            },
        }
        for work_id, hash_field in (
            ("existing-alpha", "source_epoch_sha256"),
            ("duplicate-alpha", "source_material_sha256"),
        )
    ]

    result = compile_equity_activation_research(
        equity_audit=_signed(audit_body, "audit_sha256"), acquisition_plans=plans,
        coverages=coverages, source_epochs=epochs, prior_dossiers=dossiers,
        queue_rows=queue, compiled_at=at,
    )

    assert result["selection"]["batch_id"] == "filing_disaggregation"
    assert [(job["entity_id"], job["stage"]) for job in result["jobs"]] == [
        ("ALPHA", "ready_to_enqueue"), ("BETA", "ready_to_enqueue"),
    ]
    assert set(result["jobs"][0]["coalesced_work_ids"]) == {
        "existing-alpha", "duplicate-alpha",
    }
    assert set(result["requests"][0]["target_blockers"]) == {
        "candidate_bound_research_dossier_absent", "business_fingerprint_unknowns_present",
        "strategy_frontier_scope_open", "research_coverage:reassessment_required",
    }
    assert result["requests"][0]["prior_dossier_identity"]["transport_allowed"] is False
    assert all(not request["activation_allowed"] for request in result["requests"])
    assert alpha_epoch[:16] in result["requests"][0]["request_id"]
    assert plans["ALPHA"]["source_plan_sha256"][:16] in result["requests"][0]["request_id"]


def test_activation_research_refuses_quarantined_parent():
    at = "2026-08-13T04:00:00Z"
    entity = "ALPHA"
    candidate_leaf = stable_sha256("candidate:ALPHA")
    prior_leaf = stable_sha256("dossier:ALPHA")
    audit_body = {
        "schema": AUDIT_SCHEMA, "compiled_at": at,
        "discovery_run_sha256": stable_sha256("run"),
        "qualified_candidate_count": 1, "proposal_count": 0,
        "eligible_count": 0, "blocked_count": 1,
        "rows": [{
            "entity_id": entity, "candidate_leaf": candidate_leaf,
            "candidate_sha256": stable_sha256("candidate-body"),
            "candidate_identity": {"as_of": at, "rank": 1},
            "activation_eligible": False, "blockers": ["candidate_bound_research_dossier_absent"],
        }],
        "authority": "paper_research_proposal_audit_only", "capital_authority": False,
        "portfolio_authority": False, "brokerage_authority": False,
    }
    coverage_body = {
        "schema": RESEARCH_COVERAGE_SCHEMA, "entity_id": entity,
        "candidate_leaf": candidate_leaf, "candidate_sha256": stable_sha256("candidate-body"),
        "prior_dossier_leaf": prior_leaf, "subscription_leaf": None,
        "accepted_reassessment_leaves": [], "source_checks": [],
        "missing_required_source_ids": [], "max_age_days": 45, "expires_at": None,
        "status": "research_evidence_quarantined", "covered": False,
        "deep_research_activation": "request", "available_at": at,
        "scope": "qualitative_strategy_industry_and_durable_earnings_only",
        "capital_authority": False,
    }

    try:
        compile_equity_activation_research(
            equity_audit=_signed(audit_body, "audit_sha256"), acquisition_plans={entity: {}},
            coverages={entity: _signed(coverage_body, "coverage_sha256")},
            source_epochs={}, prior_dossiers={entity: {"entity_id": entity}}, compiled_at=at,
        )
    except ValueError as error:
        assert str(error) == "equity audit has no blocked candidate with reusable research lineage"
    else:
        raise AssertionError("quarantined evidence must route to fresh candidate research")


def test_activation_research_enqueue_is_immutable_and_idempotent(tmp_path, monkeypatch):
    at = "2026-08-13T04:00:00Z"
    workspace = tmp_path / "investment"
    (workspace / "state").mkdir(parents=True)
    (workspace / "workspace.yaml").write_text(
        "owner: paper\ngolden_store: state/golden_store.sqlite3\n", encoding="utf-8",
    )
    store = GoldenStore(workspace / "state" / "golden_store.sqlite3")
    candidate_payload = {
        "schema": "jaggedthoughts-discovery-candidate-v1",
        "candidate_id": "equity:ALPHA", "candidate_sha256": stable_sha256("candidate"),
        "entity_id": "ALPHA", "entity_kind": "public_equity", "as_of": at,
        "screen_status": "qualified", "rank": 1, "research_rank": 1,
        "rank_score": 0.5, "source_refs": [],
    }
    candidate = GoldenLeaf(
        owner="paper", object_kind="discovery_candidate", object_id="equity:ALPHA",
        epoch=candidate_payload["candidate_sha256"], occurred_at=at, available_at=at,
        payload=candidate_payload, source_refs=("fixture",),
    )
    store.append_bundle((candidate,), ())
    epoch_body = {
        "candidate_leaf": candidate.leaf_sha256, "candidate_as_of": at,
        "sources": [{
            "source_id": "sec_alpha_submissions", "canonical_url": "https://www.sec.gov/a",
        }],
    }
    request_body = {
        "schema": "jaggedthoughts-equity-activation-research-request-v1",
        "request_id": "activation-research:audit:ALPHA:filing_disaggregation",
        "created_at": at, "equity_audit_sha256": stable_sha256("audit"),
        "discovery_run_sha256": stable_sha256("run"),
        "candidate_identity": {
            "entity_id": "ALPHA", "candidate_leaf": candidate.leaf_sha256,
            "candidate_sha256": candidate_payload["candidate_sha256"],
            "candidate_id": "equity:ALPHA", "as_of": at, "rank": 1,
            "research_rank": 1,
        },
        "proposal_identity": None, "proposal_status": "evidence_blocked",
        "prior_dossier_identity": {
            "dossier_leaf": stable_sha256("prior-leaf"),
            "dossier_sha256": stable_sha256("prior"), "candidate_leaf": stable_sha256("old"),
            "generated_at": at, "transport_allowed": False,
        },
        "coverage_identity": {"coverage_sha256": stable_sha256("coverage")},
        "source_epoch": {**epoch_body, "source_epoch_sha256": stable_sha256(epoch_body)},
        "acquisition": {
            "source_batch_id": "filing_disaggregation",
            "coordinate_ids": ["segment_economics"],
        },
        "target_blockers": ["candidate_bound_research_dossier_absent"],
        "expected_exit": "validated_transport_and_typed_observations_or_typed_failure",
        "capital_authority": False, "proposal_mutation_allowed": False,
        "activation_allowed": False,
    }
    request = {**request_body, "request_sha256": stable_sha256(request_body)}
    compiled_job = {
        "entity_id": "ALPHA", "work_id": "investment-activation-research:alpha",
        "job_sha256": stable_sha256("compiled-job"),
    }
    batch_body = {
        "schema": "jaggedthoughts-equity-activation-research-batch-v1",
        "requests": [request], "jobs": [compiled_job],
    }
    batch = {**batch_body, "batch_sha256": stable_sha256(batch_body)}
    monkeypatch.setattr(
        "ztare.investment.equity_activation_research.compile_workspace_equity_activation_research",
        lambda root: batch,
    )
    frontier_body = {
        "schema": "jaggedthoughts-company-strategy-frontier-v1",
        "compiler_contract_version": 7,
        "company": {
            "id": "ALPHA", "candidate_leaf": stable_sha256("old"),
            "source_dossier_sha256": stable_sha256("prior"),
        },
        "evidence_epoch": at,
        "frontier_programs": [{
            "program_id": "frontier", "unique_option_ids": ["expand_scope"],
        }],
        "local_peak_programs": [{
            "program_id": "local", "unique_option_ids": [],
        }],
        "option_catalog": [{
            "option_id": "expand_scope", "option_sha256": stable_sha256("option"),
            "description": "Expand the source-bound operating scope.",
            "claim_status": "supported", "implementation_event": None,
            "outcome_contracts": [], "evidence_refs": ["filing"],
            "mechanism": {
                "economic_bridge": "earnings_durability",
                "mechanism_sha256": stable_sha256("mechanism"),
            },
        }],
    }
    frontier = {
        **frontier_body, "strategy_frontier_sha256": stable_sha256(frontier_body),
    }
    frontier_dir = workspace / "strategy_frontiers" / "results"
    frontier_dir.mkdir(parents=True)
    (frontier_dir / "alpha.json").write_text(json.dumps(frontier), encoding="utf-8")

    first = enqueue_workspace_equity_activation_research(workspace, max_attempts=2)
    second = enqueue_workspace_equity_activation_research(workspace, max_attempts=2)

    assert (first["queued_count"], first["reused_count"]) == (1, 0)
    assert (second["queued_count"], second["reused_count"]) == (0, 1)
    connection = work_queue.connect(str(workspace / "state" / "research_jobs.sqlite3"))
    rows = work_queue.list_items(connection, limit=10)
    connection.close()
    assert [(row["kind"], row["status"], row["priority"]) for row in rows] == [
        (ACTIVATION_RESEARCH_JOB_KIND, "queued", 1025000),
    ]
    assert len(list((workspace / "research_jobs" / "activation" / "requests").glob("*.json"))) == 1
    assert len(list((workspace / "research_jobs" / "requests").glob("*.json"))) == 1
    assert len(store.list_leaves(owner="paper", object_kind="agent_research_request", limit=10)) == 1
    dossier_request = json.loads(next(
        (workspace / "research_jobs" / "requests").glob("*.json")
    ).read_text(encoding="utf-8"))
    assert dossier_request["research_question_frontier"]["selected_program"]["atom_ids"] == [
        "strategy_option_evidence:expand_scope",
    ]
    assert dossier_request["research_question_frontier"]["strategy_context"][
        "current_candidate_leaf"
    ] == candidate.leaf_sha256
