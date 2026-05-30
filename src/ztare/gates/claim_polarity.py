from __future__ import annotations

import ast
from collections.abc import Mapping, Sequence


DEFAULT_REJECTION_TEXT_MARKERS = (
    "not ",
    "do not ",
    "reject",
    "rejected",
    "exclude",
    "excluded",
    "exclusion",
    "inadmissible",
    "out of scope",
    "forbidden",
    "not allowed",
    "without",
    "no ",
    "insufficient",
    "not enough",
    "not_claimed",
    "not claimed",
    "does not",
    "cannot",
    "must pay",
    "only if",
)


DEFAULT_REJECTION_KEY_MARKERS = (
    "forbidden",
    "not_allowed",
    "not allowed",
    "not_claimed",
    "not claimed",
    "not_accepted",
    "not accepted",
    "not_accepted_as",
    "not accepted as",
    "excluded",
    "excluded_without",
    "exclude",
    "inadmissible",
    "nonclaim",
    "non_claim",
    "known_gap",
    "known gap",
    "weakness",
    "failure_mode",
    "failure mode",
    "fails_if",
    "fails if",
    "fail_if",
    "fail if",
    "falsifier",
    "fails",
    "rejected",
)


DEFAULT_POSITIVE_CLAIM_TEXT_MARKERS = (
    "prove ",
    "proves",
    "proved",
    "proof of",
    "theorem follows",
    "theorem is accepted",
    "accepted theorem",
    "establishes",
    "established",
    "suffices",
    "therefore",
    "hence",
    "solves",
    "global theorem",
)


DEFAULT_POSITIVE_CLAIM_KEY_MARKERS = (
    "claim",
    "theorem",
    "conclusion",
    "proof",
    "accepted_current_status",
    "current_status",
)


def is_rejection_context(
    text: str,
    *,
    markers: Sequence[str] = DEFAULT_REJECTION_TEXT_MARKERS,
) -> bool:
    """Return True when prose is explicitly rejecting or demoting a claim.

    This is intentionally a polarity helper, not a semantic theorem checker.
    It prevents a gate from treating strings inside "forbidden"/"not claimed"
    prose as positive endorsements.
    """

    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def is_rejection_key(
    key: str,
    *,
    markers: Sequence[str] = DEFAULT_REJECTION_KEY_MARKERS,
) -> bool:
    lowered = key.lower()
    return any(marker in lowered for marker in markers)


def is_positive_claim_context(
    text: str,
    *,
    markers: Sequence[str] = DEFAULT_POSITIVE_CLAIM_TEXT_MARKERS,
) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def is_positive_claim_key(
    key: str,
    *,
    markers: Sequence[str] = DEFAULT_POSITIVE_CLAIM_KEY_MARKERS,
) -> bool:
    lowered = key.lower()
    return any(marker in lowered for marker in markers)


def ast_rejection_string_lines(
    source: str,
    *,
    rejection_key_markers: Sequence[str] = DEFAULT_REJECTION_KEY_MARKERS,
) -> set[int]:
    """Return line numbers of string literals under negative-polarity keys.

    Example:

        {"not_claimed": ["Clay proof"]}

    marks only the child string line, not every nearby line. This avoids
    proximity bugs where a nearby honest caveat accidentally launders an
    actual positive claim.
    """

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()

    lines: set[int] = set()

    def string_value(node: ast.AST | None) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def mark_string_descendants(node: ast.AST) -> None:
        for child in ast.walk(node):
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                end_lineno = getattr(child, "end_lineno", child.lineno)
                lines.update(range(child.lineno, end_lineno + 1))

    def visit(node: ast.AST, rejection_context: bool = False) -> None:
        if isinstance(node, ast.Assert):
            mark_string_descendants(node)
            return
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if rejection_context or is_rejection_context(node.value):
                end_lineno = getattr(node, "end_lineno", node.lineno)
                lines.update(range(node.lineno, end_lineno + 1))
            return
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=False):
                key_text = string_value(key) or ""
                child_rejection = rejection_context or is_rejection_key(
                    key_text,
                    markers=rejection_key_markers,
                )
                if key is not None:
                    visit(key, rejection_context)
                visit(value, child_rejection)
            return
        for child in ast.iter_child_nodes(node):
            visit(child, rejection_context)

    visit(tree)
    return lines


