from ztare.common.equivariance import stable_sha256
from ztare.investment.learning_experiment_activation import compile_learning_experiment_activation
from ztare.investment.learning_credit import (
    compile_learning_credit_assignment,
    learning_credit_allows,
)
from ztare.investment.learning_experiment_design import compile_learning_experiment_design
from ztare.investment.research_jobs import (
    assign_research_question_policies,
    compile_research_request,
    compile_research_learning,
)
from ztare.investment.prospective_return_window import (
    bind_prospective_return_window,
    settle_prospective_return_window,
)
from ztare.investment.research_question_policy_outcome import (
    freeze_research_question_policy_action,
    settle_research_question_policy_outcome,
)


def _components(result):
    return {row["component_id"]: row for row in result["components"]}


def test_question_assignment_is_candidate_level_and_batch_invariant():
    leaves = [f"{index:064x}" for index in range(1, 4)]

    def assigned(values, run, when):
        rows = [
            {"entity_kind": "public_equity", "candidate_leaf": leaf}
            for leaf in values
        ]
        assign_research_question_policies(
            rows, source_run_ids=(run,), completed_at=when,
        )
        return {
            row["candidate_leaf"]: {
                key: row["research_policy_assignment"][key]
                for key in (
                    "assignment_unit_id", "randomization_sha256", "arm_id",
                    "assignment_probability",
                )
            }
            for row in rows
        }

    baseline = assigned(leaves, "run-a", "2026-08-01T00:00:00Z")
    changed = assigned(
        [f"{99:064x}", *reversed(leaves), f"{100:064x}"],
        "run-b", "2026-08-09T00:00:00Z",
    )
    assert {leaf: changed[leaf] for leaf in leaves} == baseline


def test_research_request_binds_v2_assignment_unit():
    request = compile_research_request(
        job={"work_id": "job:a", "job_sha256": "b" * 64, "cycle_sha256": "c" * 64},
        candidate={
            "candidate_id": "equity:ABC", "candidate_sha256": "a" * 64,
            "entity_id": "ABC", "entity_kind": "public_equity",
            "as_of": "2026-08-01T00:00:00Z", "screen_status": "qualified",
            "source_refs": [],
        },
        candidate_leaf="e" * 64,
        discovery_run={
            "run_id": "run:a", "run_sha256": "d" * 64,
            "rank_program_input": {"lanes": [{
                "benchmark_id": "SPY", "candidates": [{"candidate_id": "equity:ABC"}],
            }]},
        },
        created_at="2026-08-01T00:00:00Z",
    )
    assert request["learning_contract"]["question_policy_assignment_unit_id"] == "e" * 64
    assert request["research_policy_outcome_contract"]["benchmark_id"] == "SPY"


