import json

import yaml

from ztare.common.equivariance import stable_sha256
from ztare.investment.equity_paper import DECISION_SCHEMA, _matching_frontier
from ztare.investment.golden_store import (
    GoldenEdge,
    GoldenLeaf,
    GoldenStore,
    record_research_evidence_quarantine,
    research_evidence_is_admissible,
)
from ztare.investment.research_memory import (
    candidate_research_coverage,
    candidate_strategy_phenotype,
    record_candidate_research_coverage,
)
from ztare.investment.workspace import _paper_watch_rows


def test_quarantine_removes_bad_dossier_from_current_decision_surfaces(tmp_path) -> None:
    owner = "paper"
    store = GoldenStore(tmp_path / "state" / "golden_store.sqlite3")
    candidate = GoldenLeaf(
        owner=owner, object_kind="discovery_candidate", object_id="equity:ALPHA",
        epoch="candidate", occurred_at="2026-08-10T00:00:00Z",
        available_at="2026-08-10T00:00:00Z",
        payload={
            "schema": "jaggedthoughts-discovery-candidate-v1",
            "entity_id": "ALPHA", "candidate_sha256": "c" * 64,
        },
        source_refs=("fixture",),
    )
    store.append_leaf(candidate)
    dossier = GoldenLeaf(
        owner=owner, object_kind="candidate_research_dossier",
        object_id=f"research:ALPHA:{candidate.leaf_sha256}", epoch="dossier",
        occurred_at="2026-08-10T00:01:00Z", available_at="2026-08-10T00:01:00Z",
        payload={
            "schema": "jaggedthoughts-candidate-research-dossier-v1",
            "entity_id": "ALPHA", "candidate_leaf": candidate.leaf_sha256,
            "dossier_sha256": "d" * 64,
            "strategy": {"choices": [{"id": "focus"}], "reinforcing_edges": []},
        },
        source_refs=("fixture",),
    )
    store.append_leaf(dossier)
    assert candidate_strategy_phenotype(
        store, owner=owner, candidate_leaf=candidate.leaf_sha256,
        as_of="2026-08-10T00:00:30Z",
    )[0] is None
    assert candidate_strategy_phenotype(
        store, owner=owner, candidate_leaf=candidate.leaf_sha256,
        as_of="2026-08-10T00:01:30Z",
    )[0]["entity_id"] == "ALPHA"
    quarantine_leaf = record_research_evidence_quarantine(
        store, owner=owner, target_leaf=dossier.leaf_sha256,
        reason_code="acceptance_time_violation",
        detected_at="2026-08-11T00:00:00Z", source_refs=("receipt:fixture",),
    )

    assert not research_evidence_is_admissible(
        store, owner=owner, target_leaf=dossier.leaf_sha256,
    )
    assert research_evidence_is_admissible(
        store, owner=owner, target_leaf=dossier.leaf_sha256,
        as_of="2026-08-10T12:00:00Z",
    )
    derived = GoldenLeaf(
        owner=owner, object_kind="candidate_research_dossier",
        object_id=f"research:ALPHA:{candidate.leaf_sha256}", epoch="derived",
        occurred_at="2026-08-10T00:02:00Z", available_at="2026-08-10T00:02:00Z",
        payload={
            **dossier.payload, "dossier_sha256": "e" * 64,
            "strategy": {"choices": [{"id": "focus"}], "reinforcing_edges": []},
        },
        source_refs=("fixture",),
    )
    store.append_bundle(
        (derived,), (GoldenEdge(derived.leaf_sha256, dossier.leaf_sha256, "derived_from"),),
    )
    assert not research_evidence_is_admissible(
        store, owner=owner, target_leaf=derived.leaf_sha256,
    )
    coverage = candidate_research_coverage(
        store, owner=owner, candidate_leaf=candidate.leaf_sha256,
        current_receipts={},
    )
    assert coverage["status"] == "research_evidence_quarantined"
    assert coverage["covered"] is False
    assert coverage["evidence_quarantine_leaf"] == quarantine_leaf
    record_candidate_research_coverage(store, owner=owner, coverage=coverage)
    assert candidate_strategy_phenotype(
        store, owner=owner, candidate_leaf=candidate.leaf_sha256,
    )[0] is None

    frontier_dir = tmp_path / "strategy_frontiers" / "results"
    frontier_dir.mkdir(parents=True)
    (frontier_dir / "alpha-frontier.json").write_text(json.dumps({
        "company": {
            "candidate_leaf": candidate.leaf_sha256,
            "source_dossier_sha256": "d" * 64,
        },
    }), encoding="utf-8")
    assert _matching_frontier(
        tmp_path, "ALPHA", candidate.leaf_sha256, "d" * 64,
        store=store, owner=owner, dossier_leaf=dossier.leaf_sha256,
    ) is None

    (tmp_path / "workspace.yaml").write_text(yaml.safe_dump({
        "owner": owner, "golden_store": "state/golden_store.sqlite3",
    }), encoding="utf-8")
    decision_dir = tmp_path / "paper_decisions" / "equities"
    decision_dir.mkdir(parents=True)
    body = {
        "schema": DECISION_SCHEMA, "decision_id": "decision:alpha",
        "activated_at": "2026-08-10T01:00:00Z",
        "entity": {"entity_id": "ALPHA", "entity_kind": "public_equity"},
        "evidence": {
            "candidate_leaf": candidate.leaf_sha256,
            "dossier_leaf": dossier.leaf_sha256,
        },
    }
    (decision_dir / "alpha.json").write_text(json.dumps({
        **body, "decision_sha256": stable_sha256(body),
    }), encoding="utf-8")
    assert _paper_watch_rows(tmp_path) == []
