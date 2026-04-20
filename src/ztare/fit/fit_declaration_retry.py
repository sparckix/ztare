"""GP-035 Turn 10 — FIT_DECLARATION drought retry.

Surgical compliance fix: when the mutator emits a thesis + harness but
omits (or malforms) the fenced ``fit_declaration`` block, make one
targeted retry that asks for the block only. Splice the block into the
original response so downstream parsers see the original thesis intact.

Constraints (see GP-035 seam Turn 10):
  - exactly one retry per iteration, hard-bounded
  - retry prompt is short; only includes trailing context from the
    previous response and the format spec
  - retry uses the same model_id as the primary mutator call
  - splicing is append-only; the original thesis + harness are
    preserved verbatim
  - validator+retry must be unit-testable without a live LLM call
    (mutator_callable is injectable)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Protocol


FIT_DECLARATION_BLOCK_RE = re.compile(
    r"```fit_declaration\s*\n(.*?)\n```", re.DOTALL
)


_RETRY_PROMPT_TEMPLATE = """The previous response was missing a well-formed fit_declaration block (or the one it contained could not be parsed). Your task in this retry is to produce ONLY the block, nothing else.

Do not repeat the thesis. Do not emit any prose. Do not emit any Python. Emit only a single fenced fit_declaration JSON block matching the schema below.

Required schema:
```fit_declaration
{{
  "expression": "<math expression using independent vars and named free parameters, only arithmetic (+,-,*,/,**) and math.* functions>",
  "independent_vars": ["<var1>", "<var2>"],
  "parameter_names": ["<p1>", "<p2>", "..."]
}}
```

Optional fields: "initial_guesses" (dict of param → float, default 1.0), "bounds" (dict of param → [lo, hi]).

CONTEXT — tail of your previous response (truncated for focus):
---
{previous_tail}
---

Your entire response must be exactly one fenced ```fit_declaration block. Do not include anything else.
"""


@dataclass
class RetryOutcome:
    fired: bool
    recovered: bool
    spliced_content: str
    retry_block: str | None
    reason: str  # human-readable short status


class _MutatorCallable(Protocol):
    def __call__(self, prompt: str, *, model_id: str) -> str: ...


def _extract_block(text: str) -> str | None:
    match = FIT_DECLARATION_BLOCK_RE.search(text)
    if not match:
        return None
    return match.group(0)  # full fenced block including fences


def _strip_stray_fences(text: str) -> str:
    """If the retry response wraps its fit_declaration in extra fences or
    prose, keep only the first fit_declaration block."""
    block = _extract_block(text)
    if block is not None:
        return block
    return text.strip()


def validate_and_retry_fit_declaration(
    *,
    raw_response: str,
    model_id: str,
    parse_fn: Callable[[str], object | None],
    mutator_callable: _MutatorCallable,
    tail_chars: int = 800,
) -> RetryOutcome:
    """Validate a mutator response for a parseable fit_declaration block.

    On success (block present and parseable): return RetryOutcome(fired=False,
    recovered=True, spliced_content=raw_response).

    On drought (missing or malformed): fire one retry via ``mutator_callable``,
    splice the recovered block into raw_response, and return the outcome.

    parse_fn should be ``parse_fit_declaration``. It returns None when the
    block is missing and raises ValueError when the block is malformed. Both
    cases trigger a retry.
    """

    # Primary validation
    try:
        parsed = parse_fn(raw_response)
    except ValueError as exc:
        primary_reason = f"malformed: {exc}"
        parsed = None
    else:
        primary_reason = "missing" if parsed is None else "ok"

    if parsed is not None:
        return RetryOutcome(
            fired=False,
            recovered=True,
            spliced_content=raw_response,
            retry_block=None,
            reason="ok",
        )

    # Drought: one targeted retry
    previous_tail = raw_response[-tail_chars:] if len(raw_response) > tail_chars else raw_response
    retry_prompt = _RETRY_PROMPT_TEMPLATE.format(previous_tail=previous_tail)

    try:
        retry_response = mutator_callable(retry_prompt, model_id=model_id)
    except Exception as exc:  # safe_mutate may raise on network / rate limit
        return RetryOutcome(
            fired=True,
            recovered=False,
            spliced_content=raw_response,
            retry_block=None,
            reason=f"retry-error: {exc}",
        )

    retry_block_text = _strip_stray_fences(retry_response or "")
    if not retry_block_text or not retry_block_text.startswith("```fit_declaration"):
        return RetryOutcome(
            fired=True,
            recovered=False,
            spliced_content=raw_response,
            retry_block=None,
            reason=f"retry-no-block (primary={primary_reason})",
        )

    # Validate the retry block against the same parser
    spliced = raw_response.rstrip() + "\n\n" + retry_block_text + "\n"
    try:
        retry_parsed = parse_fn(spliced)
    except ValueError as exc:
        return RetryOutcome(
            fired=True,
            recovered=False,
            spliced_content=raw_response,
            retry_block=retry_block_text,
            reason=f"retry-malformed: {exc}",
        )
    if retry_parsed is None:
        return RetryOutcome(
            fired=True,
            recovered=False,
            spliced_content=raw_response,
            retry_block=retry_block_text,
            reason=f"retry-unparseable (primary={primary_reason})",
        )

    return RetryOutcome(
        fired=True,
        recovered=True,
        spliced_content=spliced,
        retry_block=retry_block_text,
        reason=f"recovered (primary={primary_reason})",
    )
