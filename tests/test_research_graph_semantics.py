from __future__ import annotations

import json

from ztare.common.graph_algorithms import analyze
from ztare.reports.research_graph import build_research_graph
from ztare.scenarios.adapters import governed_state_from_carrier
from ztare.scenarios.strength import strength_profile


def _project(tmp_path, *, supports_claims=None):
    project = tmp_path / "projects" / "case"
    project.mkdir(parents=True)
    (project / "latest_eval_results.json").write_text(json.dumps({
        "probability_dag": {
            "outcome": {"label": "The product should launch", "probability": 0.81},
            "nodes": [{"id": "demand", "label": "Customers will adopt it", "probability": 0.73}],
        }
    }), encoding="utf-8")
    fact = {"statement": "Nine customers requested the workflow", "source_ids": ["S1"]}
    if supports_claims is not None:
        fact["supports_claims"] = supports_claims
    (project / "compiled_evidence_packet.json").write_text(json.dumps({
        "provenance": [{"source_id": "S1", "path": "interviews.md", "source_type": "source_evidence"}],
        "immutable_ground_truth": [fact],
        "candidate_claims_to_test": [{"claim": "The launch will retain users", "source_ids": ["S1"]}],
    }), encoding="utf-8")
    return tmp_path


def test_unmatched_source_fact_does_not_support_the_thesis(tmp_path):
    root = _project(tmp_path)
    graph = build_research_graph("case", root)
    fact = next(n for n in graph["nodes"] if n["id"].startswith("fact:"))
    candidate = next(n for n in graph["nodes"] if n["id"].startswith("cand:"))

    assert fact["provenance"] == "llm"
    assert fact["binding_status"] == "unattached"
    assert {e["relation"] for e in graph["edges"] if e["to"] in {fact["id"], candidate["id"]}} == {"REPORTS"}
    assert not any(e["from"] == fact["id"] and e["to"] == "thesis" for e in graph["edges"])
    assert all(e["warrant"] == "W3" for e in graph["edges"])

    profile = strength_profile(governed_state_from_carrier(graph))
    assert profile["status"] == "UNSUPPORTED"
    assert profile["profile"] == [0.0, 0.0, 0.0, 0.0]


def test_explicit_claim_target_creates_only_an_unchecked_claim_edge(tmp_path):
    root = _project(tmp_path, supports_claims=["demand"])
    graph = build_research_graph("case", root)
    fact = next(n for n in graph["nodes"] if n["id"].startswith("fact:"))
    support = [e for e in graph["edges"] if e["from"] == fact["id"] and e["relation"] == "SUPPORTS"]

    assert fact["binding_status"] == "targeted"
    assert fact["claim_targets"] == ["claim:demand"]
    assert support == [{"from": fact["id"], "to": "claim:demand", "relation": "SUPPORTS", "warrant": "W3"}]
    assert not any(e["from"] == fact["id"] and e["to"] == "thesis" for e in graph["edges"])


def test_graph_ids_are_stable_and_non_support_relations_do_not_inflate_structure(tmp_path):
    root = _project(tmp_path)
    first = build_research_graph("case", root)
    second = build_research_graph("case", root)
    assert [n["id"] for n in first["nodes"]] == [n["id"] for n in second["nodes"]]

    reads = analyze({
        "graph_kind": "source_claim_graph",
        "nodes": [
            {"id": "thesis", "type": "thesis", "label": "T", "weight": 0.9},
            {"id": "claim", "type": "claim", "label": "C", "weight": 0.9},
            {"id": "source", "type": "evidence", "label": "S"},
            {"id": "test", "type": "candidate", "label": "Experiment"},
        ],
        "edges": [
            {"from": "source", "to": "claim", "relation": "REPORTS"},
            {"from": "test", "to": "thesis", "relation": "TESTS"},
            {"from": "claim", "to": "thesis", "relation": "CONSTRAINS"},
        ],
    })
    assert {row["id"] for row in reads["unsupported"]} == {"claim", "test"}
    assert "linchpin" not in reads
    assert "argument_strength" not in reads
    assert "debate_shift" not in reads
    assert "polarization" not in reads
