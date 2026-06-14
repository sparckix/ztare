from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_validate_rubric_module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "validate_rubric.py"
    spec = importlib.util.spec_from_file_location("_validate_rubric_for_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BASE_RUBRIC = {
    "persona": "Adversarial qualitative proof judge. Demand exact objects. Penalize overclaim.",
    "rubric_mode": "kepler",
    "fit_score_mode": "none",
    "disable_evidence_fit_gate": True,
    "disable_evidence_fit_gate_reason": "qualitative substrate",
    "disable_uniqueness_gap_gate": True,
    "disable_uniqueness_gap_gate_reason": "qualitative substrate",
    "farther_tail_region": None,
    "dimensions": [
        {"name": "Generative Yield", "weight": 100, "description": "yield"}
    ],
    "criteria": {"Generative_Yield": "yield"},
}


def test_validate_rubric_accepts_well_formed_evidence_gap_caps(tmp_path: Path) -> None:
    module = _load_validate_rubric_module()
    rubric = {
        **BASE_RUBRIC,
        "evidence_gap_score_caps": [
            {
                "cap": 89,
                "severity_any": ["blocking", "degrading"],
                "text_contains_any": ["missing proof object"],
                "reason": "Proof-band score requires the missing object.",
            }
        ],
    }

    messages = module._check_rubric(rubric, tmp_path / "rubric.json", "demo")

    assert not [msg for msg in messages if msg.startswith("  ❌")]


def test_validate_rubric_rejects_unselective_evidence_gap_caps(tmp_path: Path) -> None:
    module = _load_validate_rubric_module()
    rubric = {
        **BASE_RUBRIC,
        "evidence_gap_score_caps": [
            {
                "cap": 89,
                "reason": "No selector would make this cap uninterpretable.",
            }
        ],
    }

    messages = module._check_rubric(rubric, tmp_path / "rubric.json", "demo")

    assert any("has no selector" in msg for msg in messages)


def test_validate_rubric_accepts_calibration_mode(tmp_path: Path) -> None:
    module = _load_validate_rubric_module()
    rubric = {
        **BASE_RUBRIC,
        "rubric_mode": "calibration",
        "dimensions": [
            {"name": "Instrument Fit", "weight": 100, "description": "calibration"}
        ],
        "criteria": {"Instrument_Fit": "calibration"},
    }

    messages = module._check_rubric(rubric, tmp_path / "rubric.json", "demo")

    assert not [msg for msg in messages if msg.startswith("  ❌")]
    assert any("Calibration-mode rubric" in msg for msg in messages)


def test_validate_rubric_rejects_unknown_mode_via_shared_contract(tmp_path: Path) -> None:
    module = _load_validate_rubric_module()
    rubric = {
        **BASE_RUBRIC,
        "rubric_mode": "factory",
    }

    messages = module._check_rubric(rubric, tmp_path / "rubric.json", "demo")

    assert any("not a recognized value" in msg for msg in messages)


def test_validate_rubric_rejects_malformed_secondary_observable_contract(tmp_path: Path) -> None:
    module = _load_validate_rubric_module()
    rubric = {
        **BASE_RUBRIC,
        "rubric_mode": "newton",
        "secondary_observable_contract": {
            "observable": "stress response",
            "measurement": "",
            "expected_range": "positive lift",
            "falsifier": "no lift",
        },
    }

    messages = module._check_rubric(rubric, tmp_path / "rubric.json", "demo")

    assert any("secondary_observable_contract missing" in msg for msg in messages)


def test_validate_project_accepts_newton_rubric_contract_without_charter_heading(tmp_path: Path) -> None:
    module = _load_validate_rubric_module()
    project = tmp_path / "projects" / "demo"
    project.mkdir(parents=True)
    (project / "project_charter.md").write_text("# Charter\nNo heading here.\n", encoding="utf-8")
    (project / "evidence.txt").write_text("evidence\n", encoding="utf-8")
    (project / "thesis.md").write_text("thesis\n", encoding="utf-8")
    (project / "raw").mkdir()
    rubric = {
        **BASE_RUBRIC,
        "rubric_mode": "newton",
        "secondary_observable_contract": {
            "observable": "stress response",
            "measurement": "held-out perturbation score",
            "expected_range": "positive lift",
            "falsifier": "no lift",
        },
    }

    messages = module._check_project(project, rubric, "newton")

    assert not [msg for msg in messages if "Secondary observable" in msg and msg.startswith("  ❌")]
    assert any("secondary_observable_contract" in msg for msg in messages)
