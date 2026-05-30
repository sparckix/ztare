# GP-055 Meta-judge parse robustness seam

> **Seam metadata** · `seam_id:` GP-055 · `track:` engine · `status:` unrecorded · `last_updated:` 2026-05-08


Status: open
Opened: 2026-04-14
Owner: Daniel

## Problem

The autoresearch loop's meta-judge step crashes the whole run when the
LLM returns malformed JSON that `utils.parse_llm_json` cannot repair.
Observed live on gp023_planck_sandbox_07 iter 4 (2026-04-14, ~20:53 PT):

```
json.decoder.JSONDecodeError: Unterminated string starting at: line 21 column 7 (char 968)
  ...
  File ".../validator/test_thesis.py", line 1467, in run_meta_judge
    evaluation = utils.parse_llm_json(response.text)
  File ".../common/utils.py", line 24, in parse_llm_json
    return json.loads(repaired)
```

The repair pass in `parse_llm_json` handles unbalanced `{`/`[`/`"` counts
but does not handle truncation inside a string value — which is the
actual failure mode when Gemini hits an output length ceiling mid-token.

The exception propagates out of `run_meta_judge` and kills the iteration
with no retry. On sandbox_07 this happened twice in twelve iters (iter 4
and one earlier), which is a ~16% iteration mortality rate from a
recoverable cause. On longer runs (50-iter honeypot) the expected loss
is much worse.

## Eigenquestion

When the meta-judge LLM returns malformed JSON, should the loop (a)
retry the generation, (b) synthesize a fail-closed evaluation, or (c)
crash the iter as it does today?

## Hypotheses under test

- **H1 (retry).** A second meta-judge call with the same prompt succeeds
  on malformed-JSON failures most of the time, because truncation is
  driven by sampling variance rather than prompt pathology.
- **H2 (fail-closed).** The iter should record a `meta_judge_parse_error`
  failure and continue with a zero score rather than crash. This keeps
  the loop alive but costs one iter's worth of signal.
- **H3 (crash is correct).** Crashing is the right behavior because a
  repeated malformed response indicates a deeper contract violation that
  should be surfaced to the operator, not silently retried.

H1 is the default candidate. H3 is the Mungerian inversion to check
before writing the fix.

## Discriminating test

Run a 20-iter sandbox_07 session with (a) current behavior and (b) the
retry shim installed. Compare:

1. Number of iters that crash with `parse_llm_json` → should drop to 0
   under H1.
2. Number of iters where retry was triggered → gives the true malformed
   rate on gemini-3.1-pro-preview with schema-constrained output.
3. Whether any retried calls produced *different* meta-judge scores than
   the first attempt would have (they should not, if the retry is a pure
   robustness fix and not a score-shaping patch).

Criterion (3) is the Principle VII check — retrying must not become a
scoring knob.

## Scope boundary

This seam is about **parse robustness**, not about changing meta-judge
semantics. The fix must not:

- Change which thesis pass/fail on existing gates.
- Soften the schema or the required fields list.
- Swallow non-JSON failures (timeout, auth, content filter) — those keep
  their existing handling.

If the retry shim ends up touching any of those, it has grown past the
seam and needs a new seam.

## What would make this uninterpretable

- A retry that also swaps the prompt or adds "please return valid JSON"
  mid-retry — that's a different experiment.
- A retry that silently caps at N attempts without logging — the failure
  rate becomes invisible, defeating the point of measuring it.
- A fix that lives only in `run_meta_judge` and not in the three other
  `parse_llm_json` call sites in test_thesis.py — partial robustness is
  worse than none because it hides the pattern.

## Fix sketch

Add `parse_llm_json_with_retry(response_fn, max_retries=3)` to
`common/utils.py` or a new helper module. Each call site that currently
does:

```python
response = safe_generate(prompt, config=config)
evaluation = utils.parse_llm_json(response.text)
```

becomes:

```python
evaluation = utils.parse_llm_json_with_retry(
    lambda: safe_generate(prompt, config=config).text
)
```

The helper retries the generation (not just the parse) on
`JSONDecodeError`, logging each retry to stderr. After max_retries, it
raises a distinct `MetaJudgeParseError` that the main loop can catch and
convert to a fail-closed iter result instead of a process crash.

Expected LoC: ~30 in utils.py, ~10 across four call sites in
test_thesis.py, ~10 in autoresearch_loop.py main loop for the
fail-closed catch.

## Empirical anchor

- gp023_planck_sandbox_07 debate_log_iter_1776214536.md (iter 4,
  truncated): raw crash with no recovery.
- gp023_planck_sandbox_07 debate_log_iter_1776214895.md (iter ~5, same
  run): second crash from the same cause.

Both iters are still present on disk for forensic replay.
