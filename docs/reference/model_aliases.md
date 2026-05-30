---
description: "Short-form model names used in the --mutator-model / --judge-model flags."
---
# Model Aliases

Quick reference for the short-form names used in `--mutator-model` /
`--judge-model` flags and where they resolve.

The CLI accepts short aliases (`gemini-pro`, `gpt4.1`, `claude-opus`) and
internally calls `resolve_model_id()` from
`src/ztare/common/llm_runtime.py:14`. If you pass an unrecognised alias
the loader raises `ValueError: Unsupported model family`.

## Canonical alias → resolved model ID

| CLI flag value | Resolved model ID (mutator/judge) | Resolved Director ID | Provider |
|---|---|---|---|
| `gemini` | `gemini-2.5-flash` | `gemini-3.1-pro-preview` | Google |
| `gemini-lite` | `gemini-3.1-flash-lite-preview` | `gemini-3.1-pro-preview` | Google |
| `gemini-pro` | `gemini-3.1-pro-preview` | `gemini-3.1-pro-preview` | Google |
| `claude` | `claude-sonnet-4-6` | `claude-sonnet-4-6` | Anthropic |
| `claude-opus` | `claude-opus-4-6` | `claude-opus-4-6` | Anthropic |
| `gpt4o` | `gpt-4o` | `o1` | OpenAI |
| `gpt4.1` | `gpt-4.1` | `gpt-4.1` | OpenAI |
| `gpt4.1-mini` | `gpt-4.1-mini` | `gpt-4.1-mini` | OpenAI |
| `gpt5.5` | `gpt-5.5` | `gpt-5.5` | OpenAI |
| `o1` | `o1` | `o1` | OpenAI (reasoning) |
| `o3` | `o3` | `o3` | OpenAI (reasoning) |
| `o3-mini` | `o3-mini` | `o3-mini` | OpenAI (reasoning) |
| `o3-pro` | `o3-pro` | `o3-pro` | OpenAI (reasoning) |
| `o4-mini` | `o4-mini` | `o4-mini` | OpenAI (reasoning) |

The Director column applies when the model is invoked as Research
Director (post-run skeptic-review pass), which uses a stronger model
than the mutator/judge for the same alias — e.g., calling `--mutator
gemini` runs `gemini-2.5-flash` for per-iter mutation but
`gemini-3.1-pro-preview` for Director synthesis.

## Recommended pairings

The default workflow pairs **cross-family** mutator and judge so blind
spots in one family don't pass undetected by the other:

| Mutator | Judge | Why |
|---|---|---|
| `gemini-pro` | `gpt4.1` | Default for cost-aware closure runs. Cross-family + good price/perf |
| `gemini-pro` | `claude-opus` | Higher signal on subtle gaming patterns; ~3× cost of the default |
| `claude-opus` | `gpt5.5` | Frontier-only when budget allows; reserved for closure attempts on hard substrates |
| `gemini-pro` | `o3` | Reasoning-judge; for proof-heavy substrates (oeis, gp090, NS-adjacent) |

**Avoid same-family pairs** (`gemini-pro` + `gemini`, `claude` +
`claude-opus`). Same-family pairings produce correlated failure modes;
the judge tends to ratify the mutator's mistakes. See `feedback_*`
memory entries for the empirical record.

## Fallback chains

If the primary model errors out (rate limit, server error, 503), each
model has a configured fallback chain in `FALLBACK_MODEL_CHAINS`
(`src/ztare/common/llm_runtime.py:125`):

| Primary | Fallback chain |
|---|---|
| `gemini-2.5-flash` | → `claude-sonnet-4-6` → `gpt-4o` |
| `gemini-3.1-flash-lite-preview` | → `gemini-2.5-flash` → `claude-sonnet-4-6` |
| `gemini-3.1-pro-preview` | → `claude-sonnet-4-6` → `gpt-4o` |
| `claude-opus-4-6` | → `claude-sonnet-4-6` → `gpt-4o` → `gemini-2.5-flash` |
| `claude-sonnet-4-6` | → `gpt-4o` → `gemini-2.5-flash` |
| `gpt-4o` | → `claude-sonnet-4-6` → `gemini-2.5-flash` |
| `gpt-4.1` | → `claude-sonnet-4-6` → `gemini-2.5-flash` |
| `gpt-5.5` | → `claude-opus-4-6` → `gpt-4.1` → `gemini-3.1-pro-preview` |
| `o1` / `o3` / `o4-mini` | cross-family chains via the same table |

When the apparatus uses a fallback, both the primary and fallback model
costs are accounted in per-model telemetry (the 2026-04-27 stealth-bill
fix; see `src/ztare/common/llm_runtime.py:107` `_record_failed_retry`).

## Reasoning-model API note

OpenAI reasoning models (`o1`, `o3*`, `o4-mini`) and the `gpt-5.*`
frontier family use the `max_completion_tokens` API parameter, not
`max_tokens`. The apparatus auto-detects this via
`is_reasoning_openai_model()` in `src/ztare/common/llm_runtime.py:166`.
You don't have to pass anything special — just be aware that calling
these models for short-form completions is more expensive per token
because the model emits hidden reasoning tokens that count against the
output cap.

## See also

- `src/ztare/common/llm_runtime.py` — authoritative MODEL_MAP source
- `docs/guides/quickstart.md` — example invocations using these aliases
- `docs/concepts/architecture.md` — where model choice fits in the
  overall mutator → judge → director flow
