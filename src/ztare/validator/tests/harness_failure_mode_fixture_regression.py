"""Fixture regression for the harness-failure classifier.

The classifier exists to separate an AssertionError (substantive
falsification) from any other Python exception (broken harness).
Phase 1 of GP-023 collapsed the two into a single ``fail`` bucket,
which let the Judge rationalize an IndexError into a score-95
event. These tests lock the vocabulary and the terminal-exception
semantics in place.
"""

from __future__ import annotations

import sys

from ztare.validator.utilities.harness_failure_mode import (
    FAIL_ASSERT,
    FAIL_OTHER,
    FAIL_RUNTIME,
    classify_harness_failure,
    harness_defect_banner,
)


def test_assertion_error_classified_as_fail_assert() -> None:
    stderr = (
        "Traceback (most recent call last):\n"
        '  File "test_model.py", line 42, in <module>\n'
        "    assert x == 1\n"
        "AssertionError"
    )
    status, name = classify_harness_failure(stderr)
    assert status == FAIL_ASSERT
    assert name == "AssertionError"


def test_assertion_error_with_message_classified_as_fail_assert() -> None:
    stderr = (
        "Traceback (most recent call last):\n"
        "  ...\n"
        "AssertionError: Peak location differs by > 15%"
    )
    status, name = classify_harness_failure(stderr)
    assert status == FAIL_ASSERT
    assert name == "AssertionError"


def test_index_error_classified_as_fail_runtime() -> None:
    stderr = (
        "Traceback (most recent call last):\n"
        '  File "test_model.py", line 10, in parse_evidence\n'
        "    return rows[0][1]\n"
        "IndexError: list index out of range"
    )
    status, name = classify_harness_failure(stderr)
    assert status == FAIL_RUNTIME
    assert name == "IndexError"


def test_syntax_error_classified_as_fail_runtime() -> None:
    stderr = (
        '  File "test_model.py", line 5\n'
        "    def foo(:\n"
        "           ^\n"
        "SyntaxError: invalid syntax"
    )
    status, name = classify_harness_failure(stderr)
    assert status == FAIL_RUNTIME
    assert name == "SyntaxError"


def test_terminal_exception_wins_over_chained() -> None:
    # Chained exception: raising IndexError during handling of another
    # exception. The terminal exception is the one Python prints last.
    stderr = (
        "Traceback (most recent call last):\n"
        "  ...\n"
        "KeyError: 'phi'\n"
        "\nDuring handling of the above exception, another exception occurred:\n\n"
        "Traceback (most recent call last):\n"
        "  ...\n"
        "IndexError: out of range"
    )
    status, name = classify_harness_failure(stderr)
    assert status == FAIL_RUNTIME
    assert name == "IndexError"


def test_assertion_then_harness_error_picks_terminal() -> None:
    # Hypothetical: a test helper raises AssertionError, then cleanup
    # code raises an IndexError. The IndexError is terminal; we
    # classify as harness defect. This is more conservative than
    # calling it a substantive failure — justified, because the
    # harness is no longer trustworthy.
    stderr = (
        "AssertionError: Peak mismatch\n"
        "During cleanup, another exception occurred:\n"
        "IndexError: list index out of range"
    )
    status, name = classify_harness_failure(stderr)
    assert status == FAIL_RUNTIME
    assert name == "IndexError"


def test_empty_stderr_classified_as_fail_other() -> None:
    status, name = classify_harness_failure("")
    assert status == FAIL_OTHER
    assert name == ""


def test_stderr_with_no_exception_name_classified_as_fail_other() -> None:
    status, name = classify_harness_failure("Segmentation fault (core dumped)")
    assert status == FAIL_OTHER
    assert name == ""


def test_defect_banner_contains_anti_rationalization_directive() -> None:
    banner = harness_defect_banner("IndexError")
    assert "HARNESS DEFECT" in banner
    assert "NOT a falsification" in banner.lower() or "NOT A FALSIFICATION" in banner
    assert "MUST NOT rationalize" in banner
    assert "IndexError" in banner


def test_defect_banner_without_exception_name() -> None:
    banner = harness_defect_banner("")
    assert "HARNESS DEFECT" in banner
    assert "MUST NOT rationalize" in banner


_TESTS = (
    test_assertion_error_classified_as_fail_assert,
    test_assertion_error_with_message_classified_as_fail_assert,
    test_index_error_classified_as_fail_runtime,
    test_syntax_error_classified_as_fail_runtime,
    test_terminal_exception_wins_over_chained,
    test_assertion_then_harness_error_picks_terminal,
    test_empty_stderr_classified_as_fail_other,
    test_stderr_with_no_exception_name_classified_as_fail_other,
    test_defect_banner_contains_anti_rationalization_directive,
    test_defect_banner_without_exception_name,
)


def main() -> int:
    failed = 0
    for test in _TESTS:
        try:
            test()
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {test.__name__}: {exc}")
        except Exception as exc:  # pragma: no cover
            failed += 1
            print(f"ERROR {test.__name__}: {type(exc).__name__}: {exc}")
        else:
            print(f"PASS {test.__name__}")
    print(f"\n{len(_TESTS) - failed}/{len(_TESTS)} passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
