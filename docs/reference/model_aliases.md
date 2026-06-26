---
description: "Short-form model names used in the --mutator-model / --judge-model flags."
---
# Model aliases

Quick reference for the short-form names used in `--mutator-model` /
`--judge-model` flags and where they resolve.

The CLI accepts short aliases (`gemini-pro`, `gpt4.1`, `claude-opus`) and
internally calls `resolve_model_id()` from
`src/ztare/common/llm_runtime.py`. If you pass an unrecognised alias the loader
raises `ValueError: Unsupported model family`.

## Canonical alias to resolved model ID

| CLI flag value | Resolved model ID (mutator/judge) | Resolved Director ID | Provider |
|---|---|---|---|
| `gemini` | `gemini-3.1-pro-preview` | `gemini-3.1-pro-preview` | Google |
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
| `deepseek` | `deepseek-chat` | `deepseek-chat` | DeepSeek |
| `deepseek-chat` | `deepseek-chat` | `deepseek-chat` | DeepSeek |
| `deepseek-reasoner` | `deepseek-reasoner` | `deepseek-reasoner` | DeepSeek |
| `kimi` | `kimi-k2.6` | `kimi-k2.6` | Kimi / Moonshot |
| `kimi-k2.6` | `kimi-k2.6` | `kimi-k2.6` | Kimi / Moonshot |
| `kimi-k2.5` | `kimi-k2.5` | `kimi-k2.5` | Kimi / Moonshot |
| `kimi-code` | `kimi-k2.7-code` | `kimi-k2.7-code` | Kimi / Moonshot |
| `kimi-code-fast` | `kimi-k2.7-code-highspeed` | `kimi-k2.7-code-highspeed` | Kimi / Moonshot |
| `moonshot-v1-8k` | `moonshot-v1-8k` | `moonshot-v1-8k` | Kimi / Moonshot |
| `moonshot-v1-32k` | `moonshot-v1-32k` | `moonshot-v1-32k` | Kimi / Moonshot |
| `moonshot-v1-128k` | `moonshot-v1-128k` | `moonshot-v1-128k` | Kimi / Moonshot |
| `grok` | `grok-4.3` | `grok-4.3` | Grok / xAI |
| `xai` | `grok-4.3` | `grok-4.3` | Grok / xAI |
| `grok-4.3` | `grok-4.3` | `grok-4.3` | Grok / xAI |
| `grok-code` | `grok-build-0.1` | `grok-build-0.1` | Grok / xAI |
| `grok-build` | `grok-build-0.1` | `grok-build-0.1` | Grok / xAI |
| `grok-build-0.1` | `grok-build-0.1` | `grok-build-0.1` | Grok / xAI |

The Director column applies when the model is invoked as Research
Director (post-run skeptic-review pass), which uses a stronger model
than the mutator/judge for some aliases. `gemini` now resolves to
`gemini-3.1-pro-preview` in both mutator/judge and Director contexts.

## Recommended pairings

The default workflow pairs **cross-family** mutator and judge so blind
spots in one family don't pass undetected by the other:

| Mutator | Judge | Why |
|---|---|---|
| `gemini-pro` | `gpt4.1` | Default for cost-aware closure runs. Cross-family + good price/perf |
| `gemini-pro` | `claude-opus` | Higher signal on subtle gaming patterns (~3× cost of the default) |
| `claude-opus` | `gpt5.5` | Frontier-only when budget allows, reserved for closure attempts on hard research projects |
| `gemini-pro` | `o3` | Reasoning judge for proof-heavy sequence, formal, or PDE-adjacent work |
| `kimi` | `claude` or `gpt4.1` | Low-cost agentic generation with cross-family verification |
| `kimi-code` | `claude` or `gpt4.1` | Long-context coding or repo work (keep a non-Kimi judge for auditability) |
| `grok` | `gemini-pro` or `kimi` | xAI generation with non-xAI verification, useful as another independent family |
| `grok-code` | `gemini-pro` or `gpt4.1` | Coding-agent variant with cross-family judge |

**Avoid same-family pairs** (`gemini-pro` + `gemini`, `claude` +
`claude-opus`). Same-family pairings produce correlated failure modes:
the judge tends to ratify the mutator's mistakes. See `feedback_*`
memory entries for the empirical record.

