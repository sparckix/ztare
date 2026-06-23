import json

from ztare.common import embeddings


def test_build_atlas_manifest_uses_repo_relative_path_for_repo_artifacts(monkeypatch, tmp_path) -> None:
    repo = tmp_path / "repo"
    out_emb = repo / "analytics/public/index/test_atlas_embeddings.json"
    out_manifest = repo / "analytics/public/index/test_atlas_manifest.json"

    monkeypatch.setattr(embeddings, "REPO", repo)
    monkeypatch.setattr(
        embeddings,
        "embed_batch",
        lambda _client, texts, **_kwargs: [[float(i + 1)] for i, _ in enumerate(texts)],
    )

    embeddings.build_atlas(
        [{"id": "row-1", "text": "first row", "title": "First"}],
        out_emb,
        out_manifest,
        dimensions=1,
        client=object(),
        sleep=0,
    )

    manifest = json.loads(out_manifest.read_text(encoding="utf-8"))

    assert manifest["embeddings_file"] == "analytics/public/index/test_atlas_embeddings.json"


def test_build_atlas_manifest_preserves_external_absolute_path(monkeypatch, tmp_path) -> None:
    repo = tmp_path / "repo"
    out_emb = tmp_path / "outside/test_atlas_embeddings.json"
    out_manifest = tmp_path / "outside/test_atlas_manifest.json"

    monkeypatch.setattr(embeddings, "REPO", repo)
    monkeypatch.setattr(
        embeddings,
        "embed_batch",
        lambda _client, texts, **_kwargs: [[float(i + 1)] for i, _ in enumerate(texts)],
    )

    embeddings.build_atlas(
        [{"id": "row-1", "text": "first row"}],
        out_emb,
        out_manifest,
        dimensions=1,
        client=object(),
        sleep=0,
    )

    manifest = json.loads(out_manifest.read_text(encoding="utf-8"))

    assert manifest["embeddings_file"] == str(out_emb)