def test_question_policy_outcome_freezes_probe_and_settles_active_contribution():
    request = compile_research_request(
        job={"work_id": "job:a", "job_sha256": "b" * 64, "cycle_sha256": "c" * 64},
        candidate={
            "candidate_id": "equity:ABC", "candidate_sha256": "a" * 64,
            "entity_id": "ABC", "entity_kind": "public_equity",
            "as_of": "2026-08-01T00:00:00Z", "screen_status": "qualified",
            "source_refs": [],
        },
        candidate_leaf="e" * 64,
        discovery_run={
            "run_id": "run:a", "run_sha256": "d" * 64,
            "rank_program_input": {"lanes": [{
                "benchmark_id": "SPY", "candidates": [{"candidate_id": "equity:ABC"}],
            }]},
        },
        created_at="2026-08-01T00:00:00Z",
    )
    contract = request["research_policy_outcome_contract"]
    forecast_body = {
        "candidate_id": "underwriting_typed_plus_full_research",
        "predicted_values": {"active_return": 0.08},
    }
    forecast = {**forecast_body, "forecast_sha256": stable_sha256(forecast_body)}
    run_body = {
        "schema": "jaggedthoughts-closed-book-forecast-run-v1",
        "run_id": "cb:a",
        "opened_at": "2026-08-20T00:00:00Z",
        "evidence_packet": {
            "subject": {"kind": "paper_watch_decision", "candidate_leaf": "e" * 64},
            "research_snapshot": {"research_program": {
                "assignment_unit_id": "e" * 64,
            }},
        },
        "candidate_forecasts": [forecast],
    }
    run = {**run_body, "run_sha256": stable_sha256(run_body)}
    action = freeze_research_question_policy_action(
        contract, closed_book_runs=[run], frozen_at=contract["decision_cutoff_at"],
    )
    assert action["target_weight"] == 0.05
    points = {
        "ABC": [
            {"entity_id": "ABC", "value": 100, "observed_at": contract["decision_cutoff_at"], "available_at": contract["decision_cutoff_at"], "source_ref": "px:abc:0"},
            {"entity_id": "ABC", "value": 120, "observed_at": contract["outcome_due_at"], "available_at": contract["outcome_due_at"], "source_ref": "px:abc:1"},
        ],
        "SPY": [
            {"entity_id": "SPY", "value": 100, "observed_at": contract["decision_cutoff_at"], "available_at": contract["decision_cutoff_at"], "source_ref": "px:spy:0"},
            {"entity_id": "SPY", "value": 110, "observed_at": contract["outcome_due_at"], "available_at": contract["outcome_due_at"], "source_ref": "px:spy:1"},
        ],
    }
    binding = bind_prospective_return_window(
        contract["return_window"], points=points, as_of=contract["decision_cutoff_at"],
    )
    window = settle_prospective_return_window(
        contract["return_window"], binding, points=points, as_of=contract["outcome_due_at"],
    )
    outcome = settle_research_question_policy_outcome(
        contract, action, return_window_settlement=window,
        settled_at=contract["outcome_due_at"],
    )
    assert round(outcome["incremental_return_vs_no_action"], 6) == 0.00485


def test_due_question_assignment_scores_abstention_but_censors_missing_action_outcome():
    rows = [
        {"entity_kind": "public_equity", "candidate_leaf": f"{index:064x}"}
        for index in (201, 202, 203)
    ]
    assign_research_question_policies(
        rows, source_run_ids=("run",), completed_at="2025-08-01T00:00:00Z",
    )
    requests = [
        {
            "request_id": "abstain", "entity_kind": "public_equity",
            "lifecycle_stage": "researched", "research_policy_assignment":
            rows[0]["research_policy_assignment"],
        },
        {
            "request_id": "missing-action-outcome", "entity_kind": "public_equity",
            "lifecycle_stage": "paper_active", "decision_id": "paper:202",
            "research_policy_assignment": rows[1]["research_policy_assignment"],
        },
        {
            "request_id": "zero-weight-watch", "entity_kind": "public_equity",
            "lifecycle_stage": "paper_active", "decision_id": "paper:203",
            "paper_target_weight": 0.0,
            "research_policy_assignment": rows[2]["research_policy_assignment"],
        },
    ]
    learning = compile_research_learning(
        research_requests=requests, queue_jobs=[],
        generated_at="2026-08-02T00:00:00Z",
    )
    statuses = {
        row["request_ids"][0]: row["economic_outcome_status"]
        for row in learning["research_question_policy_experiment"]["assignment_units"]
    }
    assert statuses == {
        "abstain": "settled_verified_no_action",
        "missing-action-outcome": "due_censored",
        "zero-weight-watch": "settled_verified_no_action",
    }
    assert learning["research_question_policy_experiment"]["routing_decision"][
        "routing_change_allowed"
    ] is False


