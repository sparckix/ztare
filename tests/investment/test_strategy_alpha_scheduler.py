import copy
import csv
import json

import pytest

from ztare.common.equivariance import stable_sha256
from ztare.investment import closed_book, workspace
from ztare.investment.golden_store import GoldenLeaf, GoldenStore
from ztare.investment.research_agent import _strategy_frontier_currency
from ztare.investment.strategy_alpha_scheduler import (
    _opened_dual_contracts,
    schedule_strategy_alpha_prospective_episodes,
    strategy_alpha_issuance_blockers,
    strategy_alpha_issuance_vetoes,
)
from ztare.investment.strategy_dual_outcome import compile_strategy_dual_outcome_episodes
from ztare.investment.strategy_learning import (
    STRATEGY_MOVE_LIBRARY_SCHEMA,
    STRATEGY_PROGRAM_ADOPTION_RESULT_SCHEMA,
    compile_strategy_program_adoption_result,
    compile_strategy_program_outcome_plan,
    candidate_bound_strategy_move,
    compatible_strategy_source_request_sha256s,
    covered_strategy_source_request_sha256s,
    due_strategy_program_adoption_requests,
    strategy_choice_admission_status,
)
from ztare.investment.strategy_options import RESULT_SCHEMA


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def test_only_current_abi_strategy_episodes_block_new_issuance():
    episodes = [
        {"run_id": "legacy", "entity_id": "OLD", "settled": False,
         "compatibility_abi": "legacy_nomination"},
        {"run_id": "current", "entity_id": "CURRENT", "settled": False,
         "opened_at": "2026-08-01T00:00:00Z",
         "scheduled_exit_at": "2026-09-01T00:00:00Z",
         "compatibility_abi": "dual_outcome_contract"},
        {"run_id": "settled", "entity_id": "DONE", "settled": True,
         "compatibility_abi": "dual_outcome_contract"},
    ]

    assert [row["run_id"] for row in strategy_alpha_issuance_blockers(episodes)] == [
        "current"
    ]
    assert strategy_alpha_issuance_vetoes(
        episodes, proposed_entity_id="CURRENT", proposed_at="2026-08-01T12:00:00Z",
    )
    assert not strategy_alpha_issuance_vetoes(
        episodes, proposed_entity_id="ANOTHER", proposed_at="2026-08-01T12:00:00Z",
    )
    full_cohort = episodes + [
        {"run_id": f"current-{index}", "entity_id": f"E{index}", "settled": False,
         "opened_at": "2026-08-01T00:00:00Z",
         "scheduled_exit_at": "2026-09-01T00:00:00Z",
         "compatibility_abi": "dual_outcome_contract"}
        for index in range(7)
    ]
    assert strategy_alpha_issuance_vetoes(
        full_cohort, proposed_entity_id="NINTH", proposed_at="2026-08-01T12:00:00Z",
    )
    assert strategy_alpha_issuance_vetoes(
        episodes, proposed_entity_id="LATE", proposed_at="2026-08-03T00:00:00Z",
    )