The post-champion inverter is a separate falsifier pass. Its historical default
is `gpt4.1` through `ZTARE_INVERTER_MODEL`. `ztare autoresearch run` also
accepts `--inverter <alias>` and Make accepts `INVERTER_MODEL=<alias>`.
Set it explicitly for budgeted or provider-diverse runs, for example
`--mutator kimi --judge grok --inverter claude`.

## Fallback chains

`LLMRuntime` supports configured fallback chains for callers that explicitly
want continuity after rate limits, server errors, provider outages, or billing
configuration failures. In-loop autoresearch does not use these chains by
default: `make experiment-loop` passes `--no_model_fallback` unless
`MODEL_FALLBACK=1`, and `ztare autoresearch run` requires
`--allow-model-fallback` to opt in. That default keeps runtime-family
provenance sealed for ordinary experiments.


Configured chains live in `FALLBACK_MODEL_CHAINS`:

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
| `kimi-k2.6` | → `claude-sonnet-4-6` → `gpt-4.1` → `gemini-3.1-pro-preview` |
| `kimi-k2.5` | → `kimi-k2.6` → `claude-sonnet-4-6` → `gpt-4.1` |
| `kimi-k2.7-code` | → `kimi-k2.6` → `claude-sonnet-4-6` → `gpt-4.1` |
| `kimi-k2.7-code-highspeed` | → `kimi-k2.7-code` → `kimi-k2.6` → `gpt-4.1` |
| `grok-4.3` | → `gemini-3.1-pro-preview` → `gpt-4.1` → `kimi-k2.6` |
| `grok-build-0.1` | → `grok-4.3` → `gemini-3.1-pro-preview` → `gpt-4.1` |

When the runtime uses a fallback, both the primary and fallback model
costs are accounted in per-model telemetry (the 2026-04-27 stealth-bill
fix (see `src/ztare/common/llm_runtime.py:107` `_record_failed_retry`).

## Kimi / Moonshot API note

Kimi uses the shared Chat Completions transport with
`https://api.moonshot.ai/v1`. Set `KIMI_API_KEY` locally. The official
`MOONSHOT_API_KEY` spelling is also accepted. `KIMI_BASE_URL` can
override the endpoint for a proxy or gateway.

The runtime intentionally does not alias deprecated `kimi-latest` or
`kimi-k2-*-preview` model IDs. Use `kimi` for the current general model
or `kimi-code` / `kimi-code-fast` for the K2.7 Code variants.

## Grok / xAI API note

Grok uses the shared Chat Completions transport with `https://api.x.ai/v1`.
Set `XAI_API_KEY` locally. `GROK_API_KEY` is accepted as a compatibility
alias. `XAI_BASE_URL` can override the endpoint for a proxy or gateway.

Use `grok` for xAI's current general text model (`grok-4.3`) and
`grok-code` / `grok-build` for the coding model (`grok-build-0.1`).

## Evidence search backend note

`make evidence-fetch` separates public-source search from downstream evidence
compile/runtime model choice. `MODEL=` is still passed to workspace update and
evidence compile. `EVIDENCE_SEARCH_BACKEND=auto|openai|anthropic` selects the
web-search provider used to fetch public sources. The environment spelling is
`ZTARE_EVIDENCE_SEARCH_BACKEND`. Use an explicit backend when a non-search
model label such as `deepseek`, `kimi`, or `grok` should compile or run the
project while OpenAI or Anthropic handles public source search. Fetch manifests
record the requested model, backend selector, and resolved search backend.

## Reasoning-model API note

OpenAI reasoning models (`o1`, `o3*`, `o4-mini`) and the `gpt-5.*`
frontier family take the `max_completion_tokens` API parameter; the older
`max_tokens` parameter does not apply to them. ZTARE auto-detects this via
`is_reasoning_openai_model()` in `src/ztare/common/llm_runtime.py:166`.
No special parameters are required, but calling these models for
short-form completions is more expensive per token because the model
emits hidden reasoning tokens that count against the output cap.

## See also

- `src/ztare/common/llm_runtime.py`: authoritative MODEL_MAP source
- `docs/guides/quickstart.md`: example invocations using these aliases
- `docs/concepts/architecture.md`: where model choice fits in the
  overall mutator to judge to director flow
