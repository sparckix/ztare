import json
import re
import sys


class MetaJudgeParseError(Exception):
    """Raised when parse_llm_json_with_retry exhausts its retry budget."""


def parse_llm_json(raw_text):
    clean_text = raw_text.strip()
    # GP-135 (2026-04-23): extract JSON from embedded code fences or from
    # prose-prefixed responses (Claude frequently writes reasoning before
    # the JSON; the old char-0-only parser retried 3x burning budget).
    # Strategy: try char-0 first (happy path), then fall back to
    # extracting the first balanced {...} or [...] object anywhere in
    # the text.
    if clean_text.startswith("```json"):
        clean_text = clean_text[7:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
    elif clean_text.startswith("```"):
        clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
    clean_text = clean_text.strip()

    def _try_load(s):
        return json.loads(s)

    def _try_repair_and_load(s):
        repaired = s
        if repaired.count('"') % 2 != 0:
            repaired += '"'
        open_braces = repaired.count('{') - repaired.count('}')
        open_brackets = repaired.count('[') - repaired.count(']')
        repaired += ']' * max(0, open_brackets)
        repaired += '}' * max(0, open_braces)
        return json.loads(repaired)

    # 1) happy path: the whole (fence-stripped) text is JSON
    try:
        return _try_load(clean_text)
    except json.JSONDecodeError:
        pass

    # 2) fenced json block inside the response (```json ... ```)
    m_fenced = re.search(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", raw_text, re.DOTALL)
    if m_fenced:
        try:
            return _try_load(m_fenced.group(1))
        except json.JSONDecodeError:
            pass

    # 3) first balanced {...} anywhere in the text, using bracket-tracking
    #    (handles "reasoning prose before JSON" pattern common with Claude)
    for opener, closer in (("{", "}"), ("[", "]")):
        start = raw_text.find(opener)
        while start != -1:
            depth = 0
            in_str = False
            esc = False
            for i in range(start, len(raw_text)):
                c = raw_text[i]
                if in_str:
                    if esc:
                        esc = False
                    elif c == "\\":
                        esc = True
                    elif c == '"':
                        in_str = False
                elif c == '"':
                    in_str = True
                elif c == opener:
                    depth += 1
                elif c == closer:
                    depth -= 1
                    if depth == 0:
                        candidate = raw_text[start:i + 1]
                        try:
                            return _try_load(candidate)
                        except json.JSONDecodeError:
                            break
            start = raw_text.find(opener, start + 1)

    # 4) last-ditch: truncation repair on the original cleaned text
    return _try_repair_and_load(clean_text)


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
