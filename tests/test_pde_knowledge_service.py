import json

from ztare.leanmill.solver.no_good_store import NoGoodStore
from ztare.leanmill.solver.proof_cache import ProofCache
from ztare.pde.knowledge_service import (
    build_leanmill_memory_summary,
    build_pde_knowledge_context,
)


def test_pde_knowledge_context_reuses_leanmill_memory_without_owning_it(tmp_path) -> None:
    statement = "theorem pde_goal : True := by trivial"
    proof_cache_path = tmp_path / "proof_cache.jsonl"
    no_good_path = tmp_path / "no_good.jsonl"

    ProofCache(proof_cache_path).put(statement, "by trivial", source="test")
    NoGoodStore(no_good_path).record(
        statement,
        "vacuous_closure",
        "test witness",
        confirmed=True,
        source="test",
    )

    context = build_pde_knowledge_context(
        target="annular pressure payment",
        query="annular Riesz payment",
        statement=statement,
        theorem_db={
            "annular_profile": {
                "requires": {"annular_bandlimit": True},
                "concludes": {"usable": True},
                "does_not_accept": [],
            }
        },
        available={"annular_bandlimit": True},
        proof_cache_path=proof_cache_path,
        no_good_store_path=no_good_path,
        embedder=lambda _text: [1.0],
        top_k_mathlib=0,
        top_k_domain=0,
        top_k_own=0,
    )

    assert context["schema"] == "pde-knowledge-context-v1"
    assert context["theorem_profile_cards"][0]["applicability"]["verdict"] == "MATCH"
    assert context["leanmill_memory"]["proof_cache"]["hit"] is True
    assert context["leanmill_memory"]["no_good_store"]["n_matches"] == 1
    assert any("FailureMemoryLeaf" in item for item in context["recommended_leaf_sequence"])
    assert "advisory_retrieval_only" in context["credit_boundary"]


def test_leanmill_memory_summary_fails_open_when_paths_absent() -> None:
    summary = build_leanmill_memory_summary(statement="")

    assert summary["schema"] == "pde-leanmill-memory-summary-v1"
    assert summary["proof_cache"]["enabled"] is False
    assert summary["no_good_store"]["enabled"] is False
    assert "lean statement not supplied" in summary["skip_reasons"]
