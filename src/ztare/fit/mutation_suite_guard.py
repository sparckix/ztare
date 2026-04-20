from __future__ import annotations


NO_SUITE_SENTINEL = "assert False, 'AI failed to provide a testable falsification suite.'"


def validate_python_suite_candidate(python_code: str | None) -> None:
    stripped = (python_code or "").strip()
    if not stripped:
        raise ValueError(
            "Missing required Python falsification suite block; reject candidate before evaluation."
        )
    if stripped == NO_SUITE_SENTINEL:
        raise ValueError(
            "Mutator emitted the no-suite sentinel falsification block; reject candidate before evaluation."
        )
