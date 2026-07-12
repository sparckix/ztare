"""Candidate extraction helpers for mutator responses.

The autoresearch loop historically selected the first fenced python block.
That is brittle: frontier models often include a skeleton/example block before
the actual ``test_model.py`` block, causing R1 to reject a recoverable response
and burn a full retry.  This module keeps that repair deterministic and local.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


_FENCED_BLOCK_RE = re.compile(
    r"```(?P<label>[A-Za-z0-9_+-]*)[ \t]*\n(?P<body>.*?)\n```",
    re.DOTALL,
)


@dataclass(frozen=True)
class PythonCandidateExtraction:
    python_code: str | None
    clean_thesis: str
    selected_block_index: int | None
    selected_score: int
    num_python_blocks: int
    num_fenced_blocks: int
    auto_repaired: bool


_PYTHON_CARRIER_MARKERS = (
    "def I_model",
    "def step(",
    "WORLD_MODEL_SPEC",
    "PROGRAM",
    "EXTENSIONS_SRC",
    "PARAMETRIC_FORM",
    "LAGRANGIAN",
)

_STRATEGY_RECEIPT_LINE_PREFIXES = (
    "STRATEGY_CARD_DISCHARGE:",
    "STRATEGY_CARD_RECEIPT:",
    "STRATEGY_CARD_DISCHARGE =",
    "STRATEGY_CARD_RECEIPT =",
)


def _theorem_packet_function_markers(rubric_data: dict | None) -> tuple[str, ...]:
    contract = (rubric_data or {}).get("theorem_packet_contract") or {}
    required = contract.get("required_top_level_functions") or []
    markers: list[str] = []
    for name in required:
        if isinstance(name, str) and name.strip():
            markers.append(f"def {name.strip()}")
    return tuple(markers)


def _score_python_block(
    body: str,
    theorem_packet_markers: tuple[str, ...] = (),
) -> int:
    """Score how likely a fenced block is the real ``test_model.py``.

    This is not semantic inference. It is a stable contract heuristic:
    blocks declaring the module-level apparatus names and ``I_model`` are
    preferred over illustrative snippets.
    """
    score = 0
    markers = (
        ("def step(", 105),
        ("WORLD_MODEL_SPEC", 100),
        ("PROGRAM", 95),
        ("EXTENSIONS_SRC", 90),
        ("def I_model", 100),
        ("def vector_ledger_terms", 95),
        ("def trackb_convexity_theorem", 95),
        ("def dual_state_price_kernel", 80),
        ("def accepted_trackb_outcome", 70),
        ("PARAMETRIC_FORM", 35),
        ("PARAMETER_NAMES", 30),
        ("MODEL_PARAMS", 20),
        ("INIT_RANGE", 10),
        ("from features import", 8),
        ("VISIBLE_SET", 5),
    )
    for marker, weight in markers:
        if marker in body:
            score += weight
    for marker in theorem_packet_markers:
        if marker in body:
            score += 90
    stripped = body.strip()
    if stripped.startswith("import ") or "\nimport " in body:
        score += 3
    if "..." in body:
        score -= 25
    if "return ..." in body:
        score -= 50
    return score


def _looks_like_python_carrier(text: str) -> bool:
    return any(marker in text for marker in _PYTHON_CARRIER_MARKERS)


def _unwrap_accidental_full_block_docstring(body: str) -> tuple[str, bool]:
    """Recover when a worker wraps executable carrier code in one docstring.

    This is intentionally narrow. A normal module docstring followed by code is
    valid Python and should be preserved. We only unwrap when the opening
    triple-quote contains carrier markers before its first close, meaning the
    executable body itself was quoted.
    """
    text = (body or "").strip()
    for quote in ('"""', "'''"):
        if not text.startswith(quote):
            continue
        close = text.find(quote, len(quote))
        if close < 0:
            if _looks_like_python_carrier(text[len(quote):]):
                return text[len(quote):].strip(), True
            continue
        quoted_prefix = text[len(quote):close]
        if not _looks_like_python_carrier(quoted_prefix):
            continue
        unwrapped = text[len(quote):].strip()
        if unwrapped.endswith(quote):
            unwrapped = unwrapped[: -len(quote)].rstrip()
        return unwrapped, True
    return body, False


def _extract_strategy_receipt_lines(body: str) -> tuple[str, str, bool]:
    """Move strategy-card control receipts out of candidate Python code."""
    lines = (body or "").splitlines()
    kept: list[str] = []
    receipts: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith(_STRATEGY_RECEIPT_LINE_PREFIXES):
            receipts.append(line.strip())
        else:
            kept.append(line)
    if not receipts:
        return body, "", False
    return "\n".join(kept).strip(), "\n".join(receipts).strip(), True


