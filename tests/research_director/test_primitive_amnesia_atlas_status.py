import json

from ztare.research_director.primitive_amnesia import (
    AtlasFreshnessStatus,
    Primitive,
    atlas_freshness_status,
    build_primitive_atlas,
    evaluate,
    miss_queue_status,
    primitive_catalog_digest,
    record_miss_queue,
)
from ztare.research_director import primitive_amnesia
from ztare.research_director.primitive_tick_surface import build_primitive_tick_surface


def _vec(value: float) -> list[float]:
    return [value] * 768


def _write_catalog(path, signatures):
    rows = [
        {
            "id": signature.upper(),
            "path": f"src/ztare/test/{signature}.py",
            "kind": "primitive",
            "description": f"{signature} test primitive",
            "signature": signature,
        }
        for signature in signatures
    ]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def _digest_for_catalog(path) -> str:
    return primitive_catalog_digest(primitive_amnesia._extract_from_arch_index(path))


def test_atlas_freshness_status_passes_when_catalog_and_atlas_match(tmp_path) -> None:
    catalog = tmp_path / "architecture_index.jsonl"
    atlas = tmp_path / "primitive_atlas_embeddings.json"
    _write_catalog(catalog, ["alpha", "beta"])
    atlas.write_text(
        json.dumps(
                {
                    "backend": "gemini-code",
                    "n": 2,
                    "catalog_digest": _digest_for_catalog(catalog),
                    "embeddings": {"alpha": _vec(0.1), "beta": _vec(0.3)},
                }
            ),
            encoding="utf-8",
        )

    status = atlas_freshness_status(catalog_path=catalog, atlas_path=atlas)

    assert status.ok is True
    assert status.catalog_count == 2
    assert status.atlas_n == 2
    assert status.embeddings_count == 2
    assert status.catalog_digest_matches is True
    assert status.warnings == []


def test_atlas_freshness_status_flags_catalog_digest_mismatch(tmp_path) -> None:
    catalog = tmp_path / "architecture_index.jsonl"
    atlas = tmp_path / "primitive_atlas_embeddings.json"
    _write_catalog(catalog, ["alpha"])
    atlas.write_text(
        json.dumps(
            {
                "backend": "gemini-code",
                "n": 1,
                "catalog_digest": "stale-digest",
                "embeddings": {"alpha": _vec(0.1)},
            }
        ),
        encoding="utf-8",
    )

    status = atlas_freshness_status(catalog_path=catalog, atlas_path=atlas)

    assert status.ok is False
    assert status.catalog_digest_matches is False
    assert any("catalog_digest does not match" in warning for warning in status.warnings)


def test_atlas_freshness_status_flags_missing_embedding(tmp_path) -> None:
    catalog = tmp_path / "architecture_index.jsonl"
    atlas = tmp_path / "primitive_atlas_embeddings.json"
    _write_catalog(catalog, ["alpha", "beta"])
    atlas.write_text(
        json.dumps(
            {
                "backend": "gemini-code",
                "n": 1,
                "catalog_digest": _digest_for_catalog(catalog),
                "embeddings": {"alpha": [0.1, 0.2]},
            }
        ),
        encoding="utf-8",
    )

    status = atlas_freshness_status(catalog_path=catalog, atlas_path=atlas)

    assert status.ok is False
    assert status.missing_embeddings == 1
    assert any("lack atlas embeddings" in warning for warning in status.warnings)


def test_atlas_freshness_status_flags_malformed_embeddings(tmp_path) -> None:
    catalog = tmp_path / "architecture_index.jsonl"
    atlas = tmp_path / "primitive_atlas_embeddings.json"
    _write_catalog(catalog, ["alpha"])
    atlas.write_text(
        json.dumps(
            {
                "backend": "gemini-code",
                "n": 1,
                "catalog_digest": _digest_for_catalog(catalog),
                "embeddings": {"alpha": []},
            }
        ),
        encoding="utf-8",
    )

    status = atlas_freshness_status(catalog_path=catalog, atlas_path=atlas)

    assert status.ok is False
    assert status.invalid_embeddings == 1
    assert any("malformed" in warning for warning in status.warnings)


