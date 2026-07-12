from __future__ import annotations

from ztare.validator.model_aliases import ensure_canonical_model_aliases


def test_predictor_step_gets_legacy_aliases() -> None:
    code = "def step(state, action, t):\n    return state\n"

    aliased = ensure_canonical_model_aliases(code)

    assert "f = step" in aliased
    assert "model = step" in aliased
    assert "I_model = step" in aliased


def test_patch_delta_is_not_exported_as_predictor() -> None:
    code = (
        'PATCH_BASE = {"source_ref":"workspace/submissions/base.py","sha256":"abc"}\n'
        "def PATCH_DELTA(base_next, state, action, t):\n"
        "    return base_next\n"
    )

    aliased = ensure_canonical_model_aliases(code)

    assert aliased == code
    assert "f = PATCH_DELTA" not in aliased
    assert "model = PATCH_DELTA" not in aliased
    assert "I_model = PATCH_DELTA" not in aliased


def test_existing_patch_delta_alias_is_not_considered_valid_predictor_source() -> None:
    code = (
        "def PATCH_DELTA(base_next, state, action, t):\n"
        "    return base_next\n"
        "model = PATCH_DELTA\n"
    )

    aliased = ensure_canonical_model_aliases(code)

    assert "I_model = model" not in aliased
    assert "f = model" not in aliased