def test_credit_requires_isolated_variation_not_a_bundled_win():
    routing_body = {
        "schema": "jaggedthoughts-research-question-routing-decision-v1",
        "routing_change_allowed": True,
    }
    routing = {**routing_body, "decision_sha256": stable_sha256(routing_body)}
    research_body = {
        "schema": "jaggedthoughts-research-acquisition-learning-v1",
        "rows": [{"question_program_id": "q1"}],
        "research_question_policy_experiment": {
            "valid_assignment_unit_count": 40, "settled_itt_unit_count": 40,
            "routing_decision": routing,
        },
    }
    research = {**research_body, "learning_sha256": stable_sha256(research_body)}
    matrix_body = {
        "schema": "jaggedthoughts-activation-matrix-policy-learning-v2",
        "valid_pair_count": 20, "complete_pair_count": 20,
        "routing_change_allowed": True,
    }
    matrix = {
        **matrix_body, "policy_learning_sha256": stable_sha256(matrix_body),
    }
    base = dict(
        research_learning=research,
        closed_book={"forecast_learning": {"bundles": [{
            "bundle": {"mechanism_ids": ["valuation", "durability"]},
            "settled_count": 8, "inference_block_count": 8,
            "episodes": [{"candidate_id": "underwriting-v1"}],
        }]}},
        institutional_learning={
            "candidates": [{"law_key": "a"}, {"law_key": "b"}],
            "evaluations": [{"law_key": "a", "promotion_eligible": True}],
        },
        fund_sleeve_comparison={"sleeves": [{"programs": [{
            "program_id": "fund-a", "implementation_review_admitted": True,
        }]}]},
        portfolio_policy={
            "run_count": 8, "settled_count": 8,
            "latest_run": {"policies": [{"policy_id": "learned_law_priority"}],
                "attribution_contract": {"rows": [
                    {
                        "comparison_id": "learned_law_priority__vs__discovery_priority",
                        "law_contributions": [{"law_key": "a"}, {"law_key": "b"}],
                    },
                    {
                        "comparison_id": "fund-a__vs__fund-b",
                        "isolated_component_kind": "fund_implementation_program",
                        "implementation_program_id": "fund-a",
                        "reference_implementation_program_id": "fund-b",
                    },
                ]}},
            "scoreboard": {
                "inference_block_count": 8,
                "attribution_comparisons": [
                    {"comparison_id": "learned_law_priority__vs__discovery_priority", "episode_count": 8},
                    {"comparison_id": "fund-a__vs__fund-b", "episode_count": 8},
                ],
                "latest_policy_review": {
                    "activation_status": "eligible_for_paper_policy_review",
                    "recommended_policy_id": "learned_law_priority",
                },
            },
        },
        activation_matrix_policy_learning=matrix,
    )
    assignment = compile_learning_credit_assignment(**base)
    rows = _components(assignment)

    assert rows["research_question_policy"]["credit_earned"] is True
    assert rows["underwriting_forecast_bundle"]["settled_outcome_count"] == 1
    assert rows["underwriting_forecast_bundle"]["isolated_credit_count"] == 0
    assert rows["strategy_regularity"]["status"] == "bundled_law_policy_outcomes"
    assert rows["strategy_regularity"]["isolated_credit_count"] == 0
    assert rows["fund_implementation_program"]["isolated_credit_count"] == 8
    assert rows["complete_paper_portfolio_policy"]["credit_earned"] is True
    assert learning_credit_allows(
        assignment, component_id="research_question_policy",
        use="future_research_question_routing", source_ref=routing["decision_sha256"],
    )
    assert not learning_credit_allows(
        assignment, component_id="research_question_policy",
        use="operator_paper_policy_review", source_ref=routing["decision_sha256"],
    )
    assert learning_credit_allows(
        assignment, component_id="activation_response_question_policy",
        use="future_activation_question_routing", source_ref=matrix["policy_learning_sha256"],
    )

    invalid_routing = {**routing, "decision_sha256": "invalid"}
    invalid_research_body = {
        **research_body,
        "research_question_policy_experiment": {
            **research_body["research_question_policy_experiment"],
            "routing_decision": invalid_routing,
        },
    }
    base["research_learning"] = {
        **invalid_research_body,
        "learning_sha256": stable_sha256(invalid_research_body),
    }
    assert _components(compile_learning_credit_assignment(**base))[
        "research_question_policy"
    ]["credit_earned"] is False

    base["portfolio_policy"]["latest_run"]["attribution_contract"]["rows"][0][
        "law_contributions"
    ] = [{"law_key": "a"}]
    refined = _components(compile_learning_credit_assignment(**base))
    assert refined["strategy_regularity"]["isolated_credit_count"] == 8


