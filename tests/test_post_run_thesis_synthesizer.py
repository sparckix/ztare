from pathlib import Path

from src.ztare.synthesis.iter_extraction import IterRecord
from src.ztare.synthesis.post_run_thesis_synthesizer import (
    _filter_records_for_synthesis,
    _trim_cluster_to_quality_cap,
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
