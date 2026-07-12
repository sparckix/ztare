"""Tests for src/ztare/common/pricing_calibration.py (Finding 7)."""

import json
import math
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.ztare.common.pricing_calibration import (
    calibration_report,
    dedup_predictive_mass,
    quoted_bits,
    record_calibration,
)
from src.ztare.common.information_yield_pricing import identification_bits
sys.path.insert(0, str(_ROOT / "scripts" / "public" / "validators"))
from collision_table import build_collision_table  # type: ignore[import]


# ---------------------------------------------------------------------------
# dedup_predictive_mass
# ---------------------------------------------------------------------------

def test_dedup_collapses_clones():
    """Three members with the same prediction → one representative."""
    pairs = [("m1", "pred_A"), ("m2", "pred_A"), ("m3", "pred_A")]
    result = dedup_predictive_mass(pairs)
    assert len(result) == 1
    assert result[0] == ("m1", "pred_A")


def test_dedup_distinct_preds_unchanged():
    pairs = [("m1", "X"), ("m2", "Y"), ("m3", "Z")]
    result = dedup_predictive_mass(pairs)
    assert len(result) == 3


def test_dedup_mixed_clones_and_distinct():
    """Two distinct classes, one duplicated."""
    pairs = [("a", "p1"), ("b", "p2"), ("c", "p1"), ("d", "p2")]
    result = dedup_predictive_mass(pairs)
    assert len(result) == 2
    preds = {r[1] for r in result}
    assert preds == {"p1", "p2"}


def test_dedup_list_predictions_by_content():
    """List predictions with the same content should collapse."""
    pairs = [("m1", [1, 2, 3]), ("m2", [1, 2, 3]), ("m3", [4, 5, 6])]
    result = dedup_predictive_mass(pairs)
    assert len(result) == 2


def test_dedup_empty():
    assert dedup_predictive_mass([]) == []


# ---------------------------------------------------------------------------
# unknown_model_mass scaling
# ---------------------------------------------------------------------------

def _uniform_cells(n: int) -> dict:
    """n equally-sized cells of 1 member each."""
    return {i: [f"m{i}"] for i in range(n)}


def test_quoted_bits_lower_than_raw():
    """quoted_bits must be strictly below raw identification_bits when mass > 0."""
    cells = _uniform_cells(4)
    raw = identification_bits(cells, 4)
    q = quoted_bits(cells, 4, unknown_model_mass=0.2)
    assert q == pytest.approx(raw * 0.8)
    assert q < raw


def test_quoted_bits_zero_mass_equals_raw():
    cells = _uniform_cells(4)
    raw = identification_bits(cells, 4)
    q = quoted_bits(cells, 4, unknown_model_mass=0.0)
    assert q == pytest.approx(raw)


def test_quoted_bits_env_var(monkeypatch):
    monkeypatch.setenv("ZTARE_UNKNOWN_MODEL_MASS", "0.5")
    cells = _uniform_cells(4)
    raw = identification_bits(cells, 4)
    q = quoted_bits(cells, 4)  # should read env
    assert q == pytest.approx(raw * 0.5)


def test_quoted_bits_single_cell_is_zero():
    """A fully-merged committee has zero entropy regardless of mass."""
    cells = {0: ["m1", "m2", "m3"]}
    q = quoted_bits(cells, 3, unknown_model_mass=0.2)
    assert q == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# calibration ledger
# ---------------------------------------------------------------------------

def test_record_and_report(tmp_path):
    proj = tmp_path / "project"
    record_calibration(proj, quoted_bits_value=1.5, realized_survivor_reduction=0.4)
    record_calibration(proj, quoted_bits_value=0.8, realized_survivor_reduction=0.9)
    report = calibration_report(proj)
    assert report["n_rows"] == 2
    assert report["mean_quoted_bits"] == pytest.approx(1.15, rel=1e-4)
    assert report["mean_realized_reduction"] == pytest.approx(0.65, rel=1e-4)
    # First row: 1.5 > 0.4 (overquote); second: 0.8 < 0.9 (not). → 50 %
    assert report["overquote_fraction"] == pytest.approx(0.5)


def test_report_no_ledger(tmp_path):
    report = calibration_report(tmp_path / "empty_proj")
    assert report["n_rows"] == 0
    assert "honest_note" in report


