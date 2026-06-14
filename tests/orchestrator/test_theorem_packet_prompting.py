import json
from pathlib import Path

from src.ztare.orchestrator.briefing_providers.contract_rules import ContractRulesProvider
from src.ztare.orchestrator.mutator_briefing import BriefingContext
from src.ztare.orchestrator.submission_path_helpers import (
    detect_submission_contract,
    format_r1_retry_skeleton,
    requires_i_model_submission,
    submission_contract_kind,
)


def _rubric() -> dict:
    return {
        "fit_score_mode": "none",
        "require_i_model_in_submission": False,
        "theorem_packet_contract": {
            "required_top_level_functions": [
                "vector_ledger_terms",
                "trackb_convexity_theorem",
            ]
        },
    }


def _qualitative_rubric() -> dict:
    return {
        "rubric_mode": "calibration",
        "falsification_mode": "bounded_discriminator",
        "enable_fit_primitive": False,
        "enable_fit_primitive_features": False,
        "fit_score_mode": "none",
        "holdout_hard_gate": False,
        "holdout_budget": 0,
        "disable_evidence_fit_gate": True,
        "disable_uniqueness_gap_gate": True,
    }


def test_theorem_packet_retry_preserves_packet_api_not_scalar_paths():
    prompt = format_r1_retry_skeleton(
        "Python suite executed but does not define `I_model`.",
        "def vector_ledger_terms():\n    return {}",
        rubric_data=_rubric(),
    )

    assert "theorem-packet" in prompt
    assert "def vector_ledger_terms()" in prompt
    assert "def trackb_convexity_theorem()" in prompt
    assert "Do not switch to the generic numeric-declaration template" in prompt
    assert "PARAMETRIC MODEL DECLARATION" not in prompt
    assert "VARIATIONAL/LAGRANGIAN DECLARATION" not in prompt


def test_qualitative_retry_uses_assertion_suite_not_scalar_paths():
    prompt = format_r1_retry_skeleton(
        "Missing required Python falsification suite block.",
        "## Thesis\nA bounded mechanism claim.",
        rubric_data=_qualitative_rubric(),
    )

    assert "assertion suite" in prompt
    assert "PARAMETRIC MODEL DECLARATION" not in prompt
    assert "VARIATIONAL/LAGRANGIAN DECLARATION" not in prompt
    assert "def test_mechanism_is_bounded()" in prompt
    assert "no I_model" in prompt


def test_qualitative_contract_inferred_without_explicit_imodel_flag():
    rubric = _qualitative_rubric()

    assert requires_i_model_submission(rubric) is False
    assert submission_contract_kind(rubric) == "assertion_suite"


def test_numeric_retry_uses_scientific_contract_names_not_path_labels():
    prompt = format_r1_retry_skeleton(
        "PARAMETRIC_FORM AST/whitelist pre-flight FAILED",
        "```python\nPARAMETER_NAMES = ['a']\ndef I_model(features, params=None): return 0.0\n```",
        rubric_data={"require_i_model_in_submission": True},
    )

    assert "PARAMETRIC MODEL DECLARATION" in prompt
    assert "VARIATIONAL/LAGRANGIAN DECLARATION" in prompt
    assert ("PATH " + "A") not in prompt
    assert ("PATH " + "B") not in prompt


def test_retry_prompt_carries_same_iteration_strike_history():
    prompt = format_r1_retry_skeleton(
        "PARAMETRIC_FORM calls helper function",
        "```python\nPARAMETRIC_FORM = '_helper(features)'\n```",
        rubric_data={"require_i_model_in_submission": True},
        retry_error_history=[
            "PARAMETER_NAMES placed inside __main__",
            "PARAMETRIC_FORM calls helper function",
        ],
    )

    assert "Same-iteration R1 strike history" in prompt
    assert "PARAMETER_NAMES placed inside __main__" in prompt
    assert "PARAMETRIC_FORM calls helper function" in prompt
    assert "without reintroducing" in prompt


def test_retry_history_is_available_for_qualitative_contracts():
    prompt = format_r1_retry_skeleton(
        "module-level execution detected",
        "```python\nprint('debug')\n```",
        rubric_data=_qualitative_rubric(),
        retry_error_history=[
            "imported project feature table",
            "module-level execution detected",
        ],
    )

    assert "Same-iteration R1 strike history" in prompt
    assert "imported project feature table" in prompt
    assert "module-level execution detected" in prompt


