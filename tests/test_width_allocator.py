"""Tests for ztare.common.width_allocator.

10+ tests covering monotonicity, stagnation, env override, bounds,
receipt schema, and determinism.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure src is on path when running directly
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ztare.common.width_allocator import (
    RECEIPT_SCHEMA,
    _MAX_SHARDS,
    _MIN_SHARDS,
    _compute_shards,
    _stagnation,
    _unexplained_holdout_bits,
    allocate_width,
)
from ztare.worldmodel.carrier_loader import (
    resolve_current_carrier_evidence_identity,
)


# ── Fixtures ───────────────────────────────────────────────────────────────────


def _make_project(
    *,
    holdout_depth: int = 0,
    holdout_total: int | None = None,
    promotions: int = 0,
    non_promotions: int = 0,
    eliminations: int = 0,
) -> Path:
    """Build a minimal project dir with controlled receipt files."""
    tmp = Path(tempfile.mkdtemp())
    ws = tmp / "workspace"
    ws.mkdir()

    (tmp / "test_model.py").write_text("VALUE = 1\n", encoding="utf-8")
    episodes = tmp / "raw" / "episodes"
    episodes.mkdir(parents=True)
    (episodes / "episode_001.jsonl").write_text('{"r":0}\n')
    if holdout_total is not None:
        (episodes / "episode_002.jsonl").write_text(
            "".join('{"r":%d}\n' % i for i in range(holdout_total))
        )
    identity = resolve_current_carrier_evidence_identity(tmp)
    binding = identity.to_dict()

    # candidate_memory.json
    failed_gates = []
    if holdout_total is not None:
        failed_gates = [f"holdout_rollout_exact: {holdout_total}"]
    record = {
        "sha": identity.carrier_sha256,
        "evidence_epoch_sha256": identity.evidence_epoch_sha256,
        "holdout_depth": holdout_depth,
        "counterexample_trace": {
            "failed_gates": failed_gates,
            "holdout_total": None,
        },
    }
    (ws / "candidate_memory.json").write_text(json.dumps({"records": [record]}))

    # champion_materialization.jsonl
    cm_rows = []
    for _ in range(promotions):
        cm_rows.append(json.dumps({
            "promoted_sha": identity.carrier_sha256,
            "result": "promoted",
            "carrier_evidence_identity": binding,
        }))
    for _ in range(non_promotions):
        cm_rows.append(json.dumps({
            "result": "no_change",
            "carrier_evidence_identity": binding,
        }))
    (ws / "champion_materialization.jsonl").write_text("\n".join(cm_rows) + "\n")

    # residual_specialists.jsonl — with or without eliminations
    rs_rows = []
    dispatches = []
    for i in range(eliminations):
        dispatches.append({"class_id": f"cls_{i}", "eliminated_family": f"fam_{i}"})
    if dispatches or True:  # always write at least empty
        rs_rows.append(json.dumps({
            "_schema": "ztare.residual_specialists.v1",
            "dispatches": dispatches,
            "carrier_evidence_identity": binding,
        }))
    (ws / "residual_specialists.jsonl").write_text("\n".join(rs_rows) + "\n")

    return tmp


# ── Monotonicity ───────────────────────────────────────────────────────────────


def test_more_unexplained_bits_ge_width():
    """More unexplained holdout bits → at least as many shards."""
    low = _compute_shards(unexplained=1, holdout_total=None, elimination_rate=0, stagnation=0)
    high = _compute_shards(unexplained=8, holdout_total=None, elimination_rate=0, stagnation=0)
    assert high >= low


def test_quiescence_depth_equals_total():
    """depth == holdout_total → 1 shard (champion solved everything)."""
    shards = _compute_shards(unexplained=0, holdout_total=5, elimination_rate=0, stagnation=0)
    assert shards == 1


def test_quiescence_via_allocate_width(tmp_path):
    """allocate_width returns shards=1 when champion is at quiescence."""
    proj = _make_project(holdout_depth=5, holdout_total=5)
    result = allocate_width(proj)
    assert result["signals"]["holdout_total"] == 5
    assert result["shards"] == 1


def test_zero_unexplained_low_width():
    """Zero unexplained bits → width 1 (nothing to explore)."""
    shards = _compute_shards(unexplained=0, holdout_total=None, elimination_rate=0, stagnation=0)
    assert shards == _MIN_SHARDS


# ── Stagnation ─────────────────────────────────────────────────────────────────


def test_stagnation_escalates_samples():
    """stagnation >= 2 → samples_per_shard=2."""
    proj = _make_project(holdout_depth=4, non_promotions=3)
    result = allocate_width(proj)
    assert result["samples_per_shard"] == 2


def test_stagnation_low_keeps_samples_1():
    """stagnation < 2 → samples_per_shard=1."""
    proj = _make_project(holdout_depth=4, promotions=2, non_promotions=0)
    result = allocate_width(proj)
    assert result["samples_per_shard"] == 1


def test_stagnation_3_escalates_effort():
    """stagnation >= 3 → effort 'medium' (capped by default ceiling)."""
    proj = _make_project(holdout_depth=4, non_promotions=4)
    result = allocate_width(proj)
    assert result["effort"] == "medium"


def test_stagnation_1_keeps_effort_low():
    """stagnation < 3 → effort 'low'."""
    proj = _make_project(holdout_depth=4, promotions=1, non_promotions=1)
    result = allocate_width(proj)
    assert result["effort"] == "low"


# ── Env override ───────────────────────────────────────────────────────────────


def test_env_max_shards_wins(monkeypatch):
    """ZTARE_SPECIALIST_MAX_SHARDS env var overrides policy shards."""
    monkeypatch.setenv("ZTARE_SPECIALIST_MAX_SHARDS", "3")
    proj = _make_project(holdout_depth=10, non_promotions=5)
    result = allocate_width(proj)
    assert result["shards"] == 3
    monkeypatch.delenv("ZTARE_SPECIALIST_MAX_SHARDS", raising=False)


def test_effort_ceiling_env(monkeypatch):
    """ZTARE_ALLOCATOR_EFFORT_CEILING='low' caps effort at low."""
    monkeypatch.setenv("ZTARE_ALLOCATOR_EFFORT_CEILING", "low")
    proj = _make_project(holdout_depth=4, non_promotions=4)  # stag>=3 → would be medium
    result = allocate_width(proj)
    assert result["effort"] == "low"
    monkeypatch.delenv("ZTARE_ALLOCATOR_EFFORT_CEILING", raising=False)


# ── Hard bounds ────────────────────────────────────────────────────────────────


def test_shards_never_exceed_max():
    shards = _compute_shards(unexplained=100, holdout_total=None, elimination_rate=0, stagnation=10)
    assert shards <= _MAX_SHARDS


def test_shards_never_below_min():
    shards = _compute_shards(unexplained=0, holdout_total=None, elimination_rate=10, stagnation=0)
    assert shards >= _MIN_SHARDS


def test_env_max_clamped_to_bounds(monkeypatch):
    """ZTARE_SPECIALIST_MAX_SHARDS=99 is clamped to _MAX_SHARDS."""
    monkeypatch.setenv("ZTARE_SPECIALIST_MAX_SHARDS", "99")
    proj = _make_project()
    result = allocate_width(proj)
    assert result["shards"] <= _MAX_SHARDS
    monkeypatch.delenv("ZTARE_SPECIALIST_MAX_SHARDS", raising=False)


# ── Receipt schema ─────────────────────────────────────────────────────────────


def test_receipt_written_and_schema():
    """allocate_width writes a receipt row with correct schema."""
    proj = _make_project(holdout_depth=2)
    allocate_width(proj)
    rows = [json.loads(l) for l in (proj / "workspace" / "width_allocations.jsonl").read_text().splitlines() if l.strip()]
    assert rows, "no receipt rows written"
    row = rows[-1]
    assert row["schema"] == RECEIPT_SCHEMA
    assert "signals" in row
    assert "decision" in row
    assert "rationale" in row


def test_receipt_signals_keys():
    """Receipt row has the four canonical signal keys."""
    proj = _make_project(holdout_depth=3, holdout_total=10)
    allocate_width(proj)
    rows = [json.loads(l) for l in (proj / "workspace" / "width_allocations.jsonl").read_text().splitlines() if l.strip()]
    sig = rows[-1]["signals"]
    assert "unexplained_holdout_bits" in sig
    assert "holdout_total" in sig
    assert "recent_elimination_rate" in sig
    assert "stagnation" in sig
    assert sig["identity_status"] == "current"


def test_prefix_and_unrelated_max_record_cannot_allocate_width():
    proj = _make_project(holdout_depth=3, holdout_total=10)
    memory = proj / "workspace" / "candidate_memory.json"
    payload = json.loads(memory.read_text())
    current = payload["records"][0]
    current["sha"] = current["sha"][:12]
    payload["records"].append({
        "sha": "f" * 64,
        "evidence_epoch_sha256": current["evidence_epoch_sha256"],
        "holdout_depth": 999,
    })
    memory.write_text(json.dumps(payload))

    assert _unexplained_holdout_bits(proj) == (1, None)


def test_evidence_change_makes_prior_width_receipts_historical():
    proj = _make_project(holdout_depth=3, holdout_total=10)
    (proj / "raw" / "episodes" / "episode_001.jsonl").write_text('{"new":1}\n')

    result = allocate_width(proj)

    assert result["signals"]["identity_status"] == "current"
    assert result["signals"]["unexplained_holdout_bits"] == 1


# ── Determinism ────────────────────────────────────────────────────────────────


def test_pure_given_fixture(tmp_path):
    """Two calls on same fixture files return identical shards/effort/samples."""
    proj = _make_project(holdout_depth=3, holdout_total=10, non_promotions=2)
    r1 = allocate_width(proj)
    r2 = allocate_width(proj)
    assert r1["shards"] == r2["shards"]
    assert r1["effort"] == r2["effort"]
    assert r1["samples_per_shard"] == r2["samples_per_shard"]