def normalize_python_candidate_block(body: str) -> tuple[str, str, bool]:
    """Return ``(python_code, thesis_prefix, repaired)`` for a selected block."""
    code, unwrapped = _unwrap_accidental_full_block_docstring(body)
    code, receipt_text, moved_receipt = _extract_strategy_receipt_lines(code)
    return code.strip(), receipt_text, bool(unwrapped or moved_receipt)


def extract_best_python_candidate(
    raw_text: str,
    rubric_data: dict | None = None,
) -> PythonCandidateExtraction:
    """Extract the best mutator-authored python block and thesis prose.

    Selection policy:
      1. Prefer fenced blocks labelled ``python``.
      2. If there are no labelled python blocks, allow unlabeled fenced blocks
         that look like test_model.py.
      3. Choose the highest contract-marker score, not the first block.
      4. Remove all python/test_model candidate blocks from thesis prose so
         the judge sees prose, not duplicate source code.
    """
    text = raw_text or ""
    blocks = list(_FENCED_BLOCK_RE.finditer(text))
    candidates: list[tuple[int, int, re.Match[str]]] = []
    python_blocks = 0
    theorem_packet_markers = _theorem_packet_function_markers(rubric_data)
    for idx, match in enumerate(blocks):
        label = (match.group("label") or "").strip().lower()
        body = match.group("body") or ""
        score = _score_python_block(body, theorem_packet_markers)
        is_python = label == "python"
        if is_python:
            python_blocks += 1
        if is_python or (label == "" and score >= 80):
            candidates.append((score, idx, match))

    if not candidates:
        return PythonCandidateExtraction(
            python_code=None,
            clean_thesis=text.strip(),
            selected_block_index=None,
            selected_score=0,
            num_python_blocks=python_blocks,
            num_fenced_blocks=len(blocks),
            auto_repaired=False,
        )

    # Stable tie-break: later equally-scored block wins because models often
    # show a skeleton first and the filled candidate later.
    selected_score, selected_idx, selected_match = max(candidates, key=lambda item: (item[0], item[1]))
    python_code, extracted_thesis_prefix, normalized = normalize_python_candidate_block(
        selected_match.group("body") or ""
    )

    removable_spans: list[tuple[int, int]] = []
    for score, _idx, match in candidates:
        label = (match.group("label") or "").strip().lower()
        if label == "python" or score >= 80:
            removable_spans.append((match.start(), match.end()))

    pieces: list[str] = []
    cursor = 0
    for start, end in sorted(removable_spans):
        pieces.append(text[cursor:start])
        cursor = end
    pieces.append(text[cursor:])
    clean_thesis = "".join(pieces).strip()
    if extracted_thesis_prefix:
        clean_thesis = (
            extracted_thesis_prefix
            if not clean_thesis
            else extracted_thesis_prefix + "\n\n" + clean_thesis
        )

    first_python_idx = next(
        (idx for idx, match in enumerate(blocks) if (match.group("label") or "").strip().lower() == "python"),
        None,
    )
    auto_repaired = (
        selected_idx != first_python_idx
        or python_blocks > 1
        or any((match.group("label") or "").strip() == "" for _, _, match in candidates)
        or normalized
    )
    return PythonCandidateExtraction(
        python_code=python_code,
        clean_thesis=clean_thesis,
        selected_block_index=selected_idx,
        selected_score=selected_score,
        num_python_blocks=python_blocks,
        num_fenced_blocks=len(blocks),
        auto_repaired=auto_repaired,
    )


def preserve_theorem_packet_source(
    clean_thesis: str,
    python_code: str | None,
    rubric_data: dict | None,
) -> str:
    """Keep theorem-packet source visible to the judge.

    The normal candidate extractor removes the selected ``test_model.py`` block
    from thesis prose so scalar-fit projects do not duplicate code. For
    theorem-packet substrates the code *is* the theorem packet: stripping it can
    leave ``current_iteration.md`` empty or make the judge believe required
    functions are missing even though the deterministic gate passed.
    """
    contract = (rubric_data or {}).get("theorem_packet_contract") or {}
    required = contract.get("required_top_level_functions") or []
    if not required or not python_code:
        return clean_thesis
    if "## Theorem Packet Source" in (clean_thesis or ""):
        return clean_thesis
    packet = "## Theorem Packet Source\n\n```python\n" + python_code.strip() + "\n```"
    if (clean_thesis or "").strip():
        return clean_thesis.rstrip() + "\n\n" + packet
    return (
        "This theorem-packet substrate is evaluated through the module-scope "
        "functions below; treat the packet source as the thesis content.\n\n"
        + packet
    )