def test_retry_history_is_available_for_theorem_packet_contracts():
    prompt = format_r1_retry_skeleton(
        "missing top-level theorem function",
        "```python\ndef vector_ledger_terms(): return {}\n```",
        rubric_data=_rubric(),
        retry_error_history=[
            "non-stdlib import at module scope",
            "missing top-level theorem function",
        ],
    )

    assert "Same-iteration R1 strike history" in prompt
    assert "non-stdlib import at module scope" in prompt
    assert "missing top-level theorem function" in prompt
    assert "Do not switch to the generic numeric-declaration template" in prompt


def test_submission_contract_detection_uses_named_contract_ids():
    assert detect_submission_contract("PARAMETER_NAMES=[]\nPARAMETRIC_FORM='x'")["contract"] == "parametric_model"
    assert detect_submission_contract("PARAMETER_NAMES=[]\nLAGRANGIAN='q**2'\nPREDICTION='q'")["contract"] == "variational_lagrangian"
    assert detect_submission_contract("MODEL_PARAMS={'a': 1.0}")["contract"] == "fixed_parameter_model"


def test_theorem_packet_contract_rules_do_not_emit_scalar_fit_grammar(tmp_path: Path):
    ctx = BriefingContext(
        project_dir=tmp_path,
        iter_index=1,
        rubric=_rubric(),
    )

    fragment = ContractRulesProvider().fragment(ctx)

    assert "theorem-packet substrate" in fragment
    assert "def vector_ledger_terms()" in fragment
    assert "I_model: optional compatibility scaffold only" in fragment
    assert "PARAMETRIC_FORM grammar" not in fragment


def test_contract_rules_do_not_default_unspecified_rubric_to_newton(tmp_path: Path):
    rubric = {"require_i_model_in_submission": True}
    iter1 = ContractRulesProvider().fragment(
        BriefingContext(project_dir=tmp_path, iter_index=1, rubric=rubric)
    )
    recap = ContractRulesProvider().fragment(
        BriefingContext(project_dir=tmp_path, iter_index=2, rubric=rubric)
    )

    assert "Mode: newton" not in iter1
    assert "secondary observable + falsifying observation required" not in iter1
    assert "Mode: legacy_unspecified" in recap
    assert "secondary observable + falsifying observation required" not in recap


def test_contract_rules_infer_qualitative_assertion_contract(tmp_path: Path):
    rubric = _qualitative_rubric()
    iter1 = ContractRulesProvider().fragment(
        BriefingContext(project_dir=tmp_path, iter_index=1, rubric=rubric)
    )
    recap = ContractRulesProvider().fragment(
        BriefingContext(project_dir=tmp_path, iter_index=2, rubric=rubric)
    )

    assert "REQUIRED:    none (qualitative substrate)" in iter1
    assert "BANNED:      DO NOT define or call I_model()" in iter1
    assert "PARAMETRIC_FORM grammar" not in iter1
    assert "suite_shape" in recap
    assert "PARAMETRIC_FORM grammar" not in recap


def test_contract_rules_surface_newton_obligations_only_when_declared(tmp_path: Path):
    rubric = {
        "rubric_mode": "newton",
        "require_i_model_in_submission": True,
    }

    iter1 = ContractRulesProvider().fragment(
        BriefingContext(project_dir=tmp_path, iter_index=1, rubric=rubric)
    )
    recap = ContractRulesProvider().fragment(
        BriefingContext(project_dir=tmp_path, iter_index=2, rubric=rubric)
    )

    assert "### Mode: newton" in iter1
    assert "secondary observable" in iter1
    assert "Mode: newton" in recap
    assert "secondary observable + falsifying observation required" in recap


def test_trackb_rubric_disables_scalar_imodel_requirement():
    rubric = json.loads(Path("rubrics/ns_proofsearch_leray_convexity_trackb.json").read_text())

    assert rubric["require_i_model_in_submission"] is False
    assert rubric["theorem_packet_contract"]["required_top_level_functions"]
