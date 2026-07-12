from __future__ import annotations

import json
from pathlib import Path

from ztare.common.embeddings import cached_text_embeddings, query_atlas


def test_cached_text_embeddings_reuses_disk_vectors(tmp_path: Path) -> None:
    calls = {"n": 0}

    def embedder(text: str) -> list[float]:
        calls["n"] += 1
        return [1.0, 0.0] if "alpha" in text else [0.0, 1.0]

    cache = tmp_path / "vectors.json"
    vecs1, new1, pending1 = cached_text_embeddings(
        ["alpha", "beta"],
        cache_path=cache,
        embedder=embedder,
    )
    vecs2, new2, pending2 = cached_text_embeddings(
        ["alpha", "beta"],
        cache_path=cache,
        embedder=embedder,
    )

    assert vecs1 == [[1.0, 0.0], [0.0, 1.0]]
    assert vecs2 == vecs1
    assert (new1, pending1) == (2, 0)
    assert (new2, pending2) == (0, 0)
    assert calls["n"] == 2


def test_cached_text_embeddings_reports_pending_when_capped(tmp_path: Path) -> None:
    vecs, new, pending = cached_text_embeddings(
        ["a", "b", "c"],
        cache_path=tmp_path / "vectors.json",
        embedder=lambda _text: [1.0],
        max_new=1,
    )

    assert vecs.count(None) == 2
    assert (new, pending) == (1, 2)


def test_cached_text_embeddings_accepts_caller_supplied_cache_keys(tmp_path: Path) -> None:
    cache = tmp_path / "vectors.json"
    cache.write_text(json.dumps({"row-a": [0.25, 0.75]}), encoding="utf-8")
    calls = {"n": 0}

    def embedder(_text: str) -> list[float]:
        calls["n"] += 1
        return [1.0, 0.0]

    vecs, new, pending = cached_text_embeddings(
        ["changed text"],
        cache_path=cache,
        cache_keys=["row-a"],
        embedder=embedder,
    )

    assert vecs == [[0.25, 0.75]]
    assert (new, pending) == (0, 0)
    assert calls["n"] == 0


def test_query_atlas_can_cache_query_embedding(tmp_path: Path) -> None:
    atlas = tmp_path / "atlas.json"
    atlas.write_text(
        json.dumps(
            {
                "model": "fixture-model",
                "dimensions": 2,
                "meta": {"doc-a": {"title": "A"}},
                "embeddings": [{"id": "doc-a", "embedding": [1.0, 0.0]}],
            }
        ),
        encoding="utf-8",
    )
    calls = {"n": 0}

    def fake_embed_batch(_client, texts, **_kwargs):
        calls["n"] += len(texts)
        return [[1.0, 0.0] for _ in texts]

    import ztare.common.embeddings as emb

    old = emb.embed_batch
    try:
        emb.embed_batch = fake_embed_batch
        hits1 = query_atlas(atlas, "alpha query", client="fixture", query_cache_path=tmp_path / "q.json")
        hits2 = query_atlas(atlas, "alpha query", client="fixture", query_cache_path=tmp_path / "q.json")
    finally:
        emb.embed_batch = old

    assert hits1[0]["id"] == "doc-a"
    assert hits2[0]["id"] == "doc-a"
    assert calls["n"] == 1
