import csv
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from threading import Event, Lock, get_ident

import pytest

from ztare.common.equivariance import stable_sha256
from ztare.investment import closed_book as subject
from ztare.investment.golden_store import GoldenLeaf, GoldenStore


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_concurrent_open_reuses_one_semantic_episode(tmp_path: Path, monkeypatch) -> None:
    times, time_lock = {}, Lock()
    first_entered, second_entered, release = Event(), Event(), Event()
    calls, call_lock = 0, Lock()

    def now() -> str:
        with time_lock:
            slot = times.setdefault(get_ident(), len(times) + 1)
        return f"2026-08-23T00:00:{slot:02d}Z"

    def packet(*_args, opened_at: str, horizon_days: int, **_kwargs) -> dict:
        body = {
            "schema": "jaggedthoughts-closed-book-evidence-packet-v1",
            "opened_at": opened_at, "end_at": "2026-11-21T00:00:00Z",
            "horizon_days": horizon_days,
            "subject": {"kind": "paper_decision", "subject_id": "same",
                        "subject_sha256": "s" * 64},
            "entity": {"entity_id": "ACME", "entity_kind": "public_equity"},
            "benchmark": {"entity_id": "SPY"},
            "valuation_summary": {}, "decision_summary": {},
            "starting_market": {}, "discovery_summary": {},
            "field_availability": {"rows": []}, "evidence_archive": {},
        }
        return {**body, "packet_sha256": stable_sha256(body)}

    class BlockingRole:
        provider_call_count = 1

        def __init__(self, **_kwargs) -> None:
            pass

        def __call__(self, _prompt: str) -> dict:
            nonlocal calls
            with call_lock:
                calls += 1
                ordinal = calls
            (first_entered if ordinal == 1 else second_entered).set()
            if ordinal == 1:
                assert release.wait(5)
            raise RuntimeError("forecast intentionally unavailable")

    monkeypatch.setattr(subject, "_utc_now", now)
    monkeypatch.setattr(subject, "latest_operator_decision", lambda *_args: (
        tmp_path / "decisions" / "same.json", {"decision_id": "same"},
    ))
    monkeypatch.setattr(subject, "_evidence_packet", packet)
    monkeypatch.setattr(subject, "SubscriptionJSONRole", BlockingRole)
    monkeypatch.setattr(subject, "subscription_runtime_version", lambda _runtime: "test")

    def open_once() -> dict:
        return subject.open_closed_book_forecast(
            tmp_path, owner="paper", store_path=tmp_path / "state" / "golden.sqlite3",
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(open_once)
        assert first_entered.wait(5)
        second = pool.submit(open_once)
        raced_into_provider = second_entered.wait(0.2)
        release.set()
        left, right = first.result(timeout=5), second.result(timeout=5)

    assert raced_into_provider is False
    assert calls == 1
    assert left["run_id"] == right["run_id"]
    assert len(list((tmp_path / "closed_book" / "runs").glob("*.json"))) == 1
    kept, excluded = subject._canonical_episode_runs([
        left, {**left, "run_id": "later-race", "opened_at": "2026-08-23T00:01:00Z"},
    ])
    assert ([row["run_id"] for row in kept], excluded) == (
        [left["run_id"]], {"later-race": left["run_id"]},
    )


def test_prospective_block_is_frozen_deduplicated_and_settled(
    tmp_path: Path, monkeypatch,
) -> None:
    opened_at = "2026-08-10T12:00:00Z"
    decision = {
        "schema": "jaggedthoughts-investment-decision-v1",
        "decision_id": "acme-value-20260810",
        "decision_record_sha256": "d" * 64,
        "as_of": "2026-08-10T11:00:00Z",
        "profile_lifecycle": {"data_class": "operator"},
        "entity": {"entity_id": "ACME", "name": "Acme"},
        "benchmark": {"entity_id": "SPY", "name": "Benchmark"},
        "valuation_envelope": {"summary": {"price_implied_excess_return": 0.08}},
        "summary": {
            "selected_action_id": "buy-small", "target_weight": 0.10,
            "underwriting_hurdle_rate": 0.12, "representation_status": "complete",
            "scope_closed": True, "decision_closed": False,
        },
    }
    _write_json(tmp_path / "decisions" / "acme.json", decision)
    _write_json(tmp_path / "quality" / "acme.json", {
        "schema": "jaggedthoughts-company-quality-report-v1",
        "quality_report_sha256": "q" * 64,
        "as_of": "2026-08-09T00:00:00Z",
        "available_at": "2026-08-09T12:00:00Z",
        "coverage": {"years": 5}, "metrics": {"owner_earnings_cagr": 0.06},
        "scores": {"durability": 0.7}, "source_refs": ["filing:acme"],
    })
    observations = tmp_path / "data" / "observations.csv"
    observations.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        ("acme-old", "ACME", 80, "2026-02-09T00:00:00Z", "2026-02-09T01:00:00Z"),
        ("spy-old", "SPY", 400, "2026-02-09T00:00:00Z", "2026-02-09T01:00:00Z"),
        ("acme-open", "ACME", 100, "2026-08-09T00:00:00Z", "2026-08-09T01:00:00Z"),
        ("spy-open", "SPY", 500, "2026-08-09T00:00:00Z", "2026-08-09T01:00:00Z"),
        ("acme-entry", "ACME", 100, "2026-08-11T00:00:00Z", "2026-08-11T01:00:00Z"),
        ("spy-entry", "SPY", 500, "2026-08-11T00:00:00Z", "2026-08-11T01:00:00Z"),
        ("acme-end", "ACME", 112, "2026-11-09T00:00:00Z", "2026-11-09T01:00:00Z"),
        ("spy-end", "SPY", 525, "2026-11-09T00:00:00Z", "2026-11-09T01:00:00Z"),
    ]
    with observations.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=[
            "observation_id", "entity_id", "metric_id", "value",
            "observed_at", "available_at", "source_ref",
        ])
        writer.writeheader()
        for observation_id, entity_id, value, observed, available in rows:
            writer.writerow({
                "observation_id": observation_id, "entity_id": entity_id,
                "metric_id": "adjusted_price", "value": value, "observed_at": observed,
                "available_at": available, "source_ref": f"cached:{observation_id}",
            })

    monkeypatch.setattr(subject, "_utc_now", lambda: opened_at)
    monkeypatch.setattr(subject, "subscription_runtime_version", lambda runtime: "codex-test")
    packet = subject._evidence_packet(
        tmp_path, decision, opened_at=opened_at, horizon_days=90,
    )
    other_entity = {**packet, "entity": {"entity_id": "OTHER"}, "decision_record_sha256": "e" * 64}
    assert subject._episode_identity(other_entity) != subject._episode_identity(packet)
    assert subject._inference_block_identity(other_entity) == subject._inference_block_identity(packet)
    agent_result = {
        "schema": "jaggedthoughts-closed-book-agent-forecast-v1",
        "packet_sha256": packet["packet_sha256"],
        "expected_active_return": 0.04,
        "underperformance_probability": 0.35,
        "target_weight": 0.08,
        "mechanism_summary": "Durable cash generation exceeds the implied hurdle.",
        "strongest_rival": "The market has already capitalized the quality spread.",
        "falsifier": "Owner earnings fall while the benchmark expands.",
    }
    store_path = tmp_path / "state" / "golden.sqlite3"
    run = subject.open_closed_book_forecast(
        tmp_path, owner="paper", store_path=store_path, horizon_days=90,
        agent_result=agent_result,
    )
    replay = subject.open_closed_book_forecast(
        tmp_path, owner="paper", store_path=store_path, horizon_days=90,
        agent_result=agent_result,
    )
    assert len(run["candidate_forecasts"]) == 4
    assert run["settlement_contract"]["prospective_return_window"]["sealed_at"] == opened_at
    assert run["temporal_integrity"]["prospective_engine_evidence_eligible"] is True
    assert run["evidence_packet"]["evidence_archive"]["status"] == "archive_unavailable"
    assert replay["replayed"] is True
    assert replay["run_id"] == run["run_id"]

    candidate_body = {
        "schema": "jaggedthoughts-discovery-candidate-v1",
        "candidate_id": "equity:ACME",
        "entity_id": "ACME",
        "name": "Acme",
        "entity_kind": "public_equity",
        "screen_status": "qualified",
        "as_of": "2026-08-10T11:00:00Z",
        "rank": 1,
        "rank_score": 0.9,
        "quality_report_sha256": "q" * 64,
        "valuation": {
            "summary": {"price_implied_excess_return": 0.08},
            "expectations_frontier": {"scope_closed": True},
        },
        "metrics": {"price_implied_excess_return": 0.08},
        "criteria": ["positive_price_implied_excess_return"],
        "source_refs": ["discovery:acme"],
    }
    candidate_sha = stable_sha256(candidate_body)
    candidate_leaf = GoldenLeaf(
        owner="paper", object_kind="discovery_candidate", object_id="equity:ACME",
        epoch=candidate_sha, occurred_at="2026-08-10T11:00:00Z",
        available_at="2026-08-10T11:30:00Z",
        payload={**candidate_body, "candidate_sha256": candidate_sha},
        source_refs=("discovery:acme",),
    )
    candidate_leaf_sha = GoldenStore(store_path).append_leaf(candidate_leaf)
    discovery_packet = subject._discovery_evidence_packet(
        tmp_path, candidate_leaf.payload, candidate_leaf=candidate_leaf_sha,
        opened_at=opened_at, horizon_days=90, benchmark_id="SPY", probe_weight=0.05,
        candidate_available_at=candidate_leaf.available_at,
    )
    dossier = GoldenLeaf(
        owner="paper", object_kind="candidate_research_dossier",
        object_id=f"research:ACME:{candidate_leaf_sha}", epoch="dossier",
        occurred_at="2026-08-10T11:35:00Z", available_at="2026-08-10T11:35:00Z",
        payload={
            "schema": "jaggedthoughts-candidate-research-dossier-v1",
            "entity_id": "ACME", "candidate_leaf": candidate_leaf_sha,
            "dossier_sha256": "r" * 64,
            "strategy": {"choices": [{"id": "focus"}], "reinforcing_edges": []},
        },
        source_refs=("research:acme",),
    )
    dossier_sha = GoldenStore(store_path).append_leaf(dossier)
    watch_body = {
        "schema": "jaggedthoughts-public-equity-paper-decision-v1",
        "decision_id": "equity-paper-decision:ACME:research",
        "activated_at": "2026-08-10T11:40:00Z",
        "lifecycle": {"data_class": "operator", "stage": "active"},
        "entity": {"entity_id": "ACME", "entity_kind": "public_equity", "name": "Acme"},
        "evidence": {
            "candidate_leaf": candidate_leaf_sha, "candidate_sha256": candidate_sha,
            "dossier_leaf": dossier_sha,
        },
        "research": {"thesis": {"claim": "Durable cash generation persists."}},
        "paper_policy": {
            "target_weight": 0.0, "cash_default": True,
            "allocation_allowed": False, "order_routing_allowed": False,
        },
        "capital_authority": False, "brokerage_authority": False,
    }
    watch = {**watch_body, "decision_sha256": stable_sha256(watch_body)}
    watch_packet = subject._paper_watch_evidence_packet(
        tmp_path, watch, store=GoldenStore(store_path), owner="paper",
        opened_at=opened_at, horizon_days=90, benchmark_id="SPY",
    )
    assert watch_packet["subject"]["kind"] == "paper_watch_decision"
    assert watch_packet["decision_summary"]["target_weight"] == 0.0
    assert watch_packet["field_availability"]["complete"] is False
    assert watch_packet["field_availability"]["verified_field_group_count"] > 8
    assert watch_packet["strategy_snapshot"]["phenotype"]["phenotype_id"].startswith(
        "strategy-topology:"
    )
    discovery_agent = {**agent_result, "packet_sha256": discovery_packet["packet_sha256"]}
    discovery_run = subject.open_closed_book_forecast(
        tmp_path, owner="paper", store_path=store_path,
        candidate_leaf=candidate_leaf_sha, horizon_days=90, agent_result=discovery_agent,
    )
    assert discovery_run["subject"]["kind"] == "discovery_candidate"
    assert discovery_run["decision_path"] is None
    assert {row["candidate_id"] for row in discovery_run["candidate_forecasts"]} >= {
        "jaggedthoughts_discovery_valuation", "frontier_discovery_forecast",
    }

    monkeypatch.setattr(subject, "_utc_now", lambda: "2026-11-10T00:00:00Z")
    settlement = subject.settle_due_closed_book_forecasts(
        tmp_path, owner="paper", store_path=store_path,
        as_of="2026-11-10T00:00:00Z",
    )
    assert settlement["settled_count"] == 2
    assert settlement["settlements"][0]["entity_start_price"]["observed_at"] == "2026-08-11T00:00:00Z"
    assert settlement["settlements"][0]["actual_values"]["active_return"] == pytest.approx(
        0.06986007
    )
    assert len(settlement["settlements"][0]["candidate_scores"]) == 4
    status = subject.closed_book_status(tmp_path)
    assert status["scoreboard"]["inference_block_count"] == 1
    assert status["world_model_tournament"]["schema"] == "jaggedthoughts-world-model-tournament-v1"
    assert status["world_model_tournament"]["inference_sufficient"] is False
    learning = status["forecast_learning"]
    assert learning["bundle_count"] == 8
    assert learning["settled_bundle_count"] == 8
    assert learning["comparison_ready_bundle_count"] == 0
    assert learning["disagreement_queue"][0]["active_return_range"] == pytest.approx(0.04)
    assert all(not row["cross_entity_observed"] for row in learning["bundles"])

    _write_json(tmp_path / "paper_decisions/equities/acme.json", watch)
    ablation_packet = subject._paper_watch_evidence_packet(
        tmp_path, watch, store=GoldenStore(store_path), owner="paper",
        opened_at="2026-11-10T00:00:00Z", horizon_days=90, benchmark_id="SPY",
    )
    arms = subject.compile_underwriting_ablation_arms(ablation_packet)
    assert arms["typed_quantitative"]["incremental_evidence"] == {}
    assert "research" not in arms["typed_plus_fingerprint"]["incremental_evidence"]
    arm_results = {
        role: {
            **agent_result,
            "packet_sha256": packet["packet_sha256"],
            "expected_active_return": 0.01 + 0.01 * index,
            "target_weight": 0.05,
        }
        for index, (role, packet) in enumerate(arms.items())
    }
    ablation_run = subject.open_closed_book_forecast(
        tmp_path, owner="paper", store_path=store_path,
        paper_watch_decision_id=watch["decision_id"], horizon_days=90,
        ablation_agent_results=arm_results,
    )
    action = ablation_run["underwriting_information_ablation"]
    assert action["status"] == "sealed_three_arm_forecast"
    assert len({row["packet_sha256"] for row in action["arms"]}) == 3
    assert {row["candidate_id"] for row in ablation_run["candidate_forecasts"]} >= {
        f"underwriting_{role}" for role in arms
    }
    closed_status = subject.closed_book_status(tmp_path)
    ablation_status = closed_status["underwriting_ablation"]
    assert ablation_status["sealed_run_count"] == 1
    assert ablation_status["pending_settlement_count"] == 1
    assert ablation_status["comparison_ready"] is False
    projected = next(row for row in closed_status["runs"] if row["run_id"] == ablation_run["run_id"])
    assert (projected["status"], projected["entity"]["entity_id"], projected["underwriting_ablation"]) == (
        "awaiting_postseal_entry_binding", "ACME", {
            "status": "sealed_three_arm_forecast", "arms": list(arms),
        },
    )
    assert GoldenStore(store_path).verify()["ok"] is True


