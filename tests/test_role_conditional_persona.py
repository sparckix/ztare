"""Tests for role-conditional persona selection (select_persona).

Covers:
- Legacy rubric (persona-only) → same string for both DISCOVERY and EVALUATION
- personas dict → correct text per role
- HARNESS_DEBUG → discovery text
- Missing role key in personas dict → fallback to other key (logged)
- Both personas + persona present → personas wins
"""
import pytest
from ztare.common.cegis_membrane import DISCOVERY, EVALUATION, HARNESS_DEBUG, select_persona


DISCOVERY_TEXT = "You are a natural scientist discovering laws from evidence."
EVALUATION_TEXT = "You are an adversarial reviewer. Find flaws."
LEGACY_TEXT = "You are a static rubric persona."


def _rubric_legacy():
    return {"persona": LEGACY_TEXT}


def _rubric_personas():
    return {"personas": {"discovery": DISCOVERY_TEXT, "evaluation": EVALUATION_TEXT}}


def _rubric_both():
    return {
        "persona": LEGACY_TEXT,
        "personas": {"discovery": DISCOVERY_TEXT, "evaluation": EVALUATION_TEXT},
    }


def _rubric_personas_only_discovery():
    return {"personas": {"discovery": DISCOVERY_TEXT}}


def _rubric_personas_only_evaluation():
    return {"personas": {"evaluation": EVALUATION_TEXT}}


def _rubric_empty():
    return {}


# --- legacy fallback ---

def test_legacy_discovery():
    assert select_persona(_rubric_legacy(), DISCOVERY) == LEGACY_TEXT


def test_legacy_evaluation():
    assert select_persona(_rubric_legacy(), EVALUATION) == LEGACY_TEXT


def test_legacy_harness_debug():
    assert select_persona(_rubric_legacy(), HARNESS_DEBUG) == LEGACY_TEXT


# --- personas dict selects by role ---

def test_personas_discovery(capsys):
    result = select_persona(_rubric_personas(), DISCOVERY)
    assert result == DISCOVERY_TEXT
    captured = capsys.readouterr()
    assert "discovery" in captured.out


def test_personas_evaluation(capsys):
    result = select_persona(_rubric_personas(), EVALUATION)
    assert result == EVALUATION_TEXT
    captured = capsys.readouterr()
    assert "evaluation" in captured.out


def test_personas_harness_debug_maps_to_discovery(capsys):
    """HARNESS_DEBUG is treated as DISCOVERY for persona selection."""
    result = select_persona(_rubric_personas(), HARNESS_DEBUG)
    assert result == DISCOVERY_TEXT
    captured = capsys.readouterr()
    assert "discovery" in captured.out


# --- personas wins over legacy persona ---

def test_personas_wins_over_legacy():
    result = select_persona(_rubric_both(), DISCOVERY)
    assert result == DISCOVERY_TEXT
    assert result != LEGACY_TEXT


def test_personas_wins_over_legacy_eval():
    result = select_persona(_rubric_both(), EVALUATION)
    assert result == EVALUATION_TEXT
    assert result != LEGACY_TEXT


# --- missing role key falls back to other key with logged note ---

def test_missing_evaluation_key_falls_back_to_discovery(capsys):
    rubric = _rubric_personas_only_discovery()
    result = select_persona(rubric, EVALUATION)
    assert result == DISCOVERY_TEXT
    captured = capsys.readouterr()
    assert "falling back" in captured.out


def test_missing_discovery_key_falls_back_to_evaluation(capsys):
    rubric = _rubric_personas_only_evaluation()
    result = select_persona(rubric, DISCOVERY)
    assert result == EVALUATION_TEXT
    captured = capsys.readouterr()
    assert "falling back" in captured.out


# --- personas dict present but both keys absent → falls through to legacy ---

def test_personas_empty_dict_falls_back_to_legacy():
    rubric = {"personas": {}, "persona": LEGACY_TEXT}
    assert select_persona(rubric, DISCOVERY) == LEGACY_TEXT


# --- fully empty rubric → empty string ---

def test_empty_rubric():
    assert select_persona(_rubric_empty(), DISCOVERY) == ""
    assert select_persona(_rubric_empty(), EVALUATION) == ""


# --- real-artifact: selector returns each stance by role ---

def test_real_artifact_selector():
    """Verify the selector round-trips: discovery→D text, evaluation→E text."""
    rubric = {
        "persona": LEGACY_TEXT,
        "personas": {"discovery": DISCOVERY_TEXT, "evaluation": EVALUATION_TEXT},
    }
    d = select_persona(rubric, DISCOVERY)
    e = select_persona(rubric, EVALUATION)
    hd = select_persona(rubric, HARNESS_DEBUG)

    assert d == DISCOVERY_TEXT
    assert e == EVALUATION_TEXT
    assert hd == DISCOVERY_TEXT   # HARNESS_DEBUG → discovery
    assert d != e                 # stances differ
