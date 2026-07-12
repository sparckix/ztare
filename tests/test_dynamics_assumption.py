"""Tests for substrate-declared dynamics_assumption (temporal admissibility recast).

The t-read ban is now a per-substrate declared assumption, not kernel dogma.
- "markovian" (default): syntactic ban enforced verbatim.
- "lawful_time": ban lifted; anti-memorization discharged by held-out gates.
Env var ZTARE_DYNAMICS_ASSUMPTION overrides rubric/param; absent both = markovian.
"""
from __future__ import annotations

import os
import pytest

from ztare.common.worldmodel_carrier_purity import (
    validate_worldmodel_carrier_source,
    carrier_contract_error,
)

_T_READING_CARRIER = """\
def step(grid, action, t):
    if t == 0:
        return grid
    return grid
"""

_VALID_CARRIER = """\
def step(grid, action, t):
    return grid
"""


# ---------------------------------------------------------------------------
# 1. markovian default — t-reading carrier rejected with updated message
# ---------------------------------------------------------------------------

def test_markovian_default_rejects_t_reading_carrier(monkeypatch):
    monkeypatch.delenv("ZTARE_DYNAMICS_ASSUMPTION", raising=False)
    with pytest.raises(ValueError, match="temporal admissibility reject"):
        validate_worldmodel_carrier_source(_T_READING_CARRIER)


def test_markovian_default_reject_message_includes_opt_out_sentence(monkeypatch):
    monkeypatch.delenv("ZTARE_DYNAMICS_ASSUMPTION", raising=False)
    err = carrier_contract_error(_T_READING_CARRIER)
    assert err is not None
    assert "dynamics_assumption: lawful_time" in err
    assert "held-out gates" in err


# ---------------------------------------------------------------------------
# 2. lawful_time via env — same carrier accepted, proceeds to gates
# ---------------------------------------------------------------------------

def test_lawful_time_env_accepts_t_reading_carrier(monkeypatch):
    monkeypatch.setenv("ZTARE_DYNAMICS_ASSUMPTION", "lawful_time")
    # must not raise
    validate_worldmodel_carrier_source(_T_READING_CARRIER)


def test_lawful_time_env_carrier_contract_error_is_none(monkeypatch):
    monkeypatch.setenv("ZTARE_DYNAMICS_ASSUMPTION", "lawful_time")
    assert carrier_contract_error(_T_READING_CARRIER) is None


# ---------------------------------------------------------------------------
# 3. absent declaration = markovian
# ---------------------------------------------------------------------------

def test_absent_declaration_is_markovian(monkeypatch):
    monkeypatch.delenv("ZTARE_DYNAMICS_ASSUMPTION", raising=False)
    with pytest.raises(ValueError, match="temporal admissibility"):
        validate_worldmodel_carrier_source(_T_READING_CARRIER, dynamics_assumption=None)


# ---------------------------------------------------------------------------
# 4. rubric declaration honored when env absent (param path)
# ---------------------------------------------------------------------------

def test_rubric_lawful_time_param_accepted(monkeypatch):
    monkeypatch.delenv("ZTARE_DYNAMICS_ASSUMPTION", raising=False)
    # simulate gate_harness threading rubric-read value
    validate_worldmodel_carrier_source(_T_READING_CARRIER, dynamics_assumption="lawful_time")


def test_rubric_markovian_param_rejects(monkeypatch):
    monkeypatch.delenv("ZTARE_DYNAMICS_ASSUMPTION", raising=False)
    with pytest.raises(ValueError, match="temporal admissibility"):
        validate_worldmodel_carrier_source(_T_READING_CARRIER, dynamics_assumption="markovian")


# ---------------------------------------------------------------------------
# 5. env overrides rubric param (env wins)
# ---------------------------------------------------------------------------

def test_env_wins_over_param(monkeypatch):
    monkeypatch.setenv("ZTARE_DYNAMICS_ASSUMPTION", "lawful_time")
    # even though param says markovian, env says lawful_time — no error
    validate_worldmodel_carrier_source(_T_READING_CARRIER, dynamics_assumption="markovian")


def test_env_markovian_wins_over_param_lawful_time(monkeypatch):
    monkeypatch.setenv("ZTARE_DYNAMICS_ASSUMPTION", "markovian")
    with pytest.raises(ValueError, match="temporal admissibility"):
        validate_worldmodel_carrier_source(_T_READING_CARRIER, dynamics_assumption="lawful_time")


# ---------------------------------------------------------------------------
# 6. valid carrier always passes regardless of assumption
# ---------------------------------------------------------------------------

def test_valid_carrier_passes_markovian(monkeypatch):
    monkeypatch.delenv("ZTARE_DYNAMICS_ASSUMPTION", raising=False)
    validate_worldmodel_carrier_source(_VALID_CARRIER)


def test_valid_carrier_passes_lawful_time(monkeypatch):
    monkeypatch.setenv("ZTARE_DYNAMICS_ASSUMPTION", "lawful_time")
    validate_worldmodel_carrier_source(_VALID_CARRIER)
