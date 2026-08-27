from ztare.common.equivariance import stable_sha256
from ztare.investment.learning_scheduler import compile_learning_schedule
from ztare.investment.strategy_control_eligibility import (
    STRATEGY_CONTROL_ELIGIBILITY_FRONTIER_SCHEMA,
)
from ztare.investment.strategy_learning import (
    STRATEGY_COHORT_PLAN_SCHEMA,
    STRATEGY_MOVE_LIBRARY_SCHEMA,
    STRATEGY_PROGRAM_ADOPTION_REQUEST_SCHEMA,
    STRATEGY_PROGRAM_ADOPTION_RESULT_SCHEMA,
    compile_strategy_program_adoption_result,
)
from ztare.investment.strategy_transfer_acquisition import (
    compile_strategy_program_control_acquisition,
    compile_strategy_transfer_acquisition_policy,
)
from ztare.investment.strategy_transfer import compile_strategy_program_transfer_index


def test_strategy_acquisition_selects_distinguishing_batch_and_changes_queue_order():
    family = "f" * 64
    moves = [
        {
            "move_sha256": "m1", "entity_id": "FOCAL", "claim_status": "supported",
            "causal_panel_status": "treatment_event_ready", "outcome_episodes": [],
            "outcome_contracts": [{"contract_sha256": "c1", "metric_id": "margin", "due_at": "2027-01-01T00:00:00Z"}],
        },
        {
            "move_sha256": "m2", "entity_id": "NEXT", "option_id": "integrate_repairs",
            "description": "Integrate scarce repairs.", "claim_status": "supported",
            "causal_panel_status": "treatment_timing_interval_censored",
            "implementation_event": {"observed": True}, "mechanism_signature_sha256": family,
            "mechanism_phenotype_sha256": "p2", "mechanism_signature": {"action": "integrate_value_chain"},
            "frontier_bundle_count": 2, "local_peak_bundle_count": 3, "evidence_refs": ["filing"],
            "outcome_episodes": [],
            "outcome_contracts": [{"contract_sha256": "c2", "metric_id": "repair_margin", "due_at": "2028-01-01T00:00:00Z"}],
        },
    ]
    library = {
        "schema": STRATEGY_MOVE_LIBRARY_SCHEMA, "library_sha256": "library",
        "move_count": 2, "move_family_count": 1, "moves": moves,
        "move_families": [{"mechanism_signature_sha256": family, "entity_ids": ["A", "B"], "environment_count": 3}],
    }
    requests = [
        {"request_sha256": "r1", "peer_entity_id": "LOW", "mechanism_signature_sha256": family,
         "mechanism_phenotype_sha256": "p1", "industry_id": "industry", "search_end_at": "2026-01-01T00:00:00Z"},
        {"request_sha256": "r2", "peer_entity_id": "HIGH", "mechanism_signature_sha256": family,
         "mechanism_phenotype_sha256": "p1", "industry_id": "industry", "search_end_at": "2026-01-01T00:00:00Z"},
        {"request_sha256": "r3", "peer_entity_id": "XFER", "mechanism_signature_sha256": family,
         "mechanism_phenotype_sha256": "p1", "industry_id": "other-industry",
         "search_role": "cross_environment_transfer_discovery", "search_end_at": "2026-01-01T00:00:00Z"},
    ]
    plan = {
        "schema": STRATEGY_COHORT_PLAN_SCHEMA, "plan_sha256": "plan", "requests": requests,
        "target_control_unit_count": 2, "exact_focal_move_count": 1,
        "transfer_environment_searches": [{
            "mechanism_phenotype_sha256": "p1", "target_industry_id": "other-industry",
            "anchor_entity_ids": ["XFER"],
        }],
    }
    frontier = {
        "schema": STRATEGY_CONTROL_ELIGIBILITY_FRONTIER_SCHEMA, "plan_sha256": "plan",
        "control_frontier_sha256": "frontier", "audit": {"admissible_control_count": 0},
        "next_source_requests": [
            {"request_sha256": "r1", "required_evidence": ["adoption_search"]},
            {"request_sha256": "r2", "required_evidence": ["adoption_search"]},
            {"request_sha256": "r3", "required_evidence": ["adoption_search"]},
        ],
    }
    jobs = [
        {"work_id": "low", "kind": "jaggedthoughts_strategy_cohort_research", "status": "queued", "payload": {"request_sha256": "r1", "entity_id": "LOW"}},
        {"work_id": "high", "kind": "jaggedthoughts_strategy_cohort_research", "status": "queued", "payload": {"request_sha256": "r2", "entity_id": "HIGH"}},
        {"work_id": "transfer", "kind": "jaggedthoughts_strategy_cohort_research", "status": "queued", "payload": {"request_sha256": "r3", "entity_id": "XFER"}},
        {"work_id": "event", "kind": "jaggedthoughts_strategy_event_refinement_research", "status": "queued", "payload": {"move_sha256": "m2", "entity_id": "NEXT"}},
        {"work_id": "activation", "kind": "jaggedthoughts_subscription_activation_research", "status": "queued", "payload": {}},
    ]
    policy = compile_strategy_transfer_acquisition_policy(
        library=library, cohort_plan=plan, control_frontier=frontier,
        panel_readiness={"plan_sha256": "plan", "history_status": [
            {"entity_id": "LOW", "period_count": 4}, {"entity_id": "HIGH", "period_count": 12},
            {"entity_id": "XFER", "period_count": 4},
        ]}, queue_jobs=jobs, subscription_research={"daily_dispatch_budget": {"exhausted": False}},
        generated_at="2026-08-13T00:00:00Z",
    )

    assert [row["peer_entity_id"] for row in policy["control_batch"]["selected"]] == ["XFER", "HIGH"]
    assert policy["next_transition"]["work_id"] == "transfer"
    assert [row["evidence_use"] for row in policy["outcome_watch"]] == [
        "causal_panel_candidate", "descriptive_operating_outcome_only",
    ]
    assert policy["next_cross_family_acquisition"]["acquisition"] == "sharpen_focal_implementation_interval"
    assert policy["next_cross_family_acquisition"]["work_id"] == "event"
    assert policy["next_cross_family_acquisition"]["issue_now"] is True
    schedule = compile_learning_schedule(
        jobs, {}, generated_at="2026-08-13T00:00:00Z", strategy_acquisition_policy=policy,
    )
    assert schedule["next_action"]["work_id"] == "event"
    assert schedule["next_action"]["action_class"] == "sharpen_strategy_treatment_event"


