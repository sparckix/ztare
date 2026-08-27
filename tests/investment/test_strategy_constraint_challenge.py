from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from ztare.common.equivariance import stable_sha256
from ztare.investment.strategy_constraint_challenge import (
    REQUEST_SCHEMA,
    RESULT_SCHEMA,
    RUNTIME_PROVENANCE_SCHEMA,
    compile_strategy_constraint_challenge_request,
    compile_strategy_constraint_challenge_result,
    compile_strategy_constraint_frontier_gate,
    compile_strategy_constraint_successor,
)
from ztare.investment.strategy_constraint_evidence import (
    PROPOSAL_SCHEMA as EVIDENCE_PROPOSAL_SCHEMA,
    compile_strategy_constraint_evidence_request,
    compile_strategy_constraint_evidence_result,
    render_strategy_constraint_evidence_prompt,
    strategy_constraint_evidence_readiness,
    strategy_source_identity,
)
from ztare.investment.strategy_options import compile_company_strategy_frontier
from ztare.investment import research_agent


PROFILE = Path("examples/jaggedthoughts/investment/company_strategy_options.yaml")


def test_blind_evidence_separates_falsification_from_law_discrimination():
    one = strategy_constraint_evidence_readiness([{
        "predicate_effect_sha256": "a" * 64,
    }])
    two = strategy_constraint_evidence_readiness([
        {"predicate_effect_sha256": "a" * 64},
        {"predicate_effect_sha256": "b" * 64},
    ])

    assert one["status"] == "single_candidate_falsification"
    assert one["subscription_call_eligible"] is True
    assert one["institutional_law_eligible"] is False
    assert two["status"] == "competing_candidate_discrimination"
    assert two["subscription_call_eligible"] is True
    assert two["institutional_law_eligible"] is True


def test_frontier_synthesis_waits_for_blind_constraint_evidence(monkeypatch, tmp_path):
    request_sha = "a" * 64
    evidence_sha = "b" * 64
    request = {
        "request_sha256": request_sha, "entity_id": "EXAMPLE",
        "strategy_constraint_evidence": {
            "request": {"request_sha256": evidence_sha}, "status": "queued",
        },
    }
    monkeypatch.setattr(research_agent, "_strategy_frontier_request_integrity", lambda _: None)
    enqueued, finished = [], []
    monkeypatch.setattr(
        research_agent, "enqueue_strategy_constraint_evidence_request",
        lambda *args, **kwargs: enqueued.append(args[1]),
    )
    monkeypatch.setattr(
        research_agent, "_finish_agent_job",
        lambda *args, **kwargs: finished.append(kwargs["payload_update"]),
    )

    result = research_agent._consume_strategy_frontier_job(
        tmp_path, policy={"max_attempts": 3, "lease_seconds": 60},
        job={"work_id": "frontier", "payload": {
            "schema": research_agent.STRATEGY_FRONTIER_JOB_SCHEMA,
            "request_sha256": request_sha,
        }}, worker_id="worker", request=request,
    )

    assert result["status"] == "awaiting_strategy_constraint_evidence"
    assert result["provider_called"] is False
    assert enqueued == [{"request_sha256": evidence_sha}]
    assert finished[0]["stage"] == "awaiting_strategy_constraint_evidence"


def _challenge(
    *, implication: bool, independent: bool = False,
    verified_runtime: bool | None = None,
) -> tuple[dict, dict, dict]:
    profile = yaml.safe_load(PROFILE.read_text(encoding="utf-8"))
    profile.pop("contingent_policies", None)
    parent = compile_company_strategy_frontier(profile)
    a, b, c = [row["id"] for row in profile["options"][:3]]
    predicates = [
        {
            "predicate_kind": "incompatibility", "constraint_id": "a_not_b",
            "option_ids": [a, b], "evidence_refs": ["candidate_filing"],
        },
        {
            "predicate_kind": "prerequisite", "constraint_id": "a_requires_c",
            "option_id": a, "requires": [c], "evidence_refs": ["candidate_filing"],
        },
    ]
    request = compile_strategy_constraint_challenge_request(
        parent,
        examples={
            "admitted_bundles": [[a, c]], "excluded_bundles": [[a, b]],
            "implication_pairs": ([{
                "antecedent_option_ids": [a], "required_option_ids": [c],
            }] if implication else []),
            "evidence_provenance": {
                "example_source_ids": [
                    "holdout_filing" if independent else "candidate_filing"
                ],
                # Model-authored author labels are ignored by the kernel.
                "candidate_author_ids": ["self_declared_candidate"],
                "example_author_ids": ["self_declared_example"],
            },
        },
        candidate_predicates=predicates,
        source_ids=["candidate_filing", "holdout_filing"],
        observed_at="2026-07-01T00:00:00Z", available_at="2026-07-02T00:00:00Z",
        runtime_provenance=(
            lambda body: {**body, "provenance_sha256": stable_sha256(body)}
        )({
            "schema": RUNTIME_PROVENANCE_SCHEMA,
            "authority": "worker_verified_subscription_receipts",
            "candidate_call_receipt_sha256": "a" * 64,
            "example_call_receipt_sha256": "b" * 64,
        }) if (independent if verified_runtime is None else verified_runtime) else None,
    )
    return profile, parent, request