def test_atlas_freshness_status_flags_wrong_embedding_dimension(tmp_path) -> None:
    catalog = tmp_path / "architecture_index.jsonl"
    atlas = tmp_path / "primitive_atlas_embeddings.json"
    _write_catalog(catalog, ["alpha"])
    atlas.write_text(
        json.dumps(
            {
                "backend": "gemini-code",
                "n": 1,
                "catalog_digest": _digest_for_catalog(catalog),
                "embeddings": {"alpha": [0.1, 0.2]},
            }
        ),
        encoding="utf-8",
    )

    status = atlas_freshness_status(catalog_path=catalog, atlas_path=atlas)

    assert status.ok is False
    assert status.vector_dimension == 2
    assert any("dimension 2 != expected 768" in warning for warning in status.warnings)


def test_primitive_tick_surface_warns_when_atlas_status_is_stale(monkeypatch) -> None:
    def fake_status():
        return AtlasFreshnessStatus(
            ok=False,
            catalog_path="catalog",
            atlas_path="atlas",
            catalog_count=2,
            atlas_n=1,
            embeddings_count=1,
            backend="gemini-code",
            catalog_digest="digest",
            atlas_catalog_digest="stale",
            catalog_digest_matches=False,
            missing_embeddings=1,
            extra_embeddings=0,
            invalid_embeddings=0,
            vector_dimension=768,
            duplicate_embedding_keys=0,
            catalog_newer_than_atlas=False,
            warnings=["1 catalog primitives lack atlas embeddings"],
        )

    monkeypatch.setattr(primitive_amnesia, "atlas_freshness_status", fake_status)

    surface = build_primitive_tick_surface(query_terms=["autoresearch"], top_n=3)

    assert any("primitive atlas stale" in warning for warning in surface.warnings)


