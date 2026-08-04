from __future__ import annotations

import importlib.util
from pathlib import Path


def _load():
    path = (
        Path(__file__).resolve().parents[1]
        / "scripts/public/control/"
        "arc3_response_transport_square_probe.py"
    )
    spec = importlib.util.spec_from_file_location(
        "arc3_response_transport_square_probe_under_test",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_h95_saved_result_replays_without_environment_contact() -> None:
    module = _load()
    result_path = (
        Path(__file__).resolve().parents[1]
        / "research_areas/pre_registrations/"
        "arc3_consumer_indexed_exception_frontier_20260723/"
        "h95_response_transport_square/result.json"
    )

    replay = module.verify_saved_result(result_path)

    assert replay["status"] == "offline_replay_verified"
    assert replay["pair_count"] == 2
    assert replay["candidate_count"] == 4
    assert replay["mean_offer_minus_withhold_composite"] > 0.0