def test_price_epoch_can_reuse_only_the_same_hashed_business_basis(tmp_path) -> None:
    def request(leaf, candidate_sha, material_sha):
        basis = {
            "schema": "jaggedthoughts-qualitative-research-basis-v1",
            "candidate_id": "equity:ACME", "entity_id": "ACME",
            "entity_kind": "public_equity", "material_sources": [material_sha],
        }
        body = {
            "schema": "jaggedthoughts-agent-research-request-v1",
            "candidate_id": "equity:ACME", "candidate_leaf": leaf,
            "candidate_sha256": candidate_sha,
            "entity_id": "ACME", "entity_kind": "public_equity",
            "qualitative_research_basis": basis,
            "qualitative_research_basis_sha256": stable_sha256(basis),
        }
        return {**body, "request_sha256": stable_sha256(body)}

    old = request("a" * 64, "b" * 64, "same-business-source")
    current = request("d" * 64, "e" * 64, "same-business-source")
    rival = request("f" * 64, "0" * 64, "changed-business-source")
    for row in (old, current, rival):
        _write(tmp_path / "research_jobs" / "requests" / f"{row['request_sha256']}.json", row)
    compatible = compatible_strategy_source_request_sha256s(
        tmp_path, candidate_id="equity:ACME", candidate_leaf="d" * 64,
        candidate_sha256="e" * 64,
    )
    move = {
        "candidate_leaf": "a" * 64, "candidate_sha256": "b" * 64,
        "source_request_sha256": old["request_sha256"],
        "source_dossier_sha256": "2" * 64,
        "strategy_frontier_request_sha256": "3" * 64,
    }
    assert old["request_sha256"] in compatible
    assert rival["request_sha256"] not in compatible
    assert candidate_bound_strategy_move(
        move, candidate_leaf="d" * 64, candidate_sha256="e" * 64,
        compatible_source_request_sha256s=compatible,
    )
    forged = {**current, "schema": "invented-request"}
    forged["request_sha256"] = stable_sha256({
        key: value for key, value in forged.items() if key != "request_sha256"
    })
    _write(tmp_path / "research_jobs" / "requests" / "forged.json", forged)
    assert compatible_strategy_source_request_sha256s(
        tmp_path, candidate_id="equity:ACME", candidate_leaf="d" * 64,
        candidate_sha256="e" * 64,
    ) == compatible
    ambiguous = request("d" * 64, "e" * 64, "conflicting-current-source")
    _write(tmp_path / "research_jobs" / "requests" / "ambiguous.json", ambiguous)
    assert not compatible_strategy_source_request_sha256s(
        tmp_path, candidate_id="equity:ACME", candidate_leaf="d" * 64,
        candidate_sha256="e" * 64,
    )


def test_covered_candidate_epoch_resolves_its_admissible_dossier_request(tmp_path) -> None:
    (tmp_path / "workspace.yaml").write_text(
        "owner: operator\ngolden_store: state/golden.sqlite3\n", encoding="utf-8",
    )
    store = GoldenStore(tmp_path / "state" / "golden.sqlite3")
    dossier = GoldenLeaf(
        owner="operator", object_kind="candidate_research_dossier", object_id="dossier",
        epoch="d" * 64, occurred_at="2026-08-01T00:00:00Z",
        available_at="2026-08-01T00:00:00Z",
        payload={"schema": "test-dossier-v1", "request_sha256": "a" * 64},
        source_refs=("issuer",),
    )
    dossier_leaf = store.append_leaf(dossier)
    candidate_leaf = "b" * 64
    store.append_leaf(GoldenLeaf(
        owner="operator", object_kind="research_evidence_coverage",
        object_id=f"research-coverage:{candidate_leaf}", epoch="c" * 64,
        occurred_at="2026-08-02T00:00:00Z", available_at="2026-08-02T00:00:00Z",
        payload={"schema": "test-coverage-v1", "covered": True,
                 "candidate_leaf": candidate_leaf,
                 "prior_dossier_leaf": dossier_leaf}, source_refs=("monitor",),
    ))

    assert covered_strategy_source_request_sha256s(
        tmp_path, candidate_leaf=candidate_leaf,
    ) == frozenset({"a" * 64})
    currency = _strategy_frontier_currency(tmp_path, {
        "candidate_id": "equity:ACME", "candidate_leaf": "old",
        "candidate_sha256": "old", "entity_id": "ACME",
        "entity_kind": "public_equity", "research_population": "strategy_learning",
        "candidate_epoch_relation": "monitored_dossier_coverage",
        "source_request_sha256": "a" * 64,
        "candidate_coverage_leaf": next(iter(store.list_leaves(
            object_kind="research_evidence_coverage",
        )))["leaf_sha256"],
    }, {"equity:ACME": {
        "candidate_leaf": candidate_leaf, "candidate_sha256": "e" * 64,
        "entity_id": "ACME", "entity_kind": "public_equity", "screen_status": "monitor",
    }})
    assert currency["admissible"] and currency["covered_successor"]


