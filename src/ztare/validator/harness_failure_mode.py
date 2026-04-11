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


def classify_harness_failure(stderr_text: str) -> tuple[str, str]:
    """Return ``(status, exception_name)`` for a non-zero subprocess.

    ``exception_name`` is the most specific exception class name found
    in stderr (``""`` when none could be extracted). Callers use this
    to write the anti-rationalization note into the Judge's critique
    text.
    """

    if not stderr_text:
        return FAIL_OTHER, ""

    names = _EXCEPTION_NAME_RE.findall(stderr_text)
    if not names:
        return FAIL_OTHER, ""

    # Python's traceback formatting puts the final exception on the
    # last line, so the *last* match in stderr is the one that
    # actually terminated the process.
    final_name = names[-1]
    if final_name == "AssertionError":
        return FAIL_ASSERT, final_name
    return FAIL_RUNTIME, final_name


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