def test_next_design_reuses_trials_and_never_unbundles_components():
    credit = {
        "learning_credit_sha256": "credit",
        "components": [
            {"component_id": name, "credit_earned": False}
            for name in (
                "research_question_policy", "underwriting_forecast_bundle",
                "strategy_regularity", "fund_implementation_program",
                "complete_paper_portfolio_policy",
            )
        ],
    }
    research = {"research_question_policy_experiment": {
        "experiment_id": "coverage-vs-disagreement-itt-v2",
        "valid_assignment_unit_count": 4,
        "settled_itt_unit_count": 0, "minimum_settled_units_per_arm": 20,
        "routing_decision": {"decision_sha256": "route", "unit_set_sha256": "units"},
    }}
    alpha = {
        "same_information_control": True, "eligible_episode_count": 0,
        "nested_model_ids": [
            "valuation_only_control", "durability_valuation_control",
            "strategy_phenotype_durability_valuation",
        ],
        "evidence": {"evidence_sha256": "alpha-evidence"},
        "binding_activation": {"activation_statuses": [{
            "status": "activated", "binding_sha256": "binding",
        }]},
    }
    policy = {"latest_run": {
        "run_id": "policy-1", "run_sha256": "run", "opportunity_book_sha256": "book",
        "attribution_contract": {"comparisons": [{
            "comparison_id": "discovery__vs__equal", "policy_id": "discovery_priority",
            "reference_policy_id": "equal_weight_qualified",
        }], "rows": []},
    }, "scoreboard": {"inference_block_count": 0}}
    funds = {"sleeves": [{"sleeve_id": "value", "programs": [
        {"program_id": "value:a", "program_sha256": "a", "comparison_eligible": True,
         "implementation_review_admitted": True, "identity": {"subject_id": "A"},
         "correlations_to_compared_funds": {"B": 0.4}},
        {"program_id": "value:b", "program_sha256": "b", "comparison_eligible": True,
         "implementation_review_admitted": True, "identity": {"subject_id": "B"}},
    ]}]}
    laws = {"candidates": [{"law_sha256": "law"}], "evaluations": [{
        "law_key": "durability@1", "law_sha256": "law", "evaluation_sha256": "eval",
        "promotion_eligible": True,
    }]}

    result = compile_learning_experiment_design(
        learning_credit_assignment=credit, research_learning=research,
        strategy_alpha_tournament=alpha, institutional_learning=laws,
        fund_sleeve_comparison=funds, portfolio_policy=policy,
    )
    proposed = {row["component_id"]: row for row in result["proposals"]}

    assert proposed["research_question_policy"]["family_id"] == "coverage-vs-disagreement-itt-v2"
    assert proposed["underwriting_forecast_bundle"]["variation"]["varied_component_ids"] == [
        "durable_earnings_expectation", "source_bound_strategy_phenotype",
    ]
    assert proposed["underwriting_forecast_bundle"]["same_information_contract"][
        "one_component_at_a_time"
    ] is True
    assert proposed["strategy_regularity"]["variation"]["varied_component_ids"] == ["durability@1"]
    assert proposed["fund_implementation_program"]["variation"] == {
        "control_ids": ["value:a"], "treatment_ids": ["value:b"],
        "varied_component_ids": ["fund_implementation_program"], "variation_count": 1,
    }
    assert all(row["capital_authority"] is False for row in result["proposals"])
    assert all(row["lineage"]["historical_evidence_relabelled"] is False
               for row in result["proposals"])