def test_strategy_choice_continuity_requires_hashed_adjacent_chronology() -> None:
    frontiers = ("a" * 64, "b" * 64, "c" * 64)
    choice = "d" * 64
    epochs = (
        "2026-01-01T00:00:00Z", "2026-02-01T00:00:00Z",
        "2026-03-01T00:00:00Z",
    )
    moves = [{
        "entity_id": "ACME", "option_id": "choice", "evidence_epoch": epoch,
        "strategy_frontier_sha256": frontier,
        "strategy_choice_identity_sha256": choice,
    } for frontier, epoch in zip(frontiers, epochs, strict=True)]

    def edge(index):
        body = {
            "entity_id": "ACME", "earlier_evidence_epoch": epochs[index],
            "later_evidence_epoch": epochs[index + 1],
            "earlier_strategy_frontier_sha256": frontiers[index],
            "later_strategy_frontier_sha256": frontiers[index + 1],
            "strategy_choice_continuity": [{
                "option_id": "choice", "status": "preserved",
                "earlier_strategy_choice_identity_sha256": choice,
                "later_strategy_choice_identity_sha256": choice,
            }],
        }
        return {**body, "evolution_sha256": stable_sha256(body)}

    library = {"moves": moves, "frontier_evolution": [edge(0), edge(1)]}
    assert strategy_choice_admission_status(
        library, moves[0], as_of="2026-03-01T00:00:00Z",
    ) == "preserved_to_current_frontier"
    assert strategy_choice_admission_status(
        library, moves[0], as_of="2026-01-15T00:00:00Z",
    ) == "current_frontier_frozen"
    bad_hash = {**library, "frontier_evolution": [{**edge(0), "evolution_sha256": "0" * 64}, edge(1)]}
    assert strategy_choice_admission_status(bad_hash, moves[0]) is None
    reversed_edge = edge(0)
    reversed_edge.update({
        "earlier_evidence_epoch": epochs[1], "later_evidence_epoch": epochs[0],
    })
    reversed_edge["evolution_sha256"] = stable_sha256({
        key: value for key, value in reversed_edge.items() if key != "evolution_sha256"
    })
    assert strategy_choice_admission_status(
        {**library, "frontier_evolution": [reversed_edge, edge(1)]}, moves[0],
    ) is None
    assert strategy_choice_admission_status(
        {**library, "frontier_evolution": [edge(1)]}, moves[0],
    ) is None


