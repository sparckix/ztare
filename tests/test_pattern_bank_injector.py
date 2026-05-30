"""Unit tests for I-5 pattern-bank injector."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ztare.research_director.pattern_bank_injector import (
    MODE_B_CLASS,
    evaluate_injection,
)


@pytest.fixture
def bank_dir(tmp_path: Path) -> Path:
    bank = tmp_path / "bank"
    bank.mkdir()
    (bank / "catastrophic_fit_failure.md").write_text(
        "# header to be stripped\n\n_metadata block_\n\n## Mechanism\n\nbody starts here.\n\nmore body."
    )
    (bank / "missing_mechanism.md").write_text(
        "# header\n\n## Mechanism\n\nthis is a different class body."
    )
    return bank


@pytest.fixture
def log_path(tmp_path: Path) -> Path:
    return tmp_path / "operator_overrides.jsonl"


def test_off_returns_no_injection(bank_dir, log_path):
    out = evaluate_injection(
        rubric={"inject_pattern_bank": False},
        last_weakest_class="catastrophic_fit_failure",
        bank_dir=bank_dir,
        override_log_path=log_path,
    )
    assert out["fired"] is False
    assert not log_path.exists()


def test_manual_mode_injects_named_class(bank_dir, log_path):
    out = evaluate_injection(
        rubric={"inject_pattern_bank": {"mode": "manual", "class": "missing_mechanism"}},
        last_weakest_class=None,
        project="test",
        iteration=3,
        bank_dir=bank_dir,
        override_log_path=log_path,
    )
    assert out["fired"] is True
    assert out["class"] == "missing_mechanism"
    assert "different class body" in out["body"]
    assert log_path.exists()
    rec = json.loads(log_path.read_text().strip().splitlines()[-1])
    assert rec["intervention"] == "I-5_pattern_bank"
    assert rec["source"] == "manual"
    assert rec["class"] == "missing_mechanism"


def test_auto_mode_fires_only_on_matching_class(bank_dir, log_path):
    rubric = {"inject_pattern_bank": {"mode": "auto_catastrophic_fit"}}
    out_no = evaluate_injection(
        rubric=rubric,
        last_weakest_class="missing_mechanism",
        bank_dir=bank_dir,
        override_log_path=log_path,
    )
    assert out_no["fired"] is False
    assert not log_path.exists()
    out_yes = evaluate_injection(
        rubric=rubric,
        last_weakest_class=MODE_B_CLASS,
        project="p",
        iteration=5,
        bank_dir=bank_dir,
        override_log_path=log_path,
    )
    assert out_yes["fired"] is True
    assert out_yes["class"] == MODE_B_CLASS
    assert "body starts here" in out_yes["body"]
    rec = json.loads(log_path.read_text().strip().splitlines()[-1])
    assert rec["source"] == "auto_catastrophic_fit"


def test_missing_bank_file_skips(bank_dir, log_path):
    out = evaluate_injection(
        rubric={"inject_pattern_bank": {"mode": "manual", "class": "nonexistent_class"}},
        last_weakest_class=None,
        bank_dir=bank_dir,
        override_log_path=log_path,
    )
    assert out["fired"] is False
    # No log line should be appended on a skip.
    assert not log_path.exists() or log_path.read_text().strip() == ""


def test_string_shorthand_off(bank_dir, log_path):
    out = evaluate_injection(
        rubric={"inject_pattern_bank": "off"},
        last_weakest_class=MODE_B_CLASS,
        bank_dir=bank_dir,
        override_log_path=log_path,
    )
    assert out["fired"] is False


def test_dry_run_does_not_write_log(bank_dir, log_path):
    out = evaluate_injection(
        rubric={"inject_pattern_bank": {"mode": "manual", "class": "missing_mechanism"}},
        last_weakest_class=None,
        bank_dir=bank_dir,
        override_log_path=log_path,
        write_log=False,
    )
    assert out["fired"] is True
    assert not log_path.exists()


def test_cross_llm_footer_present(bank_dir, log_path):
    out = evaluate_injection(
        rubric={"inject_pattern_bank": {"mode": "manual", "class": "missing_mechanism"}},
        last_weakest_class=None,
        bank_dir=bank_dir,
        override_log_path=log_path,
        write_log=False,
    )
    assert "cross-LLM stability 0.538" in out["body"]
