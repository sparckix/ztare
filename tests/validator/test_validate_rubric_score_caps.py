from __future__ import annotations

import importlib.util
import json
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


def _write_project_surface(repo: Path, project_slug: str) -> Path:
    project = repo / "projects" / project_slug
    project.mkdir(parents=True)
    (project / "project_charter.md").write_text("# Charter\n", encoding="utf-8")
    (project / "evidence.txt").write_text("evidence\n", encoding="utf-8")
    (project / "thesis.md").write_text("thesis\n", encoding="utf-8")
    (project / "raw").mkdir()
    return project


def _write_rubric(repo: Path, project_slug: str, rubric: dict) -> Path:
    path = repo / "rubrics" / f"{project_slug}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rubric, sort_keys=True) + "\n", encoding="utf-8")
    return path


def test_validate_project_reports_qualitative_assertion_contract(tmp_path: Path) -> None:
    module = _load_validate_rubric_module()
    _write_project_surface(tmp_path, "qualitative_demo")
    rubric = {
        **BASE_RUBRIC,
        "rubric_mode": "calibration",
        "falsification_mode": "bounded_discriminator",
        "enable_fit_primitive": False,
        "enable_fit_primitive_features": False,
        "holdout_hard_gate": False,
        "holdout_budget": 0,
    }
    rubric_path = _write_rubric(tmp_path, "qualitative_demo", rubric)

    result = module.validate_rubric_project(
        "qualitative_demo",
        rubric=rubric_path,
        repo=tmp_path,
    )

    assert result["ok"] is True
    assert result["launch_contract"]["submission_contract_kind"] == "assertion_suite"
    assert result["launch_contract"]["expected_submission_surface"] == (
        "plain Python assertion suite"
    )
    assert result["launch_contract"]["requires_i_model"] is False
    assert result["launch_contract"]["registered_substrate_abi"] is None


def test_validate_project_reports_numeric_model_contract(tmp_path: Path) -> None:
    module = _load_validate_rubric_module()
    _write_project_surface(tmp_path, "numeric_demo")
    rubric = {
        "persona": "Numeric model judge.",
        "rubric_mode": "kepler",
        "falsification_mode": "numerical_proof",
        "fit_score_mode": "continuous_l2",
        "cage_meta": {"class": "nd_features"},
        "dimensions": [
            {"name": "Fit", "weight": 100, "description": "fit quality"}
        ],
        "criteria": {"Fit": "fit quality"},
    }
    rubric_path = _write_rubric(tmp_path, "numeric_demo", rubric)

    result = module.validate_rubric_project(
        "numeric_demo",
        rubric=rubric_path,
        repo=tmp_path,
    )

    assert result["ok"] is True
    contract = result["launch_contract"]
    assert contract["submission_contract_kind"] == "numeric_model"
    assert contract["expected_submission_surface"] == "numeric I_model submission"
    assert contract["requires_i_model"] is True
    assert contract["registered_substrate_abi"] == "feature_dict"
    assert contract["numeric_cross_class_diagnostic_eligible"] is True


def test_validate_project_reports_theorem_packet_contract(tmp_path: Path) -> None:
    module = _load_validate_rubric_module()
    project = _write_project_surface(tmp_path, "theorem_demo")
    (project / "evidence.txt").write_text(
        "The packet exposes def proof_progress_review().\n",
        encoding="utf-8",
    )
    (project / "test_model.py").write_text(
        "def proof_progress_review():\n    return {'ok': True}\n",
        encoding="utf-8",
    )
    rubric = {
        **BASE_RUBRIC,
        "rubric_mode": "calibration",
        "falsification_mode": "bounded_discriminator",
        "enable_fit_primitive": False,
        "enable_fit_primitive_features": False,
        "holdout_hard_gate": False,
        "holdout_budget": 0,
        "require_i_model_in_submission": False,
        "cage_meta": {"class": "proof_target"},
        "theorem_packet_contract": {
            "required_top_level_functions": ["proof_progress_review"]
        },
    }
    rubric_path = _write_rubric(tmp_path, "theorem_demo", rubric)

    result = module.validate_rubric_project(
        "theorem_demo",
        rubric=rubric_path,
        repo=tmp_path,
    )

    assert result["ok"] is True
    contract = result["launch_contract"]
    assert contract["submission_contract_kind"] == "theorem_packet"
    assert contract["expected_submission_surface"] == (
        "theorem-packet top-level functions"
    )
    assert contract["requires_i_model"] is False
    assert contract["registered_substrate_abi"] == "lean_proof"
    assert contract["theorem_required_functions"] == ["proof_progress_review"]