def test_exact_phenotype_gets_zero_weight_experiment_slot_without_reranking(
    tmp_path, monkeypatch,
) -> None:
    opened_at = "2026-08-12T12:00:00Z"
    (tmp_path / "workspace.yaml").write_text(
        "owner: operator-paper-book\ngolden_store: state/golden.sqlite3\n",
        encoding="utf-8",
    )
    quality_body = {
        "schema": "jaggedthoughts-company-quality-report-v1",
        "entity_id": "ACME", "as_of": "2026-08-12T11:00:00Z",
        "available_at": "2026-08-11T12:00:00Z",
        "coverage": {}, "metrics": {}, "scores": {}, "source_refs": ["filing:ACME"],
    }
    quality = {
        **quality_body, "quality_report_sha256": stable_sha256(quality_body),
    }
    _write(tmp_path / "quality" / "acme.json", quality)
    factor_body = {
        "schema": "jaggedthoughts-factor-analysis-v1",
        "analysis_id": "acme-market-beta", "candidate_entity_id": "ACME",
        "available_at": "2026-08-11T01:00:00Z",
        "factors": [{"factor_id": "market", "long_entity_id": "SPY",
                     "short_entity_id": "", "expected_annual_premium": 0.0}],
        "coefficients": {"betas": {"market": 1.0}},
        "source_refs": ["price:ACME", "price:SPY"],
    }
    candidate_body = {
        "schema": "jaggedthoughts-discovery-candidate-v1",
        "candidate_id": "equity:ACME", "entity_id": "ACME", "name": "Acme",
        "entity_kind": "public_equity", "screen_status": "monitor",
        "as_of": "2026-08-12T11:00:00Z", "rank": 47, "rank_score": 0.01,
        "quality_report_sha256": quality["quality_report_sha256"],
        "beta_receipt": {"status": "estimated", "analysis": {
            **factor_body, "analysis_sha256": stable_sha256(factor_body),
        }},
        "valuation": {"summary": {"price_implied_excess_return": -0.02}},
        "metrics": {"price_implied_excess_return": -0.02},
        "source_refs": ["discovery:ACME"],
    }
    candidate = {**candidate_body, "candidate_sha256": stable_sha256(candidate_body)}
    store_path = tmp_path / "state" / "golden.sqlite3"
    leaf = GoldenLeaf(
        owner="operator-paper-book", object_kind="discovery_candidate",
        object_id="equity:ACME", epoch=candidate["candidate_sha256"],
        occurred_at="2026-08-12T11:00:00Z", available_at="2026-08-12T11:30:00Z",
        payload=candidate, source_refs=("discovery:ACME",),
    )
    leaf_sha = GoldenStore(store_path).append_leaf(leaf)
    discovery_body = {
        "schema": "jaggedthoughts-discovery-run-v1",
        "run_id": "discovery-1", "candidates": [candidate], "capital_authority": False,
    }
    discovery = {**discovery_body, "run_sha256": stable_sha256(discovery_body)}
    _write(tmp_path / "discovery" / "latest.json", discovery)
    _write(tmp_path / "discovery" / "latest_record.json", {
        "run_id": discovery["run_id"], "run_sha256": discovery["run_sha256"],
        "candidate_leaves": {"equity:ACME": leaf_sha},
    })
    phenotype_sha = "b" * 64
    operating_contract = {
        "contract_sha256": "c" * 64,
        "metric_id": "owner_earnings_margin",
        "unit": "decimal",
        "direction": "increase",
        "minimum_effect": 0.05,
        "comparator": "pre_move_baseline",
        "measurement_start_at": "2026-08-10T00:00:00Z",
        "due_at": "2027-08-10T00:00:00Z",
        "evidence_refs": ["issuer:metric-definition"],
    }
    event_body = {
        "treatment_timing_status": "exact_adoption_event",
        "available_at": "2026-08-10T00:00:00Z",
        "source_refs": ["issuer:event"],
    }
    event = {**event_body, "implementation_event_sha256": stable_sha256(event_body)}
    choice_sha = "d" * 64
    library_body = {
        "schema": "jaggedthoughts-strategy-move-library-v1",
        "mechanism_phenotypes": [{
            "mechanism_phenotype_sha256": phenotype_sha,
            "exact_adoption_count": 1, "entity_ids": ["ACME"],
        }],
        "moves": [{
            "entity_id": "ACME", "mechanism_phenotype_sha256": phenotype_sha,
            "candidate_leaf": leaf_sha,
            "candidate_sha256": candidate["candidate_sha256"],
            "source_request_sha256": "1" * 64,
            "source_dossier_sha256": "2" * 64,
                "strategy_frontier_request_sha256": "3" * 64,
                "strategy_frontier_sha256": "4" * 64,
                "evidence_epoch": "2026-08-10T00:00:00Z",
                "strategy_choice_identity_sha256": choice_sha,
            "strategy_program_attribution": {
                "strategy_frontier_sha256": "4" * 64,
                "frontier_program_ids": ["frontier-program-1"],
                "local_peak_program_ids": ["frontier-program-1"],
                "scope_closed": True, "decision_closed": False,
                "status": "option_event_does_not_establish_integrated_program",
                "program_adoption_evidence_required": True,
                "recursive_frontier_credit_eligible": False,
            },
            "move_sha256": "e" * 64, "implementation_event": event,
            "outcome_contracts": [operating_contract], "outcome_episodes": [],
        }],
        "frontier_evolution": [{
            "entity_id": "ACME",
            "later_strategy_frontier_sha256": "4" * 64,
            "strategy_choice_continuity": [{
                "option_id": "durable-choice",
                "later_strategy_choice_identity_sha256": choice_sha,
                "status": "preserved",
            }],
        }],
        "capital_authority": False,
    }
    _write(tmp_path / "institutional_learning" / "strategy_moves" / "latest.json", {
        **library_body, "library_sha256": stable_sha256(library_body),
    })
    observations = tmp_path / "data" / "observations.csv"
    observations.parent.mkdir(parents=True)
    with observations.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "observation_id", "entity_id", "metric_id", "value",
            "observed_at", "available_at", "source_ref",
        ])
        writer.writeheader()
        for entity_id, value, observed_at in (
                ("ACME", 100, "2026-08-11T00:00:00Z"),
                ("SPY", 500, "2026-08-11T00:00:00Z"),
                ("ACME", 100, "2026-08-13T00:00:00Z"),
                ("SPY", 500, "2026-08-13T00:00:00Z"),
                ("ACME", 110, "2026-09-03T00:00:00Z"),
                ("SPY", 515, "2026-09-03T00:00:00Z"),
        ):
            writer.writerow({
                "observation_id": f"{entity_id}-price-{observed_at[:10]}", "entity_id": entity_id,
                    "metric_id": "adjusted_price", "value": value,
                "observed_at": observed_at,
                "available_at": observed_at,
                "source_ref": f"price:{entity_id}",
            })

    policy = {"forecast_windows": [{"horizon_days": 21, "cadence_days": 21}]}
    base = [{"entity_id": "BASE", "horizon_days": 21, "rank": 1}]
    schedule = schedule_strategy_alpha_prospective_episodes(
        tmp_path, base_windows=base, policy=policy, budget=2, evaluated_at=opened_at,
    )
    nomination = schedule["scheduled_windows"][1]
    dual = nomination["strategy_experiment_nomination"]["dual_outcome_contract"]

    assert [row["entity_id"] for row in schedule["scheduled_windows"]] == ["BASE", "ACME"]
    assert schedule["eligibility"][0]["strategy_learning_population_eligible"] is True
    assert schedule["eligibility"][0]["capital_activation_eligible"] is False
    assert nomination["rank"] == 47 and nomination["portfolio_weight"] == 0.0
    assert dual["move_sha256"] == "e" * 64
    assert dual["candidate_leaf"] == leaf_sha
    assert dual["candidate_sha256"] == candidate["candidate_sha256"]
    assert dual["operating_outcome"]["contract_sha256"] == "c" * 64
    assert dual["tested_strategy_object"] == "exact_option_phenotype"
    assert dual["strategy_program_attribution"]["recursive_frontier_credit_eligible"] is False
    assert dual["security_outcome"]["control"]["kind"] == "frozen_factor_beta_vector"
    assert dual["direct_research_priority_adjustment"] == 0.0
    assert dual["capital_authority"] is False
    assert schedule["rank_changed"] is False

    duplicate_body = {**candidate_body, "candidate_id": "equity:ACME:duplicate"}
    duplicate = {
        **duplicate_body, "candidate_sha256": stable_sha256(duplicate_body),
    }
    ambiguous_body = {**discovery_body, "candidates": [candidate, duplicate]}
    ambiguous_discovery = {
        **ambiguous_body, "run_sha256": stable_sha256(ambiguous_body),
    }
    _write(tmp_path / "discovery" / "latest.json", ambiguous_discovery)
    _write(tmp_path / "discovery" / "latest_record.json", {
        "run_id": ambiguous_discovery["run_id"],
        "run_sha256": ambiguous_discovery["run_sha256"],
        "candidate_leaves": {"equity:ACME": leaf_sha},
    })
    ambiguous_schedule = schedule_strategy_alpha_prospective_episodes(
        tmp_path, base_windows=base, policy=policy, budget=2, evaluated_at=opened_at,
    )
    assert [row["entity_id"] for row in ambiguous_schedule["scheduled_windows"]] == ["BASE"]
    assert {row["code"] for row in ambiguous_schedule["global_gaps"]} == {
        "discovery_entity_candidate_ambiguous",
    }
    _write(tmp_path / "discovery" / "latest.json", discovery)
    _write(tmp_path / "discovery" / "latest_record.json", {
        "run_id": discovery["run_id"], "run_sha256": discovery["run_sha256"],
        "candidate_leaves": {"equity:ACME": leaf_sha},
    })

    # The same ticker and event cannot activate from another candidate epoch.
    library_body["moves"][0]["candidate_sha256"] = "f" * 64
    _write(tmp_path / "institutional_learning" / "strategy_moves" / "latest.json", {
        **library_body, "library_sha256": stable_sha256(library_body),
    })
    blocked = schedule_strategy_alpha_prospective_episodes(
        tmp_path, base_windows=base, policy=policy, budget=2, evaluated_at=opened_at,
    )
    assert [row["entity_id"] for row in blocked["scheduled_windows"]] == ["BASE"]
    library_body["moves"][0]["candidate_sha256"] = candidate["candidate_sha256"]

    # Adding a later outcome cannot rewrite the contract frozen at issue time.
    library_body["moves"][0]["outcome_episodes"] = [{"episode_sha256": "o" * 64}]
    _write(tmp_path / "institutional_learning" / "strategy_moves" / "latest.json", {
        **library_body, "library_sha256": stable_sha256(library_body),
    })
    replay = schedule_strategy_alpha_prospective_episodes(
        tmp_path, base_windows=base, policy=policy, budget=2, evaluated_at=opened_at,
    )
    replay_dual = replay["scheduled_windows"][1][
        "strategy_experiment_nomination"
    ]["dual_outcome_contract"]
    assert replay_dual == dual

    monkeypatch.setattr(closed_book, "_utc_now", lambda: opened_at)
    monkeypatch.setattr(closed_book, "subscription_runtime_version", lambda runtime: "test")
    run = closed_book.open_closed_book_forecast(
        tmp_path, owner="operator-paper-book", store_path=store_path,
        candidate_leaf=leaf_sha, horizon_days=21, agent_result={},
        strategy_experiment_nomination=nomination["strategy_experiment_nomination"],
    )
    assert run["evidence_packet"]["discovery_summary"]["rank"] == 47
    assert run["evidence_packet"]["discovery_summary"][
        "strategy_experiment_nomination"
    ]["dual_outcome_contract"] == dual
    assert run["evidence_packet"]["decision_summary"]["target_weight"] == 0.0
    assert all(row["target_weight"] == 0.0 for row in run["candidate_forecasts"])
    replayed_run = closed_book.open_closed_book_forecast(
        tmp_path, owner="operator-paper-book", store_path=store_path,
        candidate_leaf=leaf_sha, horizon_days=21, agent_result={},
        strategy_experiment_nomination=nomination[
            "strategy_experiment_nomination"
        ],
    )
    assert replayed_run["replayed"] is True
    assert replayed_run["run_id"] == run["run_id"]
    episode_key = dual["dual_outcome_episode_key_sha256"]
    assert _opened_dual_contracts(tmp_path) == {episode_key}
    waiting = schedule_strategy_alpha_prospective_episodes(
        tmp_path, base_windows=base, policy=policy, budget=2,
        evaluated_at="2026-08-12T12:01:00Z",
    )
    assert [row["entity_id"] for row in waiting["scheduled_windows"]] == ["BASE"]
    assert waiting["experiment_issuance_status"] == "awaiting_eligible_strategy_source"
    assert waiting["experiment_not_before"] is None
    forged_run = copy.deepcopy(run)
    forged_run["run_id"] = "forged-run"
    forged_packet = forged_run["evidence_packet"]
    forged_nomination = forged_packet["discovery_summary"][
        "strategy_experiment_nomination"
    ]
    forged_dual = forged_nomination["dual_outcome_contract"]
    forged_dual["candidate_leaf"] = "f" * 64
    forged_dual["dual_outcome_episode_key_sha256"] = stable_sha256({
        "entity_id": forged_dual["entity_id"],
        "candidate_leaf": forged_dual["candidate_leaf"],
        "candidate_sha256": forged_dual["candidate_sha256"],
        "move_sha256": forged_dual["move_sha256"],
        "strategy_choice_identity_sha256": forged_dual[
            "strategy_choice_identity_sha256"
        ],
        "mechanism_phenotype_sha256": forged_dual["mechanism_phenotype_sha256"],
        "implementation_event_sha256": forged_dual["implementation_event_sha256"],
        "operating_contract_sha256": forged_dual["operating_outcome"]["contract_sha256"],
        "security_horizon_days": forged_dual["security_outcome"]["horizon_days"],
        "benchmark_entity_id": forged_dual["security_outcome"]["control"][
            "benchmark_entity_id"
        ],
    })
    forged_dual.pop("dual_outcome_contract_sha256")
    forged_dual["dual_outcome_contract_sha256"] = stable_sha256(forged_dual)
    forged_nomination.pop("nomination_sha256")
    forged_nomination["nomination_sha256"] = stable_sha256(forged_nomination)
    forged_packet.pop("packet_sha256")
    forged_packet["packet_sha256"] = stable_sha256(forged_packet)
    forged_run.pop("run_sha256")
    forged_run["run_sha256"] = stable_sha256(forged_run)
    replay_probe = tmp_path / "replay-probe"
    _write(replay_probe / "closed_book" / "runs" / "forged-run.json", forged_run)
    assert not _opened_dual_contracts(replay_probe)
    monkeypatch.setattr(closed_book, "_utc_now", lambda: "2026-09-03T00:00:01Z")
    settled = closed_book.settle_due_closed_book_forecasts(
        tmp_path, owner="operator-paper-book", store_path=store_path,
        as_of="2026-09-03T00:00:00Z",
    )
    assert settled["settled_count"] == 1
    with pytest.raises(ValueError, match="episode identity was already opened"):
        closed_book.open_closed_book_forecast(
            tmp_path, owner="operator-paper-book", store_path=store_path,
            candidate_leaf=leaf_sha, horizon_days=21, agent_result={},
            strategy_experiment_nomination=nomination[
                "strategy_experiment_nomination"
            ],
        )
    library_body["moves"][0]["outcome_episodes"] = [{
        "episode_sha256": "o" * 64, "contract_sha256": "c" * 64,
    }]
    _write(tmp_path / "institutional_learning" / "strategy_moves" / "latest.json", {
        **library_body, "library_sha256": stable_sha256(library_body),
    })
    joined = compile_strategy_dual_outcome_episodes(tmp_path)
    episode = joined["episodes"][0]
    assert episode["joint_status"] == "settled"
    assert episode["security_outcome"]["actual"]["factor_controlled_return"] == pytest.approx(
        0.06986007
    )
    assert episode["direct_research_priority_adjustment"] == 0.0
    assert joined["pending_count"] == 0
    assert joined["settled_count"] == 1
    assert joined["status"] == "settled"
    assert joined["current_episode"]["dual_outcome_contract_sha256"] == dual[
        "dual_outcome_contract_sha256"
    ]
    assert "promotion gates" in joined["next_activation"]


