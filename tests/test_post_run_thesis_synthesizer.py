from pathlib import Path

from ztare.synthesis import post_run_thesis_synthesizer as post_synth
from ztare.synthesis.iter_extraction import IterRecord
from ztare.synthesis.post_run_thesis_synthesizer import (
    _filter_records_for_synthesis,
    _trim_cluster_to_quality_cap,
    run_post_run_synthesis,
)


def _rec(iter_index: int, score: int) -> IterRecord:
    return IterRecord(
        iter_index=iter_index,
        score=score,
        thesis_md_path=Path(f"iter_{iter_index}.md"),
        meta_path=Path(f"iter_{iter_index}_meta.json"),
    )


def test_post_run_synthesis_filters_seed_and_low_score_records() -> None:
    records = [
        _rec(0, 12),
        _rec(1, 78),
        _rec(2, 46),
        _rec(3, 75),
        _rec(4, 75),
        _rec(5, 25),
        _rec(6, 78),
    ]

    kept = _filter_records_for_synthesis(records, {})

    assert [r.iter_index for r in kept] == [1, 3, 4, 6]


def test_post_run_synthesis_can_include_seed_when_explicitly_configured() -> None:
    records = [_rec(0, 12), _rec(1, 78), _rec(2, 46)]

    kept = _filter_records_for_synthesis(
        records,
        {
            "post_run_synthesis_include_iter0": True,
            "post_run_synthesis_min_score": 1,
        },
    )

    assert [r.iter_index for r in kept] == [0, 1, 2]


def test_post_run_synthesis_trims_broad_transitive_cluster() -> None:
    records_by_iter = {
        1: _rec(1, 78),
        2: _rec(2, 46),
        3: _rec(3, 75),
        4: _rec(4, 75),
        6: _rec(6, 78),
    }

    trimmed = _trim_cluster_to_quality_cap(
        {1, 2, 3, 4, 6},
        records_by_iter,
        {"post_run_synthesis_max_cluster_size": 3},
    )

    assert trimmed == {1, 3, 6}


def test_post_run_synthesis_promotion_baseline_includes_filtered_seed(
    monkeypatch,
    tmp_path: Path,
) -> None:
    project_dir = tmp_path / "demo"
    records = [_rec(0, 95), _rec(1, 80), _rec(2, 82)]
    candidate_path = project_dir / "workspace" / "candidate.md"

    monkeypatch.setattr(
        post_synth,
        "read_iter_records",
        lambda _project_dir, min_records_before_supplement=999: records,
    )
    monkeypatch.setattr(
        post_synth,
        "detect_complementary_pairs",
        lambda _records: [(records[1], records[2])],
    )
    monkeypatch.setattr(post_synth, "cluster_pairs_to_groups", lambda _pairs: [{1, 2}])

    def fake_compose(cluster, records_by_iter):
        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_path.write_text("candidate", encoding="utf-8")
        return candidate_path, records_by_iter[max(cluster)]

    monkeypatch.setattr(post_synth, "compose_candidate_thesis", fake_compose)

    promoted = []
    monkeypatch.setattr(
        post_synth,
        "_promote_synthesis",
        lambda *_args, **_kwargs: promoted.append(True),
    )

    attempts = run_post_run_synthesis(
        project_dir=project_dir,
        rubric_data={},
        judge_invoker=lambda _path: 90,
        margin_threshold=5,
    )

    assert attempts[0].candidate_score == 90
    assert attempts[0].margin == -5
    assert attempts[0].promoted is False
    assert attempts[0].reason == "not_promoted: margin -5 < 5"
    assert promoted == []