def test_unique_constraint_replay_compiles_successor() -> None:
    profile, parent, request = _challenge(implication=True, independent=True)
    accepted_sha = next(
        row["predicate_sha256"] for row in request["candidate_predicates"]
        if row["predicate_kind"] == "prerequisite"
    )
    result = compile_strategy_constraint_challenge_result({
        "schema": RESULT_SCHEMA, "request_sha256": request["request_sha256"],
        "assessed_at": "2026-07-03T00:00:00Z",
        "selected_predicate_sha256s": [accepted_sha],
    }, request, parent)
    successor_profile, successor = compile_strategy_constraint_successor(
        profile, parent, request, result,
    )

    assert request["schema"] == REQUEST_SCHEMA
    assert result["status"] == "accepted"
    assert result["evidence_grade"] == "diagnostic"
    assert result["research_claim_eligible"] is False
    assert successor_profile["feasibility_constraints"]["prerequisites"][0][
        "constraint_id"
    ] == "a_requires_c"
    assert successor["company"]["parent_strategy_frontier_sha256"] == parent[
        "strategy_frontier_sha256"
    ]
    assert successor["choice_space_certificate"]["feasible_bundle_count"] < parent[
        "choice_space_certificate"
    ]["feasible_bundle_count"]


def test_ambiguous_constraint_replay_cannot_create_successor() -> None:
    profile, parent, request = _challenge(implication=False)
    result = compile_strategy_constraint_challenge_result({
        "schema": RESULT_SCHEMA, "request_sha256": request["request_sha256"],
        "assessed_at": "2026-07-03T00:00:00Z", "selected_predicate_sha256s": [],
    }, request, parent)

    assert result["status"] == "ambiguous"
    assert request["independence_certificate"]["evidence_grade"] == "diagnostic"
    assert "candidate_example_source_overlap" in request[
        "independence_certificate"
    ]["diagnostic_reasons"]
    assert "holdout_visibility_not_verified" in request[
        "independence_certificate"
    ]["diagnostic_reasons"]
    assert result["replay"]["minimal_candidate_set_count"] == 2
    with pytest.raises(ValueError, match="ambiguous or insufficient"):
        compile_strategy_constraint_successor(deepcopy(profile), parent, request, result)


def test_self_declared_author_ids_cannot_upgrade_independent_sources() -> None:
    _, _, request = _challenge(
        implication=True, independent=True, verified_runtime=False,
    )

    certificate = request["independence_certificate"]
    assert certificate["evidence_grade"] == "diagnostic"
    assert "verified_role_provenance_absent" in certificate["diagnostic_reasons"]
    assert "verified_information_family_provenance_absent" in certificate[
        "diagnostic_reasons"
    ]


def test_frontier_gate_withholds_ambiguous_predicates_and_admits_unique_minimum() -> None:
    profile, parent, request = _challenge(implication=True)
    by_kind = {row["predicate_kind"]: row for row in request["candidate_predicates"]}
    constraints = {
        "incompatibilities": [{
            key: value for key, value in by_kind["incompatibility"].items()
            if key not in {"predicate_kind", "predicate_sha256"}
        }],
        "prerequisites": [{
            key: value for key, value in by_kind["prerequisite"].items()
            if key not in {"predicate_kind", "predicate_sha256"}
        }],
        "resources": [],
    }
    gate = compile_strategy_constraint_frontier_gate(
        parent, candidate_constraints=constraints,
        examples=request["constraint_challenge_examples"],
        source_ids=request["source_ids"], observed_at=request["observed_at"],
        available_at=request["available_at"],
    )

    assert gate["status"] == "accepted"
    assert gate["evidence_grade"] == "diagnostic"
    assert gate["research_claim_eligible"] is False
    assert gate["challenge_result"]["successor_eligible"] is True
    assert gate["accepted_constraints"]["incompatibilities"] == []
    assert [
        row["constraint_id"] for row in gate["accepted_constraints"]["prerequisites"]
    ] == ["a_requires_c"]

    successor_profile, successor = compile_strategy_constraint_successor(
        profile, parent, gate["challenge_request"], gate["challenge_result"],
    )
    mutated = deepcopy(successor_profile["feasibility_constraints"])
    mutated["prerequisites"][0]["requires"] = [profile["options"][1]["id"]]
    blocked = compile_strategy_constraint_frontier_gate(
        successor, candidate_constraints=mutated, examples={},
        source_ids=request["source_ids"], observed_at=successor["evidence_epoch"],
        available_at=successor["evidence_epoch"],
    )
    assert blocked["status"] == "identity_conflict"
    assert blocked["accepted_constraints"] == {
        key: [
            {
                field: value for field, value in row.items()
                if field not in {"authority", "predicate_kind", "predicate_sha256"}
            }
            for row in successor["feasibility_constraints"][key]
        ]
        for key in ("incompatibilities", "prerequisites", "resources")
    }