def test_capital_cycle_hook_passes_the_typed_nomination(tmp_path, monkeypatch) -> None:
    nomination = {"schema": "jaggedthoughts-strategy-alpha-episode-nomination-v1"}
    seen = {}

    def open_forecast(*args, **kwargs):
        seen.update(kwargs)
        return {"run_id": "run-1", "run_sha256": "r" * 64, "provider": {}, "ok": True}

    monkeypatch.setattr(workspace, "open_closed_book_forecast", open_forecast)
    monkeypatch.setattr(
        workspace, "process_strategy_alpha_issuance_actions",
        lambda *args, **kwargs: {"capital_authority": False},
    )
    row = workspace._open_capital_cycle_forecast(
        tmp_path,
        owner="paper",
        store_path=tmp_path / "store.sqlite3",
        policy={"discovery_benchmark_id": "SPY", "discovery_probe_weight": 0.05},
        window={
            "candidate_leaf": "leaf", "decision_id": None, "horizon_days": 21,
            "strategy_experiment_nomination": nomination,
        },
    )

    assert seen["strategy_experiment_nomination"] == nomination
    assert row["strategy_alpha_issuance"]["capital_authority"] is False


def test_integrated_program_requires_every_constituent_and_joint_source() -> None:
    frontier_sha, p1, p2, base = "a" * 64, "b" * 64, "c" * 64, "f" * 64
    options = ["fabric", "switch", "capacity", "portfolio"]
    exact = {option: "d" * 63 + str(index) for index, option in enumerate(options[:2])}
    outcome_body = {
        "metric_id": "owner_earnings_margin", "unit": "decimal",
        "direction": "increase", "minimum_effect": 0.01,
        "horizon_days": 730, "comparator": "pre_move_baseline",
        "measurement_start_at": "2026-07-01T00:00:00Z",
        "due_at": "2028-06-30T00:00:00Z", "evidence_refs": ["issuer"],
    }
    outcome_contract = {**outcome_body, "contract_sha256": stable_sha256(outcome_body)}
    library = {
        "schema": STRATEGY_MOVE_LIBRARY_SCHEMA,
        "moves": [{
            "strategy_frontier_sha256": frontier_sha, "option_id": option,
            "move_sha256": chr(101 + index) * 64,
            "causal_panel_status": "treatment_event_ready" if option in exact else "requires_adoption_event",
            "implementation_event": (
                {"implementation_event_sha256": exact[option], "source_refs": ["issuer"]}
                if option in exact else None
            ),
            "outcome_contracts": [outcome_contract] if option in options[:3] else [],
        } for index, option in enumerate(options)],
    }
    frontier = {
        "schema": RESULT_SCHEMA, "strategy_frontier_sha256": frontier_sha,
        "evidence_epoch": "2026-08-01T00:00:00Z",
        "company": {
            "id": "ACME", "candidate_leaf": "1" * 64,
            "candidate_sha256": "2" * 64, "source_dossier_sha256": "3" * 64,
        },
        "option_catalog": [
            {"option_id": option, "option_sha256": chr(107 + index) * 64}
            for index, option in enumerate(options)
        ],
        "frontier_programs": [
            {"program_id": p1, "expression": "combine(fabric,switch,capacity)",
             "unique_option_ids": options[:3], "evidence_refs": ["issuer"]},
            {"program_id": p2, "expression": "combine(fabric,switch,portfolio)",
             "unique_option_ids": [*options[:2], options[3]], "evidence_refs": ["issuer"]},
        ],
        "local_peak_programs": [],
        "neighborhood": {"edges": [{
            "base_program_id": base, "base_expression": "combine(fabric,switch)",
            "base_option_ids": options[:2], "target_program_id": p1,
            "added_option_id": "capacity",
            "target_is_frontier": True, "target_is_local_peak": False,
        }]},
    }
    request = due_strategy_program_adoption_requests(
        library, [frontier], as_of="2026-08-23T00:00:00Z",
    )[0]
    assert request["candidate_program_set_sha256"] == stable_sha256(
        request["candidate_programs"]
    )
    assert request["common_option_ids"] == options[:2]
    by_id = {row["program_id"]: row for row in request["candidate_programs"]}
    assert by_id[p1]["discriminating_option_ids"] == ["capacity"]
    assert by_id[base]["roles"] == ["one_choice_base"]
    source = "https://issuer.example/program"
    raw = {
        "schema": STRATEGY_PROGRAM_ADOPTION_RESULT_SCHEMA,
        "request_sha256": request["request_sha256"], "entity_id": "ACME",
        "classification": "exact_integrated_program_adoption",
        "selected_program_ids": [p1], "assessed_at": "2026-08-23T00:00:00Z",
        "coverage": {"sec_filings_searched": True, "issuer_materials_searched": True},
        "option_events": [{
            "option_id": option, "occurred_at": "2026-07-01T00:00:00Z",
            "available_at": "2026-07-02T00:00:00Z", "implementation_state": "operational",
            "source_urls": [source],
        } for option in options[:2]],
        "joint_execution_source_urls": [source],
        "sources": [{"url": source, "source_kind": "issuer",
                     "published_at": "2026-07-02T00:00:00Z", "supports": [
                         "coordinated_program", *[f"option:{option}" for option in options[:3]],
                     ]}],
        "rationale": "The issuer links the operating choices.", "residuals": [],
    }
    with pytest.raises(ValueError, match="every constituent"):
        compile_strategy_program_adoption_result(raw, request)
    raw["option_events"].append({**raw["option_events"][0], "option_id": "capacity"})
    result = compile_strategy_program_adoption_result(raw, request)
    assert result["program_adoption_evidence_eligible"] is True
    assert result["recursive_program_outcome_credit_eligible"] is False
    plan = compile_strategy_program_outcome_plan(result, request, library)
    assert plan["status"] == "prospective_readouts_frozen"
    assert plan["program_roles"] == ["global_frontier"]
    assert plan["readout_count"] == 1
    assert plan["readouts"][0]["supporting_option_ids"] == sorted(options[:3])
    assert plan["readouts"][0]["discriminating_option_ids"] == ["capacity"]
    assert plan["readouts"][0]["measurement_start_at"] == result["assessed_at"]
    assert plan["causal_program_credit_eligible"] is False
    base_raw = copy.deepcopy(raw)
    base_raw["selected_program_ids"] = [base]
    base_raw["option_events"] = base_raw["option_events"][:2]
    base_raw["sources"][0]["supports"] = [
        "coordinated_program", "option:fabric", "option:switch",
    ]
    base_result = compile_strategy_program_adoption_result(base_raw, request)
    base_plan = compile_strategy_program_outcome_plan(base_result, request, library)
    assert base_plan["status"] == "prospective_readouts_frozen"
    assert base_plan["program_roles"] == ["one_choice_base"]
    assert base_plan["discriminating_absence_option_ids"] == ["capacity"]
    library["moves"][2]["outcome_contracts"] = []
    spine_only = compile_strategy_program_outcome_plan(result, request, library)
    assert spine_only["status"] == "missing_program_discriminating_outcome_contract"
    frontier["frontier_programs"] = frontier["frontier_programs"][:1]
    one_choice_due = due_strategy_program_adoption_requests(
        library, [frontier], as_of="2026-08-23T00:00:00Z",
    )[0]
    assert {row["program_id"] for row in one_choice_due["candidate_programs"]} == {p1, base}
    frontier["neighborhood"] = {"edges": []}
    assert due_strategy_program_adoption_requests(library, [frontier], as_of="2026-08-23T00:00:00Z") == []