def test_build_primitive_atlas_fails_closed_on_partial_embedding(monkeypatch, tmp_path) -> None:
    catalog = tmp_path / "architecture_index.jsonl"
    atlas = tmp_path / "primitive_atlas_embeddings.json"
    _write_catalog(catalog, ["alpha", "beta"])
    atlas.write_text(
        json.dumps(
                {
                    "backend": "gemini-code",
                    "n": 1,
                    "embeddings": {"alpha": _vec(0.1)},
                }
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr(
        primitive_amnesia,
        "build_inventory",
        lambda: [
            Primitive("alpha", "alpha.py", "primitive", "alpha", "alpha doc", "architecture_index"),
            Primitive("beta", "beta.py", "primitive", "beta", "beta doc", "architecture_index"),
        ],
    )
    monkeypatch.setattr(primitive_amnesia, "_embed", lambda *args, **kwargs: None)

    n = build_primitive_atlas(path=atlas, backend="gemini-code")

    assert n == 0
    payload = json.loads(atlas.read_text(encoding="utf-8"))
    assert payload["n"] == 1


def test_build_primitive_atlas_reuses_existing_embeddings(monkeypatch, tmp_path) -> None:
    atlas = tmp_path / "primitive_atlas_embeddings.json"
    atlas.write_text(
        json.dumps(
            {
                "backend": "gemini-code",
                "n": 1,
                "embeddings": {"alpha": _vec(0.1)},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        primitive_amnesia,
        "build_inventory",
        lambda: [
            Primitive("alpha", "alpha.py", "primitive", "alpha", "alpha doc", "architecture_index"),
            Primitive("beta", "beta.py", "primitive", "beta", "beta doc", "architecture_index"),
        ],
    )

    calls: list[str] = []

    def fake_embed(text, *args, **kwargs):
        calls.append(text)
        return _vec(0.3)

    monkeypatch.setattr(primitive_amnesia, "_embed", fake_embed)

    n = build_primitive_atlas(path=atlas, backend="gemini-code")

    assert n == 2
    assert len(calls) == 1
    assert calls[0].startswith("beta.")
    payload = json.loads(atlas.read_text(encoding="utf-8"))
    assert payload["n"] == 2
    assert payload["embeddings"]["alpha"] == _vec(0.1)
    assert payload["embeddings"]["beta"] == _vec(0.3)


def test_build_primitive_atlas_replaces_wrong_dimension_cached_embeddings(monkeypatch, tmp_path) -> None:
    atlas = tmp_path / "primitive_atlas_embeddings.json"
    atlas.write_text(
        json.dumps(
            {
                "backend": "gemini-code",
                "n": 1,
                "embeddings": {"alpha": [0.1, 0.2]},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        primitive_amnesia,
        "build_inventory",
        lambda: [
            Primitive("alpha", "alpha.py", "primitive", "alpha", "alpha doc", "architecture_index"),
        ],
    )

    calls: list[str] = []

    def fake_embed(text, *args, **kwargs):
        calls.append(text)
        return _vec(0.9)

    monkeypatch.setattr(primitive_amnesia, "_embed", fake_embed)

    n = build_primitive_atlas(path=atlas, backend="gemini-code")

    assert n == 1
    assert len(calls) == 1
    payload = json.loads(atlas.read_text(encoding="utf-8"))
    assert payload["embeddings"]["alpha"] == _vec(0.9)


def test_build_primitive_atlas_fails_closed_on_wrong_dimension_new_embedding(
    monkeypatch, tmp_path
) -> None:
    atlas = tmp_path / "primitive_atlas_embeddings.json"
    monkeypatch.setattr(
        primitive_amnesia,
        "build_inventory",
        lambda: [
            Primitive("alpha", "alpha.py", "primitive", "alpha", "alpha doc", "architecture_index"),
        ],
    )
    monkeypatch.setattr(primitive_amnesia, "_embed", lambda *args, **kwargs: [0.1, 0.2])

    n = build_primitive_atlas(path=atlas, backend="gemini-code")

    assert n == 0
    assert not atlas.exists()


def test_evaluate_returns_structured_miss_records(monkeypatch) -> None:
    monkeypatch.setattr(
        primitive_amnesia,
        "BENCHMARK",
        [("find the missing capability", ["wanted_primitive"])],
    )
    monkeypatch.setattr(
        primitive_amnesia,
        "build_inventory",
        lambda: [
            Primitive(
                "near_miss",
                "src/ztare/test/near.py",
                "function",
                "near_miss()",
                "near miss primitive",
                "code",
                "adjacent capability",
            )
        ],
    )
    monkeypatch.setattr(
        primitive_amnesia,
        "precheck",
        lambda query, top_k, inventory, semantic: [
            {
                "name": "near_miss",
                "module": "src/ztare/test/near.py",
                "kind": "function",
                "signature": "near_miss()",
                "doc": "near miss primitive",
                "when_to_use": "adjacent capability",
                "category": "test",
                "score": 0.42,
                "matched_terms": ["capability"],
            }
        ],
    )

    result = evaluate(top_k=5, semantic=True)

    assert result["recall_at_k"] == 0.0
    assert len(result["miss_records"]) == 1
    miss = result["miss_records"][0]
    assert miss["miss_kind"] == "benchmark_target_unresolved"
    assert miss["query"] == "find the missing capability"
    assert miss["targets"] == ["wanted_primitive"]
    assert miss["top_candidates"][0]["name"] == "near_miss"
    assert "benchmark_target_unresolved" in miss["repair_policy"]


def test_evaluate_counts_only_resolvable_cases_in_recall(monkeypatch) -> None:
    monkeypatch.setattr(
        primitive_amnesia,
        "BENCHMARK",
        [
            {
                "case_id": "resolved-miss",
                "query": "find adjacent but rank misses target",
                "targets": ["wanted_primitive"],
                "confusers": ["near_miss"],
                "family": "test",
            },
            {
                "case_id": "unresolved-target",
                "query": "find absent target",
                "targets": ["absent_primitive"],
            },
        ],
    )
    monkeypatch.setattr(
        primitive_amnesia,
        "build_inventory",
        lambda: [
            Primitive(
                "wanted_primitive",
                "src/ztare/test/wanted.py",
                "function",
                "wanted_primitive()",
                "wanted primitive",
                "code",
            ),
            Primitive(
                "near_miss",
                "src/ztare/test/near.py",
                "function",
                "near_miss()",
                "near miss primitive",
                "code",
            ),
        ],
    )
    monkeypatch.setattr(
        primitive_amnesia,
        "precheck",
        lambda query, top_k, inventory, semantic: [
            {
                "name": "near_miss",
                "module": "src/ztare/test/near.py",
                "kind": "function",
                "signature": "near_miss()",
                "doc": "near miss primitive",
                "when_to_use": "",
                "category": "test",
                "score": 0.9,
                "matched_terms": [],
            }
        ],
    )

    result = evaluate(top_k=5, semantic=True)

    assert result["n"] == 2
    assert result["resolvable_n"] == 1
    assert result["recall_at_k"] == 0.0
    assert result["unresolved_target_count"] == 1
    assert result["confuser_hit_count"] == 1
    assert {miss["miss_kind"] for miss in result["miss_records"]} == {
        "retrieval_miss",
        "benchmark_target_unresolved",
    }


def test_record_miss_queue_dedupes_by_miss_id(tmp_path) -> None:
    queue = tmp_path / "primitive_amnesia_miss_queue.jsonl"
    eval_result = {
        "miss_records": [
            {
                "miss_id": "abc123",
                "benchmark_index": 0,
                "query": "missing query",
                "targets": ["wanted"],
                "top_k": 5,
                "ranker": "semantic",
                "benchmark_digest": "bench",
                "catalog_digest": "catalog",
                "top_candidates": [],
                "repair_policy": "repair",
            }
        ]
    }

    first = record_miss_queue(eval_result, path=queue)
    second = record_miss_queue(eval_result, path=queue)

    assert first["appended"] == 1
    assert second["appended"] == 0
    rows = [json.loads(line) for line in queue.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1
    assert rows[0]["schema_version"] == "primitive_amnesia_miss_v1"
    assert rows[0]["status"] == "open"
    assert rows[0]["miss_id"] == "abc123"


def test_record_miss_queue_skips_when_semantic_embedder_is_unavailable(tmp_path) -> None:
    queue = tmp_path / "primitive_amnesia_miss_queue.jsonl"
    eval_result = {
        "ranker": "semantic",
        "semantic_live": False,
        "semantic_liveness_reason": "network unavailable",
        "miss_records": [
            {
                "miss_id": "false-semantic-miss",
                "benchmark_index": 0,
                "query": "missing query",
                "targets": ["wanted"],
                "top_k": 5,
                "ranker": "semantic",
                "benchmark_digest": "bench",
                "catalog_digest": "catalog",
                "top_candidates": [],
                "repair_policy": "repair",
            }
        ],
    }

    result = record_miss_queue(eval_result, path=queue)

    assert result["skipped"] is True
    assert result["appended"] == 0
    assert result["misses"] == 1
    assert not queue.exists()


def test_miss_queue_status_counts_open_and_malformed_rows(tmp_path) -> None:
    queue = tmp_path / "primitive_amnesia_miss_queue.jsonl"
    queue.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "miss_id": "open1",
                        "status": "open",
                        "case_id": "case1",
                        "query": "find overlap primitive",
                        "targets": ["jaccard"],
                        "miss_kind": "retrieval_miss",
                        "ranker": "semantic",
                        "recorded_at": "2026-06-13T00:00:00+00:00",
                        "target_resolution": {
                            "resolved": True,
                            "matches": [
                                {
                                    "name": "jaccard_distance",
                                    "module": "src/ztare/motion/set_distance.py",
                                    "signature": "jaccard_distance(a, b)",
                                }
                            ],
                        },
                        "top_candidates": [
                            {
                                "name": "set_overlap_ratio",
                                "module": "src/ztare/motion/set_distance.py",
                                "signature": "set_overlap_ratio(a, b)",
                            }
                        ],
                    }
                ),
                json.dumps({"miss_id": "done1", "status": "closed"}),
                "{not-json",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    status = miss_queue_status(queue)

    assert status["exists"] is True
    assert status["row_count"] == 2
    assert status["open_count"] == 1
    assert status["malformed_count"] == 1
    assert status["latest_open"][0]["miss_id"] == "open1"
    assert status["promotion_review_counts"] == {
        "close_as_catalog_retrieval_repair": 1
    }
    review = status["latest_open"][0]["promotion_review"]
    assert review["validation"]["ok"] is True
    assert review["promotion_decision"] == "close_as_catalog_retrieval_repair"
    assert review["typed_carrier"] == "primitive_catalog_alias_or_atlas_repair"
    assert "jaccard_distance" in review["nearest_existing_surface"]
    assert "set_overlap_ratio" in review["nearest_confuser"]


def test_miss_queue_status_classifies_unresolved_target_as_review_candidate(tmp_path) -> None:
    queue = tmp_path / "primitive_amnesia_miss_queue.jsonl"
    queue.write_text(
        json.dumps(
            {
                "miss_id": "missing-target",
                "status": "open",
                "case_id": "case-missing",
                "query": "compile residual failure into graph operator",
                "targets": ["residual_graph_compiler"],
                "miss_kind": "benchmark_target_unresolved",
                "ranker": "semantic",
                "recorded_at": "2026-06-13T00:00:00+00:00",
                "target_resolution": {"resolved": False, "matches": []},
                "top_candidates": [],
                "repair_policy": "check duplicate before adding anything",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    status = miss_queue_status(queue)

    assert status["promotion_review_counts"] == {
        "review_missing_catalog_or_benchmark_target": 1
    }
    review = status["latest_open"][0]["promotion_review"]
    assert review["validation"]["ok"] is True
    assert review["promotion_decision"] == "review_missing_catalog_or_benchmark_target"
    assert review["typed_carrier"] == "primitive_catalog_candidate_or_benchmark_repair"
    assert "not a promoted primitive" in review["non_claim"]
    assert "duplicate" in review["kill_criterion"]


def test_precheck_demotes_substrate_artifacts_for_generic_queries(monkeypatch) -> None:
    inventory = [
        Primitive(
            "generic_residual_gate",
            "src/ztare/gates/residual_norm.py",
            "gate",
            "generic_residual_gate()",
            "Residual gate",
            "architecture_index",
            "hard residual repeated branches",
            category="gate",
        ),
        Primitive(
            "ns_residual_manifest",
            "projects/ns_millennium_hunt/workspace/ns_residual_manifest.md",
            "primitive",
            "ns_residual_manifest",
            "NS residual manifest",
            "architecture_index",
            "hard residual repeated branches",
            category="substrate-project",
        ),
    ]
    monkeypatch.setattr(primitive_amnesia, "_semantic_blend", lambda query, inv: {0: 0.70, 1: 0.74})

    ranked = primitive_amnesia.precheck(
        "hard residual with stale repeated branches",
        top_k=2,
        semantic=True,
        inventory=inventory,
    )

    assert ranked[0]["name"] == "generic_residual_gate"
    assert ranked[1]["name"] == "ns_residual_manifest"


def test_precheck_keeps_substrate_artifacts_when_query_names_substrate(monkeypatch) -> None:
    inventory = [
        Primitive(
            "generic_residual_gate",
            "src/ztare/gates/residual_norm.py",
            "gate",
            "generic_residual_gate()",
            "Residual gate",
            "architecture_index",
            "hard residual repeated branches",
            category="gate",
        ),
        Primitive(
            "ns_residual_manifest",
            "projects/ns_millennium_hunt/workspace/ns_residual_manifest.md",
            "primitive",
            "ns_residual_manifest",
            "NS residual manifest",
            "architecture_index",
            "hard residual repeated branches",
            category="substrate-project",
        ),
    ]
    monkeypatch.setattr(primitive_amnesia, "_semantic_blend", lambda query, inv: {0: 0.70, 1: 0.74})

    ranked = primitive_amnesia.precheck(
        "NS hard residual with stale repeated branches",
        top_k=2,
        semantic=True,
        inventory=inventory,
    )

    assert ranked[0]["name"] == "ns_residual_manifest"


def test_precheck_keeps_proof_search_rows_for_solver_queries(monkeypatch) -> None:
    inventory = [
        Primitive(
            "generic_research_ranker",
            "src/ztare/research_director/research_yield_mdl.py",
            "primitive",
            "score_research_avenue(avenue)",
            "Score research avenues",
            "architecture_index",
            "solver move calibrated bandit",
            category="research-operator",
        ),
        Primitive(
            "UCB-MOVE-SCORES",
            "src/ztare/leanmill/solver/move_calibration.py",
            "primitive",
            "ucb_move_scores(priors, visits, costs, c, lam)",
            "PURE UCB blend for move selection",
            "architecture_index",
            "ucb move scores calibrated priors visits",
            category="proof-search",
        ),
    ]
    monkeypatch.setattr(primitive_amnesia, "_semantic_blend", lambda query, inv: {0: 0.70, 1: 0.74})

    ranked = primitive_amnesia.precheck(
        "select which solver move to try next with a calibrated bandit",
        top_k=2,
        semantic=True,
        inventory=inventory,
    )

    assert ranked[0]["name"] == "UCB-MOVE-SCORES"