def test_program_control_acquisition_uses_sourced_fragmented_and_local_peak_controls():
    p1, p2, p3, p4 = "1" * 64, "2" * 64, "3" * 64, "4" * 64
    phenotype = {
        "composition_operator": "combine",
        "constituent_mechanism_phenotype_sha256s": [p1, p2, p3],
        "constituent_count": 3,
    }
    source_definition_sha = stable_sha256({
        "metric_locator": None,
        "measurement_source_catalog": None,
    })
    readout = {
        "readout_sha256": "r" * 64, "metric_id": "owner_earnings_margin",
        "unit": "decimal", "direction": "increase", "minimum_effect": 0.01,
        "horizon_days": 730, "source_definition_sha256": source_definition_sha,
    }
    plan_body = {
        "schema": "jaggedthoughts-strategy-program-outcome-plan-v1",
        "entity_id": "TREATED", "program_id": "treated-program",
        "program_expression": "combine(a,b)", "program_roles": ["global_frontier"],
        "program_phenotype": phenotype,
        "program_phenotype_sha256": stable_sha256(phenotype),
        "environment_boundaries": ["software"], "readouts": [readout],
    }
    plan = {**plan_body, "plan_sha256": stable_sha256(plan_body)}
    transfer = compile_strategy_program_transfer_index(
        [plan], [], generated_at="2026-08-23T00:00:00Z",
    )

    moves = []
    programs = {}
    for entity, shas, expression, roles in (
        ("FRAG", (p1, p2, p3), "combine(a,combine(b,c))", ["global_frontier"]),
        ("LOCAL", (p1, p2, p4), "combine(a,combine(b,d))", ["local_peak"]),
        ("BASE", (p1, p2), "combine(a,b)", ["global_frontier"]),
        ("QUEUED", (p1, p2, p3), "combine(x,combine(y,z))", ["global_frontier"]),
        ("FUTURE", (p1, p2, p3), "combine(f,combine(g,h))", ["global_frontier"]),
    ):
        options = []
        for index, phenotype_sha in enumerate(shas):
            option_id = f"{entity.lower()}-{index}"
            move_sha = stable_sha256([entity, option_id])
            moves.append({
                "move_sha256": move_sha, "entity_id": entity, "option_id": option_id,
                "mechanism_phenotype_sha256": phenotype_sha,
                "causal_panel_status": "treatment_event_ready",
                "environment": {"industry_boundary": "software"},
                "implementation_event": {
                    "available_at": (
                        "2026-08-23T00:00:00Z" if entity == "FUTURE"
                        else "2026-08-01T00:00:00Z"
                    ),
                    "source_refs": [f"issuer:{entity}"],
                },
                "outcome_contracts": [{
                    "contract_sha256": stable_sha256([entity, option_id, "outcome"]),
                    "metric_id": "owner_earnings_margin", "unit": "decimal",
                    "direction": "increase", "minimum_effect": 0.01,
                    "horizon_days": 730, "evidence_refs": [f"issuer:{entity}"],
                }],
            })
            if entity == "LOCAL" and index == 2:
                moves[-1]["causal_panel_status"] = "treatment_timing_interval_censored"
                moves[-1].pop("implementation_event")
            options.append({"option_id": option_id, "move_sha256": move_sha})
        programs[entity] = {
            "program_id": f"{entity.lower()}-program", "expression": expression,
            "roles": roles, "options": options,
            "discriminating_option_ids": [options[-1]["option_id"]],
        }
    library = {
        "schema": STRATEGY_MOVE_LIBRARY_SCHEMA, "library_sha256": "library",
        "moves": moves,
    }

    requests = []
    for entity, program in programs.items():
        body = {
            "schema": STRATEGY_PROGRAM_ADOPTION_REQUEST_SCHEMA,
            "request_id": f"request:{entity}", "entity_id": entity,
            "strategy_frontier_sha256": stable_sha256([entity, "frontier"]),
            "evidence_epoch": "2026-08-01T00:00:00Z",
            "search_end_at": "2026-08-22T00:00:00Z",
            "candidate_programs": [program],
            "classification_set": [
                "exact_integrated_program_adoption", "partial_option_adoption",
                "multiple_integrated_programs_observed", "no_integrated_program_adoption_found",
                "insufficient_source_coverage",
            ],
        }
        requests.append({**body, "request_sha256": stable_sha256(body)})
    by_entity = {row["entity_id"]: row for row in requests}

    def result(entity, classification, *, selected=False):
        request = by_entity[entity]
        source = f"https://issuer.example/{entity.lower()}"
        raw = {
            "schema": STRATEGY_PROGRAM_ADOPTION_RESULT_SCHEMA,
            "request_sha256": request["request_sha256"], "entity_id": entity,
            "classification": classification,
            "selected_program_ids": [programs[entity]["program_id"]] if selected else [],
            "assessed_at": "2026-08-22T00:00:00Z",
            "coverage": {"sec_filings_searched": True, "issuer_materials_searched": True},
            "option_events": [{
                "option_id": option["option_id"], "occurred_at": "2026-07-01T00:00:00Z",
                "available_at": "2026-08-01T00:00:00Z", "implementation_state": "operational",
                "source_urls": [source],
            } for option in programs[entity]["options"]],
            "joint_execution_source_urls": [source] if selected else [],
            "sources": [{
                "url": source, "source_kind": "issuer",
                "published_at": "2026-08-01T00:00:00Z", "supports": (
                    ["coordinated_program", *(
                        f"option:{option['option_id']}"
                        for option in programs[entity]["options"]
                    )] if selected else ["implementation"]
                ),
            }],
            "rationale": "Primary documents bound the program classification.", "residuals": [],
        }
        return compile_strategy_program_adoption_result(raw, request)

    acquisition = compile_strategy_program_control_acquisition(
        program_transfer=transfer, library=library,
        program_requests=requests,
        program_results=[
            result("FRAG", "no_integrated_program_adoption_found"),
            result("LOCAL", "exact_integrated_program_adoption", selected=True),
            result("BASE", "exact_integrated_program_adoption", selected=True),
        ],
        queue_jobs=[{
            "work_id": "queued-control", "kind": "jaggedthoughts_strategy_program_adoption_research",
            "status": "queued", "payload": {"request_sha256": by_entity["QUEUED"]["request_sha256"]},
        }],
        generated_at="2026-08-23T00:00:00Z",
    )

    card = acquisition["cards"][0]
    admitted = {
        row["entity_id"]: row["admitted_control_classes"]
        for row in card["admitted_source_controls"]
    }
    assert admitted == {
        "FRAG": ["same_constituents_fragmented"],
        "LOCAL": ["same_size_local_peak"],
        "BASE": ["one_choice_base_program"],
    }
    assert acquisition["candidate_control_count"] == 4
    assert acquisition["admitted_source_control_count"] == 3
    assert acquisition["admitted_fragmented_control_count"] == 1
    assert acquisition["admitted_local_peak_control_count"] == 1
    assert acquisition["admitted_one_choice_base_control_count"] == 1
    assert acquisition["next_transition"]["work_id"] == "queued-control"
    assert "FUTURE" not in {row["entity_id"] for row in card["targets"]}
    assert card["permutation_null"]["syntax_permutations_excluded"].startswith(
        "combine is associative/commutative"
    )
    assert card["permutation_null"]["ready"] is False
    assert card["composition_outcome_comparison_ready"] is False
    assert acquisition["causal_program_credit"] is False
    assert acquisition["security_return_credit"] is False
    assert acquisition["capital_authority"] is False
