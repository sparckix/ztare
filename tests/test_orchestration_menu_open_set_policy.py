import importlib.util
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
PRETICK = REPO / "scripts/public/control/pretick_runner.py"


def load_pretick_runner():
    spec = importlib.util.spec_from_file_location("pretick_runner_under_test", PRETICK)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_menu_shallow_guard_routes_unmatched_surface_to_outside_menu():
    mod = load_pretick_runner()

    selected, guard = mod._repair_shallow_menu_choice(
        goal="consent authorization blocker with adequate evidence",
        pc=None,
        menu_scores={},
    )

    assert selected == "outside_menu"
    assert guard["open_set_refusal"] is True
    assert guard["new_residual_class_candidate"] == "unmapped_by_orchestration_menu"
    assert "defer" in guard["repair_reason"]


def test_menu_shallow_guard_keeps_receipt_meta_out_of_hard_math():
    mod = load_pretick_runner()
    scores = {"hard_mathematical_residual": 3}

    selected, guard = mod._repair_shallow_menu_choice(
        goal="portable receipt schema residual with typed fields and nearest confuser",
        pc="hard_mathematical_residual",
        menu_scores=scores,
    )

    assert selected == "apparatus_self_audit"
    assert guard["open_set_refusal"] is False
    assert guard["repaired"] is True
    assert scores["apparatus_self_audit"] == 1


def test_orchestration_menu_declares_compiler_and_open_set_policy():
    menu = (REPO / "org/menu/orchestration_menu.yaml").read_text(encoding="utf-8")

    assert "version: 0.2.4" in menu
    assert "open_set_policy:" in menu
    assert "outside_menu" in menu
    assert "defer_to_new_residual_class" in menu
    assert "compiler_contract_policy:" in menu
    assert "orchestration_contract_gate.py" in menu
    assert "active_controller_surface:" in menu
    assert "specific_outside_residual_class" in menu
    assert "known_class_first_check" in menu
    assert "program_order_check" in menu
    assert "stop_condition_check" in menu
    assert "source_contract_alignment_check" in menu
    assert "deterministic_lowering_result" in menu
    assert "unchecked_wrong_contract_execution" in menu
    assert "closed_menu_forcing" in menu


def test_pretick_surfaces_orchestration_contract_gate():
    source = PRETICK.read_text(encoding="utf-8")

    assert "orchestration_contract_gate" in source
    assert "src/ztare/research_director/orchestration_contract_gate.py" in source
    assert "python -m src.ztare.research_director.orchestration_contract_gate" in source
    assert "H31-H47" in source
