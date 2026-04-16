"""GP-070 Goal Orchestrator — Predicate composition grammar (C-14).

Primitives: has_section, no_unresolved_todos, min_words, artifact_exists.
Combinators: all_of, any_of, not.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

REGISTERED_PRIMITIVES = {
    "has_section",
    "no_unresolved_todos",
    "min_words",
    "artifact_exists",
}

REGISTERED_COMBINATORS = {"all_of", "any_of", "not"}


def evaluate_predicate(
    predicate: dict[str, Any],
    *,
    workspace_dir: Path,
    artifact_path: Path | None = None,
) -> tuple[bool, str]:
    """Evaluate a predicate against workspace artifacts.

    Returns (passed, reason).
    """
    if "all_of" in predicate:
        for sub in predicate["all_of"]:
            passed, reason = evaluate_predicate(
                sub, workspace_dir=workspace_dir, artifact_path=artifact_path
            )
            if not passed:
                return False, reason
        return True, "all conditions met"

    if "any_of" in predicate:
        reasons = []
        for sub in predicate["any_of"]:
            passed, reason = evaluate_predicate(
                sub, workspace_dir=workspace_dir, artifact_path=artifact_path
            )
            if passed:
                return True, reason
            reasons.append(reason)
        return False, "none met: " + "; ".join(reasons)

    if "not" in predicate:
        passed, reason = evaluate_predicate(
            predicate["not"], workspace_dir=workspace_dir, artifact_path=artifact_path
        )
        return not passed, f"negated: {reason}"

    if "has_section" in predicate:
        section_name = predicate["has_section"]
        if artifact_path is None or not artifact_path.exists():
            return False, f"no artifact to check for section '{section_name}'"
        text = artifact_path.read_text()
        pattern = rf"^##?\s+{re.escape(section_name)}"
        if re.search(pattern, text, re.MULTILINE | re.IGNORECASE):
            return True, f"section '{section_name}' found"
        return False, f"missing section '{section_name}'"

    if "no_unresolved_todos" in predicate:
        if artifact_path is None or not artifact_path.exists():
            return True, "no artifact to check"
        text = artifact_path.read_text()
        todos = re.findall(r"\bTODO\b", text, re.IGNORECASE)
        if todos:
            return False, f"{len(todos)} unresolved TODO(s) found"
        return True, "no TODOs"

    if "min_words" in predicate:
        threshold = int(predicate["min_words"])
        if artifact_path is None or not artifact_path.exists():
            return False, "no artifact to count words"
        text = artifact_path.read_text()
        count = len(text.split())
        if count >= threshold:
            return True, f"{count} words (>= {threshold})"
        return False, f"{count} words (< {threshold})"

    if "artifact_exists" in predicate:
        path_template = predicate["artifact_exists"]
        target = workspace_dir / path_template
        if target.exists():
            return True, f"artifact exists: {path_template}"
        return False, f"missing artifact: {path_template}"

    return False, f"unknown predicate: {predicate}"


def validate_predicate_schema(predicate: dict[str, Any]) -> list[str]:
    """Validate that a predicate only uses registered primitives/combinators."""
    errors: list[str] = []

    for key in predicate:
        if key in REGISTERED_COMBINATORS:
            if key in ("all_of", "any_of"):
                if not isinstance(predicate[key], list):
                    errors.append(f"'{key}' must be a list")
                else:
                    for sub in predicate[key]:
                        errors.extend(validate_predicate_schema(sub))
            elif key == "not":
                errors.extend(validate_predicate_schema(predicate[key]))
        elif key not in REGISTERED_PRIMITIVES:
            errors.append(f"Unknown predicate primitive: '{key}'")

    return errors
