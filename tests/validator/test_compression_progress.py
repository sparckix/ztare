from ztare.validator.core.compression_progress import (
    CompressionObservation,
    dag_description_length,
    evaluate_compression_progress,
    observations_from_rows,
)


def test_dag_description_length_two_part_mdl() -> None:
    # More structure explaining the SAME outcome costs more bits; explaining the target better costs fewer.
    base = dag_description_length({"nodes": [{"id": "a"}, {"id": "b"}], "edges": [{}], "outcome": {"probability": 0.5}})
    bigger = dag_description_length({"nodes": [{"id": "a"}, {"id": "b"}, {"id": "c"}], "edges": [{}, {}], "outcome": {"probability": 0.5}})
    better = dag_description_length({"nodes": [{"id": "a"}, {"id": "b"}], "edges": [{}], "outcome": {"probability": 0.95}})
    assert bigger > base          # added structure, same fit → higher complexity
    assert better < base          # same structure, better fit → lower complexity
    # No usable outcome probability, or empty graph → no reading (None), never a crash.
    assert dag_description_length({"nodes": [{"id": "a"}], "edges": []}) is None
    assert dag_description_length({"nodes": [], "edges": [], "outcome": {"probability": 0.7}}) is None
    assert dag_description_length("not a dag") is None


def test_recent_compression_drop_recommends_continue() -> None:
    decision = evaluate_compression_progress([
        CompressionObservation(iteration_index=0, complexity=120.0),
        CompressionObservation(iteration_index=1, complexity=100.0),
        CompressionObservation(iteration_index=2, complexity=99.0),
    ])

    assert decision.recommendation == "continue"
    assert decision.last_drop_iteration == 2
    assert decision.stagnation_length == 0
    assert decision.future_progress_weight == 1.0


def test_long_flat_compression_history_recommends_narrow_or_pivot() -> None:
    decision = evaluate_compression_progress([
        CompressionObservation(iteration_index=0, complexity=120.0),
        CompressionObservation(iteration_index=1, complexity=100.0),
        CompressionObservation(iteration_index=2, complexity=100.5, novelty=True),
        CompressionObservation(iteration_index=3, complexity=101.0, novelty=True),
        CompressionObservation(iteration_index=4, complexity=100.2, novelty=True),
    ])

    assert decision.recommendation == "narrow_or_pivot"
    assert decision.last_drop_iteration == 1
    assert decision.stagnation_length == 3
    assert decision.future_progress_weight == 0.125


def test_existing_rows_feed_compression_observations_without_using_score() -> None:
    rows = [
        {"iteration_index": 3, "score": 80, "best_bic": 45.0, "wall_clock_seconds": 12.5},
        {"iteration_index": 4, "score": 95, "best_bic": 45.5, "novel_attack_ids": ["a"], "wall_clock_seconds": 15.0},
        {"iteration_index": 5, "score": 99},
    ]

    observations = observations_from_rows(rows)

    assert [item.iteration_index for item in observations] == [3, 4, 5]
    assert [item.complexity for item in observations] == [45.0, 45.5, None]
    assert observations[0].effort == 12.5
    assert observations[0].effort_unit == "seconds"
    assert observations[1].novelty is True
