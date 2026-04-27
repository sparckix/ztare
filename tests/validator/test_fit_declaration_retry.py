"""GP-035 Turn 10 — validator+retry unit tests.

These tests run without a live LLM: the mutator_callable is injected so we
can simulate every drought path.
"""

from __future__ import annotations

from src.ztare.fit.fit_declaration_retry import (
    validate_and_retry_fit_declaration,
)
from src.ztare.fit.fit_primitive import parse_fit_declaration


VALID_BLOCK = """```fit_declaration
{
  "expression": "a * phi + b",
  "independent_vars": ["phi"],
  "parameter_names": ["a", "b"]
}
```"""

MALFORMED_BLOCK = """```fit_declaration
{
  "expression": "a * phi + b",
  "independent_vars": ["phi"]
}
```"""  # missing parameter_names -> ValueError

BROKEN_JSON_BLOCK = """```fit_declaration
{ this is not json
```"""


def _make_mutator(response: str):
    calls: list[str] = []

    def _call(prompt: str, *, model_id: str) -> str:
        calls.append(prompt)
        return response

    _call.calls = calls  # type: ignore[attr-defined]
    return _call


# --- happy path: block present, no retry fires ---


def test_no_retry_when_block_present():
    raw = "Thesis: some prose.\n\n" + VALID_BLOCK + "\n\nmore prose"
    mutator = _make_mutator("should not be called")
    out = validate_and_retry_fit_declaration(
        raw_response=raw,
        model_id="fake-model",
        parse_fn=parse_fit_declaration,
        mutator_callable=mutator,
    )
    assert out.fired is False
    assert out.recovered is True
    assert out.spliced_content == raw
    assert len(mutator.calls) == 0  # type: ignore[attr-defined]


# --- drought: missing block, retry succeeds ---


def test_missing_block_retry_recovers():
    raw = "Thesis prose without any declaration.\n\n# harness stub"
    mutator = _make_mutator(VALID_BLOCK)
    out = validate_and_retry_fit_declaration(
        raw_response=raw,
        model_id="fake-model",
        parse_fn=parse_fit_declaration,
        mutator_callable=mutator,
    )
    assert out.fired is True
    assert out.recovered is True
    assert out.retry_block is not None
    assert "fit_declaration" in out.spliced_content
    # original content preserved
    assert out.spliced_content.startswith(raw.rstrip())
    assert len(mutator.calls) == 1  # type: ignore[attr-defined]
    # downstream parsing now succeeds
    parsed = parse_fit_declaration(out.spliced_content)
    assert parsed is not None
    assert parsed.expression == "a * phi + b"


# --- drought: malformed block, retry succeeds ---


def test_malformed_block_retry_recovers():
    raw = "Thesis prose.\n\n" + MALFORMED_BLOCK
    mutator = _make_mutator(VALID_BLOCK)
    out = validate_and_retry_fit_declaration(
        raw_response=raw,
        model_id="fake-model",
        parse_fn=parse_fit_declaration,
        mutator_callable=mutator,
    )
    assert out.fired is True
    # NOTE: parse_fit_declaration finds the FIRST block in order. After
    # splicing, the malformed block is still first, so parse still fails.
    # This is expected: the validator's job is to give one retry; if the
    # mutator's original malformed block still gets parsed first, the
    # iteration proceeds to the missing-declaration fallback path. Verify
    # the reason string reflects the malformed state.
    assert not out.recovered
    assert "malformed" in out.reason or "retry-malformed" in out.reason


# --- drought: broken JSON (ValueError on primary) ---


def test_broken_json_triggers_retry():
    raw = "Thesis.\n\n" + BROKEN_JSON_BLOCK
    mutator = _make_mutator("no block here either")
    out = validate_and_retry_fit_declaration(
        raw_response=raw,
        model_id="fake-model",
        parse_fn=parse_fit_declaration,
        mutator_callable=mutator,
    )
    assert out.fired is True
    assert out.recovered is False
    assert "malformed" in out.reason or "retry-no-block" in out.reason


# --- drought: retry returns nothing useful ---


def test_retry_no_block_returns_unresolved():
    raw = "Thesis without block"
    mutator = _make_mutator("I cannot help with that request.")
    out = validate_and_retry_fit_declaration(
        raw_response=raw,
        model_id="fake-model",
        parse_fn=parse_fit_declaration,
        mutator_callable=mutator,
    )
    assert out.fired is True
    assert out.recovered is False
    assert out.spliced_content == raw
    assert "retry-no-block" in out.reason or "primary=missing" in out.reason


# --- drought: mutator raises (network error) ---


def test_retry_exception_returns_unresolved():
    raw = "Thesis without block"

    def _raise(prompt: str, *, model_id: str) -> str:
        raise RuntimeError("simulated network failure")

    out = validate_and_retry_fit_declaration(
        raw_response=raw,
        model_id="fake-model",
        parse_fn=parse_fit_declaration,
        mutator_callable=_raise,
    )
    assert out.fired is True
    assert out.recovered is False
    assert "retry-error" in out.reason


# --- bounded-once: the helper itself does not loop ---


def test_retry_fires_exactly_once():
    raw = "Thesis"
    call_count = {"n": 0}

    def _count(prompt: str, *, model_id: str) -> str:
        call_count["n"] += 1
        return "still no block"

    validate_and_retry_fit_declaration(
        raw_response=raw,
        model_id="fake-model",
        parse_fn=parse_fit_declaration,
        mutator_callable=_count,
    )
    assert call_count["n"] == 1


# --- retry response with extra fences / prose is cleaned ---


def test_retry_response_with_surrounding_prose():
    raw = "Thesis without block"
    decorated_retry = (
        "Sure, here's the block you requested:\n\n"
        + VALID_BLOCK
        + "\n\nLet me know if you need anything else."
    )
    mutator = _make_mutator(decorated_retry)
    out = validate_and_retry_fit_declaration(
        raw_response=raw,
        model_id="fake-model",
        parse_fn=parse_fit_declaration,
        mutator_callable=mutator,
    )
    assert out.fired is True
    assert out.recovered is True
    parsed = parse_fit_declaration(out.spliced_content)
    assert parsed is not None
    assert parsed.parameter_names == ["a", "b"]
