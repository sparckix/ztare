"""Tests for the R1 module-level I_model lint (mutation_suite_guard).

Pin down the gp159-class regression: R1 lint must reject module-level
I_model(...) calls AT MODULE SCOPE but ALLOW them inside
`if __name__ == "__main__":` blocks (which the apparatus does not run
at import) per Contract C hint guidance.
"""

from __future__ import annotations

import pytest

from src.ztare.fit.mutation_suite_guard import _ast_check_no_module_level_i_model_call


class TestR1ModuleLevelLint:
    def test_clean_module_level_no_violation(self):
        code = (
            "MODEL_PARAMS = {}\n"
            "def I_model(d, params=None):\n"
            "    return 2 * d\n"
        )
        assert _ast_check_no_module_level_i_model_call(code) is None

    def test_module_level_call_caught(self):
        code = (
            "def I_model(d):\n"
            "    return d\n"
            "I_model(5.0)\n"
        )
        msg = _ast_check_no_module_level_i_model_call(code)
        assert msg is not None
        assert "Module-level I_model" in msg

    def test_module_level_call_in_assert_caught(self):
        code = (
            "def I_model(d):\n"
            "    return d\n"
            "assert I_model(5.0) > 0, 'must be positive'\n"
        )
        msg = _ast_check_no_module_level_i_model_call(code)
        assert msg is not None

    def test_call_inside_main_guard_allowed(self):
        # Contract C hint tells the mutator to put debug calls in
        # `if __name__ == "__main__":`. The apparatus does NOT run that
        # block at import. The lint must NOT flag these as module-level.
        code = (
            "def I_model(d, params=None):\n"
            "    return 2 * d\n"
            "\n"
            'if __name__ == "__main__":\n'
            "    print(I_model(5.0))\n"
            "    assert I_model(10.0) > 0\n"
        )
        assert _ast_check_no_module_level_i_model_call(code) is None

    def test_call_inside_main_guard_inverted_form(self):
        # Some mutators write `if "__main__" == __name__:` — should also
        # be recognized as a main guard.
        code = (
            "def I_model(d):\n"
            "    return d\n"
            "\n"
            'if "__main__" == __name__:\n'
            "    print(I_model(1.0))\n"
        )
        assert _ast_check_no_module_level_i_model_call(code) is None

    def test_call_inside_function_body_allowed(self):
        # I_model called inside another function's body is fine — it
        # only fires when the function is invoked, not at import.
        code = (
            "def I_model(d):\n"
            "    return d\n"
            "def helper():\n"
            "    return I_model(5.0)\n"
        )
        assert _ast_check_no_module_level_i_model_call(code) is None

    def test_message_does_not_recommend_post_fit_sanity(self):
        # The error message previously suggested `_post_fit_sanity` as a fix —
        # that's the gp159 anti-pattern. Verify the message no longer does.
        code = (
            "def I_model(d):\n"
            "    return d\n"
            "I_model(1.0)\n"
        )
        msg = _ast_check_no_module_level_i_model_call(code)
        assert msg is not None
        assert "_post_fit_sanity" in msg, "msg should still NAME the anti-pattern to forbid it"
        # but explicitly forbids hiding in helper
        assert "Do NOT hide" in msg or "do not hide" in msg.lower()
        # And recommends the if __name__ block as the legitimate alternative
        assert "__main__" in msg