def test_underwriting_ablation_requires_eight_independent_blocks() -> None:
    roles = (
        "typed_quantitative", "typed_plus_fingerprint", "typed_plus_full_research",
    )
    process_body = {
        "schema": "jaggedthoughts-forecast-process-bundle-v1",
        "model_identity_complete": True,
        "resolved_model": "gpt-5.6-sol",
    }
    process = {
        **process_body, "process_bundle_sha256": stable_sha256(process_body),
    }
    availability_body = {
        "schema": "jaggedthoughts-field-availability-certificate-v1",
        "complete": True,
        "unverified_field_paths": [],
    }
    availability = {
        **availability_body, "certificate_sha256": stable_sha256(availability_body),
    }
    runs = tuple({
        "run_id": f"run-{index}", "sealed_at": f"2026-{index + 1:02d}-01T00:00:00Z",
        "provider": {"process_bundle": process},
        "evidence_packet": {"field_availability": availability},
        "underwriting_information_ablation": {
            "schema": "jaggedthoughts-underwriting-information-ablation-action-v1",
            "status": "sealed_three_arm_forecast",
            "same_model_process_sha256": process["process_bundle_sha256"],
            "arms": [
                {"role": role, "forecast_candidate_id": f"underwriting_{role}"}
                for role in roles
            ],
        },
    } for index in range(8))
    scores = {
        "typed_quantitative": (0.12, 0.25, 0.001),
        "typed_plus_fingerprint": (0.08, 0.20, 0.002),
        "typed_plus_full_research": (0.05, 0.10, 0.003),
    }
    settlements = tuple({
        "run_id": f"run-{index}",
        "evaluated_at": "2026-09-01T00:00:00Z",
        "candidate_scores": [{
            "candidate_id": f"underwriting_{role}",
            "active_return_absolute_error": values[0],
            "underperformance_brier": values[1],
            "active_return_contribution_after_cost": values[2],
        } for role, values in scores.items()],
    } for index in range(8))
    blocks = {f"run-{index}": f"block-{index}" for index in range(8)}

    seven = subject.compile_underwriting_ablation_status(
        runs[:7], settlements[:7], inference_block_ids=blocks,
    )
    eight = subject.compile_underwriting_ablation_status(
        runs, settlements, inference_block_ids=blocks,
    )
    assert seven["comparison_ready"] is False
    assert eight["comparison_ready"] is True
    assert eight["comparisons"][0]["block_weighted_mean"][
        "absolute_error_reduction"
    ] == pytest.approx(0.04)