def test_activation_uses_only_complete_frozen_pairs_and_exact_preopen_actions():
    selected = [
        {"entity_kind": "public_equity", "candidate_leaf": f"{rank:064x}"}
        for rank in range(1, 4)
    ]
    assign_research_question_policies(
        selected, source_run_ids=("run",), completed_at="2026-08-13T00:00:00Z",
    )
    left, right, third = (row["research_policy_assignment"] for row in selected)
    assert all(row["eligible"] for row in (left, right, third))

    requests = []
    for index, assignment in enumerate((left, right)):
        requests.append({
            "request_id": f"request-{index}", "request_sha256": f"request-sha-{index}",
            "candidate_leaf": f"leaf-{index}", "entity_id": f"E{index}",
            "lifecycle_stage": "evidence_ready", "source_refs": [f"public-{index}"],
            "research_policy_assignment": assignment,
        })
    design = {
        "design_sha256": "design", "proposals": [
            {"experiment_id": "research-design", "family_id": "coverage-vs-disagreement-itt-v2",
             "component_id": "research_question_policy"},
            {"experiment_id": "alpha-design", "family_id": "strategy-alpha-nested-ablation-v1",
             "component_id": "underwriting_forecast_bundle"},
        ],
    }
    alpha_action = {
        "run_id": "run-alpha", "status": "activated", "action_id": "action-alpha",
        "action_sha256": "action-sha", "binding_sha256": "binding-sha",
        "evaluated_at": "2026-08-13T01:00:00Z",
    }
    result = compile_learning_experiment_activation(
        learning_experiment_design=design,
        research_learning={"research_question_policy_experiment": {
            "settled_itt_unit_count": 0, "minimum_settled_units_per_arm": 20,
        }},
        research_requests=requests,
        subscription_research={"queue": {"jobs": [{
            "kind": "jaggedthoughts_subscription_research", "status": "queued",
            "work_id": "work-exact", "payload": {
                "request_sha256": "request-sha-0", "candidate_leaf": "leaf-0", "entity_id": "E0",
            },
        }]}},
        discovery={"schedule": {"next_due_at": "2026-08-14T00:00:00Z"}},
        strategy_alpha_tournament={
            "eligible_episode_count": 0,
            "evidence": {"settlement_count": 0, "gaps": [{
                "code": "settlement_missing", "run_id": "run-alpha",
                "end_at": "2026-11-11T00:00:00Z",
            }]},
            "binding_activation": {
                "activation_statuses": [alpha_action],
                "runs": [{"run_id": "run-alpha", "status": "bound", "gap_codes": []}],
            },
        },
        capital_cycle={"latest_run": {"strategy_alpha_schedule": {
            "scheduled_windows": [],
            "eligibility": [{"eligible": True, "candidate_id": "equity:MRVL"}],
        }}},
        generated_at="2026-08-13T02:00:00Z",
    )
    transitions = {row["component_id"]: row for row in result["transitions"]}
    assert result["next_transition"]["work_id"] == "work-exact"
    assert transitions["research_question_policy"]["issued"]["valid_assignment_unit_count"] == 2
    assert transitions["underwriting_forecast_bundle"]["next_activation"] == {
        "transition": "schedule_next_nonoverlapping_strategy_alpha_window",
        "subject_id": "equity:MRVL", "nomination_sha256": None,
        "not_before": "2026-11-11T00:00:00Z",
        "blocker": "awaiting_nonoverlapping_due_forecast_window",
    }
    assert result["capital_authority"] is False
    assert stable_sha256({k: v for k, v in result.items() if k != "policy_sha256"}) == result["policy_sha256"]
