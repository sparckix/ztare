"""Classify a ``python test_model.py`` subprocess failure.

Motivation (GP-023 Phase 1 post-mortem): the Phase 1 sandbox ran
with a harness that raised ``IndexError`` while parsing
``evidence.txt``. The subprocess wrapper in ``test_thesis.py``
reported ``test_suite_status="fail"`` for both (a) an ``AssertionError``
that actually falsified the thesis and (b) a ``Traceback ...
IndexError: list index out of range`` that represented a broken
harness. The Judge read stderr as plain text and rationalized the
second case as "tooling noise, not a falsification," producing the
score-95 event that GP-030 was written to prevent.

This module gives the critique text a structured label so the Judge
can't collapse the two cases together. The label also feeds the
deterministic-gate hard-fail reason text when
``finalize_deterministic_score`` runs, so an operator reading the
score contract can tell at a glance whether a "fail" was substantive
falsification or a harness defect.

Vocabulary:

- ``fail_assert`` — subprocess exited non-zero, stderr contains
  ``AssertionError``. This is a substantive falsification.
- ``fail_runtime`` — subprocess exited non-zero, stderr contains any
  *other* Python exception (IndexError, KeyError, NameError,
  ImportError, SyntaxError, TypeError, ZeroDivisionError, ...).
  The harness is broken; the thesis has not been tested. Judge MUST
  NOT rationalize this as survivorship.
- ``fail_other`` — subprocess exited non-zero with stderr that does
  not match either bucket (rare; e.g. truncated output, non-Python
  tooling error). Treated as a harness defect, not a falsification.
"""

from __future__ import annotations

import re


FAIL_ASSERT = "fail_assert"
FAIL_RUNTIME = "fail_runtime"
FAIL_OTHER = "fail_other"

# Any stdlib exception name except AssertionError. Not exhaustive —
# we match by "<Name>Error" or "<Name>Exception" in stderr as a
# conservative heuristic. The goal is to separate AssertionError from
# everything else; false positives on some domain exception class are
# acceptable because they still represent "harness did not test the
# thesis."
_EXCEPTION_NAME_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9_]*(?:Error|Exception))\b"
)


def classify_harness_failure(
    stderr_text: str,
    stdout_text: str = "",
) -> tuple[str, str]:
    """Return ``(status, exception_name)`` for a non-zero subprocess.

    ``exception_name`` is the most specific exception class name found
    in stderr (``""`` when none could be extracted). Callers use this
    to write the anti-rationalization note into the Judge's critique
    text.

    GP-166 Fix A (2026-04-25 night): when the regex-based exception
    name match fails (truncated stderr, wrapped exception, gate-harness
    internal print format) BUT the stderr text mentions an `assert` /
    `AssertionError` pattern, classify as FAIL_ASSERT rather than
    FAIL_OTHER.

    GP-167 Fix (2026-04-25 night, panel-revealed): substrates with
    frozen gate harnesses (gate_harness.py --run-visible-assertions)
    report gate failure via exit code 1 + JSON in stdout, with empty
    stderr. The harness has done its job; the form has been falsified
    by the gate. Previously the empty stderr made classify return
    FAIL_OTHER, which the apparatus labeled "harness defect cap" and
    capped the score at 50. This was the dominant false-positive on
    gp163d's 16-iter run history. The fix: when stderr is empty AND
    stdout contains a valid JSON envelope with `all_gates_pass: false`
    (or any of the legacy `passed: false` keys), treat as FAIL_ASSERT
    (legitimate falsification) rather than FAIL_OTHER (broken harness).
    """

    # GP-167 fix: gate-harness JSON path. When stderr is empty but the
    # subprocess exited non-zero, check whether stdout carries a gate
    # verdict. A failed gate is a falsification, not a tooling defect.
    if not stderr_text and stdout_text:
        try:
            import json as _json
            payload = _json.loads(stdout_text.strip())
            if isinstance(payload, dict):
                # Canonical gp163d-style schema
                if payload.get("all_gates_pass") is False:
                    return FAIL_ASSERT, "GateFailure"
                # Legacy individual-gate schema
                for key in ("holdout", "farther_tail", "asymptotic"):
                    sub = payload.get(key)
                    if isinstance(sub, dict) and sub.get("passed") is False:
                        return FAIL_ASSERT, "GateFailure"
        except Exception:
            pass  # fall through to regular classification

    if not stderr_text:
        return FAIL_OTHER, ""

    names = _EXCEPTION_NAME_RE.findall(stderr_text)
    if not names:
        # Fallback: still try to detect AssertionError before giving up.
        # The regex misses some formats (e.g., bare "assert <expr>" lines
        # without a Python traceback header, or stderr truncated before
        # the exception name reached buffer).
        if _ASSERT_FALLBACK_RE.search(stderr_text):
            return FAIL_ASSERT, "AssertionError"
        return FAIL_OTHER, ""

    # Python's traceback formatting puts the final exception on the
    # last line, so the *last* match in stderr is the one that
    # actually terminated the process.
    final_name = names[-1]
    if final_name == "AssertionError":
        return FAIL_ASSERT, final_name
    return FAIL_RUNTIME, final_name


