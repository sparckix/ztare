from __future__ import annotations

import json
from pathlib import Path

from src.ztare.reports.rubric_mode_corpus_audit import (
    audit_rubric_mode_corpus,
    main,
    render_text,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


def _write_charter(repo: Path, project: str, text: str) -> None:
    path = repo / "projects" / project / "project_charter.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_eval_history(repo: Path, project: str, rows: list[dict]) -> None:
    path = repo / "projects" / project / "workspace" / "eval_history.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _row(report: dict, rubric_path: str) -> dict:
    return next(row for row in report["rows"] if row["rubric_path"] == rubric_path)


def test_corpus_audit_flags_mode_coherence_gaps(tmp_path):
    _write_json(
        tmp_path / "rubrics/good_newton.json",
        {
            "rubric_mode": "newton",
            "dimensions": [{"name": "Generative Yield", "weight": 15}],
        },
    )
    _write_charter(tmp_path, "good_newton", "## Secondary observable\nx\n")
    _write_json(
        tmp_path / "rubrics/newton_secondary_gap.json",
        {
            "rubric_mode": "newton",
            "dimensions": [{"name": "Generative Yield", "weight": 15}],
        },
    )
    _write_charter(tmp_path, "newton_secondary_gap", "# Charter\n")
    _write_json(
        tmp_path / "rubrics/newton_charter_gap.json",
        {
            "rubric_mode": "newton",
            "dimensions": [{"name": "Generative Yield", "weight": 15}],
        },
    )
    (tmp_path / "projects" / "newton_charter_gap").mkdir(parents=True, exist_ok=True)
    _write_json(
        tmp_path / "rubrics/newton_project_gap.json",
        {
            "rubric_mode": "newton",
            "dimensions": [{"name": "Generative Yield", "weight": 15}],
        },
    )
    _write_json(
        tmp_path / "rubrics/dormant_newton.json",
        {
            "rubric_mode": "newton",
            "__do_not_run_live": True,
            "__do_not_run_live_reason": "archived experiment surface",
            "dimensions": [{"name": "Generative Yield", "weight": 15}],
        },
    )
    _write_json(
        tmp_path / "rubrics/kepler_confused.json",
        {
            "rubric_mode": "kepler",
            "dimensions": [{"name": "Generative Yield", "weight": 20}],
        },
    )
    _write_json(
        tmp_path / "rubrics/legacy.json",
        {"dimensions": [{"name": "Fit", "weight": 100}]},
    )
    _write_json(
        tmp_path / "rubrics/bad_mode.json",
        {"rubric_mode": "factory", "dimensions": [{"name": "Fit", "weight": 100}]},
    )
    _write_json(
        tmp_path / "rubrics/sealed.json",
        {
            "rubric_mode": "sealed_holdout",
            "__do_not_run_live": True,
            "dimensions": [{"name": "Fit", "weight": 100}],
        },
    )
    _write_json(
        tmp_path / "rubrics/__test_newton_gate.json",
        {
            "rubric_mode": "newton",
            "dimensions": [{"name": "Generative Yield", "weight": 20}],
        },
    )
    _write_charter(tmp_path, "__test_newton_gate", "# fixture\n")

    report = audit_rubric_mode_corpus(repo=tmp_path)

    assert report["summary"]["rubric_count"] == 10
    assert report["summary"]["attention_count"] == 5
    assert report["summary"]["legacy_unset"]["count"] == 1
    assert report["summary"]["legacy_unset"]["with_project_count"] == 0
    assert report["summary"]["legacy_unset"]["without_project_count"] == 1
    assert report["summary"]["legacy_unset"]["charter_status_counts"]["project_missing"] == 1
    assert _row(report, "rubrics/good_newton.json")["status"] == "ok"
    assert (
        _row(report, "rubrics/newton_secondary_gap.json")["status"]
        == "newton_secondary_observable_missing"
    )
    assert (
        "Secondary observable"
        in _row(report, "rubrics/newton_secondary_gap.json")["repair_hint"]
    )
    assert (
        _row(report, "rubrics/newton_charter_gap.json")["status"]
        == "newton_charter_missing"
    )
    assert "project_charter.md" in _row(
        report,
        "rubrics/newton_charter_gap.json",
    )["repair_hint"]
    assert (
        _row(report, "rubrics/newton_project_gap.json")["status"]
        == "newton_project_missing"
    )
    assert "retire or archive" in _row(report, "rubrics/newton_project_gap.json")["repair_hint"]
    assert _row(report, "rubrics/newton_secondary_gap.json")["validation_command"] == (
        "python scripts/public/validators/validate_rubric.py "
        "newton_secondary_gap --rubric rubrics/newton_secondary_gap.json --verbose"
    )
    assert _row(report, "rubrics/kepler_confused.json")["status"] == "kepler_with_generative_yield"
    assert _row(report, "rubrics/legacy.json")["status"] == "legacy_unset"
    assert _row(report, "rubrics/bad_mode.json")["status"] == "invalid_contract"
    assert _row(report, "rubrics/sealed.json")["status"] == "sealed_holdout"
    assert _row(report, "rubrics/dormant_newton.json")["status"] == "do_not_run_live"
    assert "archived experiment surface" in "; ".join(
        _row(report, "rubrics/dormant_newton.json")["notes"]
    )
    assert _row(report, "rubrics/__test_newton_gate.json")["status"] == "test_fixture"


def test_rubric_level_secondary_observable_contract_counts_as_present(tmp_path):
    _write_json(
        tmp_path / "rubrics/rubric_contract_newton.json",
        {
            "rubric_mode": "newton",
            "secondary_observable_contract": {
                "observable": "held-out sibling behavior",
                "measurement": "run the sibling scorer",
                "expected_range": "non-empty prediction with bounded error",
                "falsifier": "only restates the primary fit",
            },
            "dimensions": [{"name": "Generative Yield", "weight": 15}],
        },
    )

    report = audit_rubric_mode_corpus(repo=tmp_path)
    row = _row(report, "rubrics/rubric_contract_newton.json")

    assert row["status"] == "ok"
    assert row["charter_secondary_observable"] == "present"
    assert "secondary observable contract present in rubric" in row["notes"]


def test_malformed_secondary_observable_contract_is_invalid_contract(tmp_path):
    _write_json(
        tmp_path / "rubrics/bad_contract_newton.json",
        {
            "rubric_mode": "newton",
            "secondary_observable_contract": {
                "observable": "held-out sibling behavior",
                "measurement": "",
                "expected_range": "non-empty prediction with bounded error",
                "falsifier": "only restates the primary fit",
            },
            "dimensions": [{"name": "Generative Yield", "weight": 15}],
        },
    )
    _write_charter(tmp_path, "bad_contract_newton", "Secondary observable: y\n")

    report = audit_rubric_mode_corpus(repo=tmp_path)
    row = _row(report, "rubrics/bad_contract_newton.json")

    assert row["status"] == "invalid_contract"
    assert "secondary_observable_contract missing" in "; ".join(row["notes"])


def test_dynamic_rubric_maps_to_base_project(tmp_path):
    _write_json(
        tmp_path / "rubrics/dynamic_demo.json",
        {
            "rubric_mode": "newton",
            "dimensions": [{"name": "Generative Yield", "weight": 15}],
        },
    )
    _write_charter(tmp_path, "demo", "Secondary observable: y\n")

    report = audit_rubric_mode_corpus(repo=tmp_path)
    row = _row(report, "rubrics/dynamic_demo.json")

    assert row["project_slug"] == "demo"
    assert row["project_path"] == "projects/demo"
    assert row["status"] == "ok"


def test_dynamic_committee_panel_is_not_rubric_mode_attention(tmp_path):
    _write_json(
        tmp_path / "rubrics/dynamic_demo.json",
        {
            "committee": {
                "role": "Attacker",
                "persona": "Audit numerical and procedural fragility.",
                "focus_area": "Look for brittle assumptions.",
            }
        },
    )
    _write_eval_history(
        tmp_path,
        "demo",
        [{"timestamp": "2999-01-01T00:00:00Z", "score": 1}],
    )

    report = audit_rubric_mode_corpus(repo=tmp_path, freshness_days=30)
    row = _row(report, "rubrics/dynamic_demo.json")

    assert row["project_slug"] == "demo"
    assert row["status"] == "committee_panel"
    assert row["mode"] == "committee_panel"
    assert report["summary"]["attention_count"] == 0
    assert "committee_panel" in report["summary"]["status_counts"]


def test_single_rubric_scope_and_text_render(tmp_path):
    _write_json(
        tmp_path / "custom/rubric.json",
        {"rubric_mode": "kepler", "dimensions": [{"name": "Fit", "weight": 100}]},
    )

    report = audit_rubric_mode_corpus(repo=tmp_path, rubric="custom/rubric.json")
    rendered = render_text(report)

    assert report["summary"]["rubric_count"] == 1
    assert "Rubric-mode corpus audit" in rendered
    assert "attention: none" in rendered
    assert "legacy_unset=" in rendered


def test_single_rubric_scope_accepts_bare_slug(tmp_path):
    _write_json(
        tmp_path / "rubrics/demo.json",
        {"rubric_mode": "calibration", "dimensions": [{"name": "Fit", "weight": 100}]},
    )
    (tmp_path / "projects" / "demo").mkdir(parents=True)

    report = audit_rubric_mode_corpus(repo=tmp_path, rubric="demo")

    assert report["summary"]["rubric_count"] == 1
    assert report["rows"][0]["rubric_path"] == "rubrics/demo.json"
    assert report["rows"][0]["status"] == "ok"


def test_single_legacy_rubric_scope_requires_mode_decision(tmp_path):
    _write_json(
        tmp_path / "custom/legacy.json",
        {"dimensions": [{"name": "Fit", "weight": 100}]},
    )

    report = audit_rubric_mode_corpus(repo=tmp_path, rubric="custom/legacy.json")
    rendered = render_text(report)

    assert report["summary"]["rubric_count"] == 1
    assert report["summary"]["attention_count"] == 1
    assert report["summary"]["legacy_unset"]["count"] == 1
    assert report["attention"][0]["status"] == "legacy_unset"
    assert "decide whether the rubric is kepler, newton, or calibration" in rendered


def test_recent_legacy_project_run_is_attention(tmp_path):
    _write_json(
        tmp_path / "rubrics/recent_legacy.json",
        {"dimensions": [{"name": "Fit", "weight": 100}]},
    )
    _write_json(
        tmp_path / "rubrics/stale_legacy.json",
        {"dimensions": [{"name": "Fit", "weight": 100}]},
    )
    _write_eval_history(
        tmp_path,
        "recent_legacy",
        [{"timestamp": "2999-01-01T00:00:00Z", "score": 1}],
    )
    _write_eval_history(
        tmp_path,
        "stale_legacy",
        [{"timestamp": "2000-01-01T00:00:00Z", "score": 1}],
    )

    report = audit_rubric_mode_corpus(repo=tmp_path, freshness_days=30)

    recent = _row(report, "rubrics/recent_legacy.json")
    stale = _row(report, "rubrics/stale_legacy.json")
    assert recent["status"] == "legacy_unset"
    assert recent["latest_run_timestamp"] == "2999-01-01T00:00:00Z"
    assert recent["recent_run"] is True
    assert stale["status"] == "legacy_unset"
    assert stale["recent_run"] is False
    assert report["summary"]["attention_count"] == 1
    assert report["attention"][0]["rubric_path"] == "rubrics/recent_legacy.json"
    assert report["summary"]["legacy_unset"]["recent_with_project_count"] == 1
    assert report["summary"]["legacy_unset"]["recent_examples"][0]["rubric_path"] == (
        "rubrics/recent_legacy.json"
    )


def test_text_render_includes_repair_hint_and_check_command(tmp_path):
    _write_json(
        tmp_path / "rubrics/newton_secondary_gap.json",
        {
            "rubric_mode": "newton",
            "dimensions": [{"name": "Generative Yield", "weight": 15}],
        },
    )
    _write_charter(tmp_path, "newton_secondary_gap", "# Charter\n")

    report = audit_rubric_mode_corpus(repo=tmp_path)
    rendered = render_text(report)

    assert "repair=add a charter section named 'Secondary observable'" in rendered
    assert (
        "check=python scripts/public/validators/validate_rubric.py newton_secondary_gap"
        in rendered
    )


def test_main_fail_on_attention_returns_one(tmp_path, monkeypatch):
    _write_json(
        tmp_path / "rubrics/newton_secondary_gap.json",
        {
            "rubric_mode": "newton",
            "dimensions": [{"name": "Generative Yield", "weight": 15}],
        },
    )
    _write_charter(tmp_path, "newton_secondary_gap", "# Charter\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("src.ztare.reports.rubric_mode_corpus_audit.REPO", tmp_path)

    assert main(["--freshness-days", "14", "--fail-on-attention"]) == 1
