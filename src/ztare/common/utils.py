import json
import re
import sys


class MetaJudgeParseError(Exception):
    """Raised when parse_llm_json_with_retry exhausts its retry budget."""


def parse_llm_json(raw_text):
    clean_text = raw_text.strip()
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:-3]
    elif clean_text.startswith("```"):
        clean_text = clean_text[3:-3]
    clean_text = clean_text.strip()
    try:
        return json.loads(clean_text)
    except json.JSONDecodeError:
        # Attempt to repair truncated JSON by closing open strings/objects/arrays
        repaired = clean_text
        # Close any unterminated string
        if repaired.count('"') % 2 != 0:
            repaired += '"'
        # Close open brackets/braces
        open_braces = repaired.count('{') - repaired.count('}')
        open_brackets = repaired.count('[') - repaired.count(']')
        repaired += ']' * max(0, open_brackets)
        repaired += '}' * max(0, open_braces)
        return json.loads(repaired)


def parse_llm_json_with_retry(generate_fn, *, max_retries=3, call_site="llm_json"):
    """Call ``generate_fn`` and parse its result as JSON with retry on parse failure.

    ``generate_fn`` must be a zero-arg callable returning the raw LLM text
    (so the generation itself is retried, not just the parse — sampling
    variance is the usual cause of mid-string truncation on schema-
    constrained Gemini calls).

    Non-JSON exceptions from ``generate_fn`` are not caught here — they
    keep their existing handling (timeouts, auth failures, content
    filters). Only ``json.JSONDecodeError`` triggers a retry.

    Raises ``MetaJudgeParseError`` once the retry budget is exhausted.
    """
    last_err = None
    last_text = ""
    for attempt in range(1, max_retries + 1):
        text = generate_fn()
        last_text = text
        try:
            return parse_llm_json(text)
        except json.JSONDecodeError as exc:
            last_err = exc
            print(
                f"[{call_site}] parse_llm_json attempt {attempt}/{max_retries} "
                f"failed: {exc}. Retrying generation.",
                file=sys.stderr,
            )
    preview = (last_text or "")[:400].replace("\n", " ")
    raise MetaJudgeParseError(
        f"parse_llm_json exhausted {max_retries} retries at {call_site}; "
        f"last error={last_err}; preview={preview!r}"
    )