def is_structural_rejection_match(
    lines: Sequence[str],
    idx: int,
    *,
    ast_rejection_lines: set[int] | None = None,
    lookback: int = 5,
) -> bool:
    """Return True if line index `idx` is a negative-context match.

    Preference order:
    1. AST evidence: the string literal is a child of a negative-polarity
       dictionary key.
    2. The matched line itself rejects the claim.
    3. A nearby preceding structural key rejects the child strings.
    """

    if ast_rejection_lines and idx + 1 in ast_rejection_lines:
        return True
    if is_rejection_context(lines[idx]):
        return True
    prior = "\n".join(lines[max(0, idx - lookback):idx])
    return is_rejection_key(prior)


def positive_phrase_group_labels(
    source: str,
    banned_groups: Mapping[str, Sequence[str]],
    *,
    ast_rejection_lines: set[int] | None = None,
    lookback: int = 5,
) -> list[str]:
    """Return banned-group labels used in positive, non-rejected context.

    `banned_groups` is intentionally explicit: gates still own their domain
    vocabulary. This helper only standardizes polarity so future harnesses do
    not reimplement brittle phrase-proximity logic.
    """

    lowered = source.lower()
    lines = lowered.splitlines()
    if ast_rejection_lines is None:
        ast_rejection_lines = ast_rejection_string_lines(source)

    reasons: list[str] = []
    for label, phrases in banned_groups.items():
        matched_indices: list[int] = []
        for idx, line in enumerate(lines):
            if any(phrase.lower() in line for phrase in phrases):
                matched_indices.append(idx)
        if matched_indices and not all(
            is_structural_rejection_match(
                lines,
                idx,
                ast_rejection_lines=ast_rejection_lines,
                lookback=lookback,
            )
            for idx in matched_indices
        ):
            reasons.append(label)
    return reasons


def hard_positive_phrase_group_labels(
    source: str,
    banned_groups: Mapping[str, Sequence[str]],
    *,
    rejection_key_markers: Sequence[str] = DEFAULT_REJECTION_KEY_MARKERS,
    positive_key_markers: Sequence[str] = DEFAULT_POSITIVE_CLAIM_KEY_MARKERS,
    positive_text_markers: Sequence[str] = DEFAULT_POSITIVE_CLAIM_TEXT_MARKERS,
) -> list[str]:
    """Return banned labels only when they appear as affirmative claims.

    This is stricter than `positive_phrase_group_labels`: it intentionally
    avoids hard-failing paid runs merely because a candidate names a forbidden
    move in a discriminator, falsifier, or rejected-promotion list. Ambiguous
    mentions should be routed to judge/rubric review, while hard gates block
    contract absence and clear positive endorsement.
    """

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    reasons: list[str] = []

    def string_value(node: ast.AST | None) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def visit(
        node: ast.AST,
        *,
        rejection_context: bool = False,
        positive_key_context: bool = False,
    ) -> None:
        if isinstance(node, ast.Assert):
            return
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            value = node.value
            if rejection_context or is_rejection_context(value):
                return
            hard_positive = positive_key_context or is_positive_claim_context(
                value,
                markers=positive_text_markers,
            )
            if not hard_positive:
                return
            lowered = value.lower()
            for label, phrases in banned_groups.items():
                if any(phrase.lower() in lowered for phrase in phrases):
                    reasons.append(label)
            return
        if isinstance(node, ast.Dict):
            for key, value in zip(node.keys, node.values, strict=False):
                key_text = string_value(key) or ""
                child_rejection = rejection_context or is_rejection_key(
                    key_text,
                    markers=rejection_key_markers,
                )
                child_positive = positive_key_context or is_positive_claim_key(
                    key_text,
                    markers=positive_key_markers,
                )
                if key is not None:
                    visit(
                        key,
                        rejection_context=rejection_context,
                        positive_key_context=positive_key_context,
                    )
                visit(
                    value,
                    rejection_context=child_rejection,
                    positive_key_context=child_positive,
                )
            return
        for child in ast.iter_child_nodes(node):
            visit(
                child,
                rejection_context=rejection_context,
                positive_key_context=positive_key_context,
            )

    visit(tree)
    return sorted(set(reasons))