# Fallback pattern: any line that looks like a bare assertion failure or
# a Python traceback whose exception name was truncated off. Conservative:
# requires either "AssertionError" verbatim or a Python traceback frame
# pointing at an `assert` statement. The frame can be inside any function
# (`in <module>`, `in test_thesis`, `in run_validation`, etc.) — the
# epistemic panel review (2026-04-25 night) caught that the original
# `<module>`-only regex missed in-function asserts, which were the
# dominant gp163d failure mode.
_ASSERT_FALLBACK_RE = re.compile(
    r"AssertionError|"
    r'File\s+"[^"]+"\s*,\s*line\s+\d+\s*,\s*in\s+\S+\s*\n[^\n]*\bassert\b',
    re.MULTILINE,
)


def sanitize_stderr_for_mutator(stderr_text: str, exception_name: str) -> str:
    """GP-157 v5.0 Gap #1 (2026-04-25 night, panel Failure Mode 1):
    strip Popper-leakage from raw stderr before it flows back to the
    mutator's prompt.

    The full traceback is preserved in the operator-facing debate log;
    only the mutator-facing summary uses this sanitized form. The mutator
    must learn from `failure_mode + exception_class + score` — never
    from internal file paths, line numbers, apparatus stack frames, or
    holdout-data structure that could be reverse-engineered into a
    test-passing regex.

    Returns a one- or two-line message:
      `<ExceptionClass>: <leaf message>` — leaf message is the LAST line
      of the traceback (the actual error text), with absolute paths
      stripped to basename. No frame info, no line numbers.

    Empty stderr → empty string. Non-traceback stderr → first non-empty
    line, path-stripped.
    """
    import re as _re
    if not stderr_text:
        return ""
    lines = [ln.rstrip() for ln in stderr_text.splitlines() if ln.strip()]
    if not lines:
        return ""
    # The leaf error line is the last non-empty line in a Python
    # traceback (e.g., "AssertionError: I_model returns NaN ...").
    leaf = lines[-1]
    # Strip absolute paths to basename: '/Users/.../foo.py' -> 'foo.py'
    leaf = _re.sub(r"(/[^\s\"',]+/)+([\w_.\-]+\.py)", r"\2", leaf)
    # Strip line-number references like "line 156"
    leaf = _re.sub(r",?\s*line\s+\d+", "", leaf)
    # Cap length to deny prompt-injection attacks via verbose error msgs
    if len(leaf) > 240:
        leaf = leaf[:237] + "..."
    if exception_name and exception_name not in leaf:
        return f"{exception_name}: {leaf}"
    return leaf


def harness_defect_banner(exception_name: str) -> str:
    """Anti-rationalization banner text for fail_runtime / fail_other.

    Goes into the Judge's Level 3 critique section so the Judge cannot
    treat a broken harness as evidence of survivorship. Phrased in the
    imperative, because the Phase 1 Judge walked past a softer
    wording in the earlier run.
    """

    exception_clause = (
        f" (terminating exception: `{exception_name}`)"
        if exception_name
        else ""
    )
    return (
        "🚨 HARNESS DEFECT — NOT A FALSIFICATION ATTEMPT.\n"
        f"The Level 3 suite did not run to completion{exception_clause}. "
        "The thesis has NOT been tested. "
        "Judge MUST treat this as an uncategorized tooling failure and "
        "MUST NOT rationalize it as evidence the thesis survived scrutiny. "
        "Any score reflecting 'mostly passed' in this state is a "
        "categorization error."
    )