def test_blind_subscription_evidence_earns_independent_replay() -> None:
    _, parent, dossier_challenge = _challenge(implication=True)
    by_kind = {row["predicate_kind"]: row for row in dossier_challenge["candidate_predicates"]}
    constraints = {
        "incompatibilities": [{
            key: value for key, value in by_kind["incompatibility"].items()
            if key not in {"predicate_kind", "predicate_sha256"}
        }],
        "prerequisites": [{
            key: value for key, value in by_kind["prerequisite"].items()
            if key not in {"predicate_kind", "predicate_sha256"}
        }],
        "resources": [],
    }
    diagnostic = compile_strategy_constraint_frontier_gate(
        parent, candidate_constraints=constraints,
        examples=dossier_challenge["constraint_challenge_examples"],
        source_ids=dossier_challenge["source_ids"],
        observed_at=dossier_challenge["observed_at"],
        available_at=dossier_challenge["available_at"],
    )
    request = compile_strategy_constraint_evidence_request(
        parent, diagnostic, parent_path="parent.json", entity_id="EXAMPLE",
        dossier_sha256="d" * 64,
        option_vocabulary=[{
            "option_id": row["option_id"], "description": row["description"],
        } for row in parent["option_catalog"]],
        forbidden_sources=[{
            "source_id": "candidate_filing", "url": "https://example.com/candidate",
        }],
        candidate_call_receipt_sha256="a" * 64,
    )
    prompt = render_strategy_constraint_evidence_prompt(request)
    assert request["probe_frontier"]["informative_bundle_count"] > 0
    assert request["probe_frontier"]["targets"][0]["option_ids"]
    assert not any(value in prompt for value in (
        "candidate_filing", "candidate_predicates", "https://example.com/candidate",
    ))
    assert strategy_source_identity(
        "https://www.sec.gov/Archives/edgar/data/1/000000000000000001/a.htm",
    ) == strategy_source_identity(
        "https://www.sec.gov/Archives/edgar/data/1/000000000000000001/b.htm",
    )
    a = by_kind["prerequisite"]["option_id"]
    c = by_kind["prerequisite"]["requires"][0]
    b = next(value for value in by_kind["incompatibility"]["option_ids"] if value != a)
    holdout_url = (
        "https://www.sec.gov/Archives/edgar/data/1/"
        "000000000000000001/holdout.htm"
    )
    proposal = {
        "schema": EVIDENCE_PROPOSAL_SCHEMA, "request_sha256": request["request_sha256"],
        "sources": [{
            "url": holdout_url, "title": "Holdout",
            "published_at": "2026-07-03T00:00:00Z",
        }],
        "admitted_bundles": [{
            "example_id": "admitted", "option_ids": [a, c],
            "evidence_refs": [holdout_url],
        }],
        "excluded_bundles": [{
            "example_id": "excluded", "option_ids": [a, b],
            "evidence_refs": [holdout_url],
        }],
        "implication_pairs": [{
            "example_id": "implication", "antecedent_option_ids": [a],
            "required_option_ids": [c],
            "evidence_refs": [holdout_url],
        }],
        "residual": "none",
    }
    provenance = {
        "schema": "jaggedthoughts-subscription-result-provenance-v1",
        "call_receipt_sha256": "b" * 64, "accepted_at": "2026-07-04T00:00:00Z",
    }
    provenance = {**provenance, "provenance_sha256": stable_sha256(provenance)}
    capture = {
        "schema": "jaggedthoughts-sec-filing-url-capture-v1",
        "source_url": holdout_url,
        "accepted_at": "2026-07-03T00:00:00Z",
        "content_sha256": "c" * 64,
        "publication_time_authority": "sec_provider_acceptance_time",
    }
    capture = {**capture, "capture_sha256": stable_sha256(capture)}
    result = compile_strategy_constraint_evidence_result(
        request, proposal, parent, accepted_at="2026-07-04T00:00:00Z",
        provider_result_provenance=provenance, source_captures=[capture],
    )

    assert result["status"] == "replayed"
    assert result["evidence_grade"] == "candidate_blind_source_disjoint_replay"
    assert result["research_claim_eligible"] is True
