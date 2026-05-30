import importlib.util
from pathlib import Path


def _load_pretick_runner():
    path = Path(__file__).resolve().parents[1] / "scripts/public/control/pretick_runner.py"
    spec = importlib.util.spec_from_file_location("pretick_runner_under_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_receipt_schema_residual_does_not_default_to_hard_math():
    runner = _load_pretick_runner()

    pc, guard = runner._repair_shallow_menu_choice(
        goal=(
            "portable receipt schema residual: determine whether downstream "
            "action comes from GP-216, GP-219 receipt fields, or nearest confuser"
        ),
        pc="hard_mathematical_residual",
        menu_scores={"hard_mathematical_residual": 2, "apparatus_self_audit": 0},
    )

    assert pc == "apparatus_self_audit"
    assert guard["repaired"] is True
    assert guard["receipt_meta_surface"] is True
    assert guard["hard_math_qualified"] is False


def test_hard_math_qualified_residual_stays_hard_math():
    runner = _load_pretick_runner()

    pc, guard = runner._repair_shallow_menu_choice(
        goal="hard mathematical residual for a Lean PDE theorem estimate",
        pc="hard_mathematical_residual",
        menu_scores={"hard_mathematical_residual": 4},
    )

    assert pc == "hard_mathematical_residual"
    assert guard["repaired"] is False
    assert guard["hard_math_qualified"] is True


def test_recurrence_memory_risk_requires_memory_pairing_signal():
    runner = _load_pretick_runner()

    assert runner._has_recurrence_memory_risk(
        "avoid rediscovery of a killed vector using project memory"
    ) is True
    assert runner._has_recurrence_memory_risk(
        "fresh source acquisition with a new packet"
    ) is False
