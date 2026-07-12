"""Planted tests for the substrate-generic evidence quotients."""

import pytest

from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.evidence_quotients import (
    cap_events,
    episode_contrast,
    event_timeline,
    resolve_episode_ref,
)


def _log_a() -> EpisodeLog:
    g0 = ((1, 1, 0), (0, 0, 0), (0, 0, 2))
    g1 = ((1, 0, 0), (0, 0, 0), (0, 0, 2))  # (0,1): 1 -> 0
    g2 = ((0, 0, 0), (0, 3, 0), (0, 0, 2))  # (0,0): 1 -> 0 and (1,1): 0 -> 3
    log = EpisodeLog()
    log.append(g0, 1, g1)  # t=0
    log.append(g1, 2, g2)  # t=1
    log.append(g2, 1, g2)  # t=2, no change
    return log


def _log_b() -> EpisodeLog:
    g0 = ((1, 1, 0), (0, 0, 0), (5, 5, 5))
    g1 = ((1, 1, 0), (0, 4, 0), (5, 5, 5))
    log = EpisodeLog()
    log.append(g0, 3, g1)  # t=0
    return log


def test_event_timeline_groups_matching_cell_changes():
    out = event_timeline(
        _log_a(), cell_predicate_spec={"before_in": [1], "after_not_in": [3]}
    )
    assert out["events"] == [
        {"t": 0, "a": 1, "cells": [{"row": 0, "col": 1, "before": 1, "after": 0}], "count": 1},
        {"t": 1, "a": 2, "cells": [{"row": 0, "col": 0, "before": 1, "after": 0}], "count": 1},
    ]
    assert out["counts_by_t"] == {0: 1, 1: 1}
    assert out["distinct_cells"] == 2
    assert out["rate_series"] == [1, 1, 0]


def test_event_timeline_changed_form_counts_all_changes():
    out = event_timeline(_log_a(), cell_predicate_spec={"changed": True})
    assert out["rate_series"] == [1, 2, 0]
    assert out["distinct_cells"] == 3
    assert [row["count"] for row in out["events"]] == [1, 2]


def test_event_timeline_unknown_spec_key_raises():
    with pytest.raises(ValueError, match="bogus"):
        event_timeline(_log_a(), cell_predicate_spec={"before_in": [1], "bogus": 1})
    with pytest.raises(ValueError, match="non-empty"):
        event_timeline(_log_a(), cell_predicate_spec={})


def test_episode_contrast_census_and_rows():
    out = episode_contrast(_log_a(), _log_b())
    assert out["status"] == "ok"
    assert out["color_census_a"] == {0: 6, 1: 2, 2: 1}
    assert out["color_census_b"] == {0: 4, 1: 2, 5: 3}
    assert out["census_delta"] == {0: -2, 2: -1, 5: 3}
    assert out["rows_differing"] == [2]
    assert out["shape_a"] == [3, 3] and out["shape_b"] == [3, 3]


def test_episode_contrast_missing_t_is_loud():
    out = episode_contrast(_log_a(), _log_b(), at_t=2)
    assert out["status"] == "missing_t"
    assert out["missing_in"] == ["b"]
    assert "t=2" in out["errors"]["b"]
    assert "available" in out["errors"]["b"]


def test_cap_events_truncates_loudly():
    payload = {"events": [{"t": i} for i in range(250)], "rate_series": []}
    out = cap_events(payload, cap=200)
    assert len(out["events"]) == 200
    assert "50 dropped" in out["events_truncated"]
    untouched = cap_events({"events": [{"t": 0}]}, cap=200)
    assert "events_truncated" not in untouched


def test_resolve_episode_ref_unknown_names_valid_refs(tmp_path):
    episodes = tmp_path / "raw" / "episodes"
    episodes.mkdir(parents=True)
    _log_a().write_jsonl(episodes / "episode_001.jsonl")
    assert resolve_episode_ref(tmp_path, "visible") == (episodes / "episode_001.jsonl").resolve()
    with pytest.raises(ValueError, match="episode_001"):
        resolve_episode_ref(tmp_path, "holdout")  # file absent -> loud, names valid refs
    with pytest.raises(ValueError, match="not under raw/episodes"):
        resolve_episode_ref(tmp_path, "workspace/other.jsonl")


def test_strategy_battery_menu_exposes_evidence_quotients(tmp_path):
    from ztare.worldmodel.strategy_battery import WorldmodelBattery

    menu = WorldmodelBattery().query_menu()
    assert "event_timeline" in menu and "episode_contrast" in menu
    episodes = tmp_path / "raw" / "episodes"
    episodes.mkdir(parents=True)
    _log_a().write_jsonl(episodes / "episode_001.jsonl")
    _log_b().write_jsonl(episodes / "episode_002.jsonl")
    _desc, fn = menu["event_timeline"]
    out = fn(tmp_path, episode="visible", spec='{"changed": true}')
    assert out["rate_series"] == [1, 2, 0]
    _desc, fn = menu["episode_contrast"]
    out = fn(tmp_path)
    assert out["census_delta"] == {0: -2, 2: -1, 5: 3}
