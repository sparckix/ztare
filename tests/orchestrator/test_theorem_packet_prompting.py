import json
from pathlib import Path

from src.ztare.orchestrator.briefing_providers.contract_rules import ContractRulesProvider
from src.ztare.orchestrator.mutator_briefing import BriefingContext
from src.ztare.orchestrator.submission_path_helpers import format_r1_retry_skeleton


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


def test_theorem_packet_retry_preserves_packet_api_not_scalar_paths():
    prompt = format_r1_retry_skeleton(
        "Python suite executed but does not define `I_model`.",
        "def vector_ledger_terms():\n    return {}",
        rubric_data=_rubric(),
    )

    assert "theorem-packet" in prompt
    assert "def vector_ledger_terms()" in prompt
    assert "def trackb_convexity_theorem()" in prompt
    assert "Do not switch to the generic Path A/Path B scaffold" in prompt
    assert "PATH A — PARAMETRIC_FORM" not in prompt
    assert "PATH B — LAGRANGIAN" not in prompt


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


def test_trackb_rubric_disables_scalar_imodel_requirement():
    rubric = json.loads(Path("rubrics/ns_proofsearch_leray_convexity_trackb.json").read_text())

    assert rubric["require_i_model_in_submission"] is False
    assert rubric["theorem_packet_contract"]["required_top_level_functions"]