def test_report_tiny_corpus_note(tmp_path):
    proj = tmp_path / "p"
    record_calibration(proj, 1.0, 0.5)
    report = calibration_report(proj)
    assert "thin" in report["honest_note"]


def test_ledger_is_jsonl(tmp_path):
    proj = tmp_path / "p"
    record_calibration(proj, 1.0, 0.5)
    record_calibration(proj, 0.5, 0.3)
    lines = (proj / "workspace" / "pricing_calibration.jsonl").read_text().strip().splitlines()
    assert len(lines) == 2
    for line in lines:
        row = json.loads(line)
        assert "quoted_bits" in row
        assert "realized_survivor_reduction" in row


# ---------------------------------------------------------------------------
# collision_table: Finding 4
# ---------------------------------------------------------------------------

def _write_episode(project_dir: Path, name: str, rows: list[dict]) -> None:
    ep_dir = project_dir / "raw" / "episodes"
    ep_dir.mkdir(parents=True, exist_ok=True)
    with (ep_dir / name).open("w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def test_collision_table_clean_data_no_collisions(tmp_path):
    """Episode with no (s,a,t) conflicts → n_collisions == 0."""
    proj = tmp_path / "clean"
    rows = [
        {"t": i, "s": [i], "a": 0, "s_next": [i + 1]}
        for i in range(10)
    ]
    _write_episode(proj, "episode_001.jsonl", rows)
    result = build_collision_table(proj)
    assert result["n_collisions"] == 0
    assert result["n_rows"] == 10
    assert "support-local Markov consistency" in result["verdict"]


def test_collision_table_detects_collision(tmp_path):
    """Same (s, a, t) in two episodes but different s_next → collision detected."""
    proj = tmp_path / "collide"
    s = [[1, 2], [3, 4]]
    rows_ep1 = [{"t": 0, "s": s, "a": 1, "s_next": [[0, 0], [0, 0]]}]
    rows_ep2 = [{"t": 0, "s": s, "a": 1, "s_next": [[9, 9], [9, 9]]}]
    _write_episode(proj, "episode_001.jsonl", rows_ep1)
    _write_episode(proj, "episode_002.jsonl", rows_ep2)
    result = build_collision_table(proj)
    assert result["n_collisions"] > 0
    assert "not supported" in result["verdict"]


def test_collision_table_history_divergent(tmp_path):
    """Collision where preceding rows differ → history_divergent flag set."""
    proj = tmp_path / "hist_div"
    s = [[5, 5]]
    # episode 1: preceded by row [0] → prev_hash A
    rows_ep1 = [
        {"t": 0, "s": [[0]], "a": 0, "s_next": [[1]]},  # different preceding row
        {"t": 1, "s": s, "a": 2, "s_next": [[0, 0]]},
    ]
    # episode 2: preceded by row [99] → prev_hash B
    rows_ep2 = [
        {"t": 0, "s": [[99]], "a": 0, "s_next": [[88]]},  # different preceding row
        {"t": 1, "s": s, "a": 2, "s_next": [[7, 7]]},    # same (s,a,t) different s_next
    ]
    _write_episode(proj, "episode_001.jsonl", rows_ep1)
    _write_episode(proj, "episode_002.jsonl", rows_ep2)
    result = build_collision_table(proj)
    assert result["n_history_divergent_collisions"] > 0


def test_collision_table_same_s_next_no_collision(tmp_path):
    """Two episodes with same (s,a,t) AND same s_next → not a collision."""
    proj = tmp_path / "agree"
    s = [[3, 3]]
    rows = [{"t": 0, "s": s, "a": 1, "s_next": [[4, 4]]}]
    _write_episode(proj, "episode_001.jsonl", rows)
    _write_episode(proj, "episode_002.jsonl", rows)
    result = build_collision_table(proj)
    assert result["n_collisions"] == 0


def test_collision_table_empty_project(tmp_path):
    """Project with no episode files → zero rows, no collisions."""
    proj = tmp_path / "empty"
    (proj / "raw" / "episodes").mkdir(parents=True)
    result = build_collision_table(proj)
    assert result["n_rows"] == 0
    assert result["n_collisions"] == 0
