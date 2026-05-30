#!/usr/bin/env python3
"""Patch lm_eval 0.4.x token-prompt calls for vLLM 0.11+.

OLMES currently pins `lm_eval==0.4.3` and `vllm==0.11.0`. That pair can import
cleanly but fails at runtime because lm_eval calls `LLM.generate` with the
removed `prompt_token_ids=` keyword. vLLM 0.11 expects token prompts as
`TokensPrompt(prompt_token_ids=...)` objects passed through `prompts`.
"""

from __future__ import annotations

import importlib.metadata as md
from pathlib import Path


def version_tuple(text: str) -> tuple[int, ...]:
    parts = []
    for chunk in text.split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        if digits:
            parts.append(int(digits))
        else:
            break
    return tuple(parts)


def main() -> int:
    lm_eval_version = md.version("lm_eval")
    vllm_version = md.version("vllm")
    if version_tuple(vllm_version) < (0, 11):
        print(f"vllm {vllm_version}: patch not needed")
        return 0

    import lm_eval.models.vllm_causallms as target

    path = Path(target.__file__).resolve()
    text = path.read_text(encoding="utf-8")
    original = text

    text = text.replace(
        "from vllm import LLM, SamplingParams",
        "from vllm import LLM, SamplingParams, TokensPrompt",
    )
    text = text.replace(
        "prompt_token_ids=requests, sampling_params=sampling_params",
        "prompts=[TokensPrompt(prompt_token_ids=req) for req in requests], sampling_params=sampling_params",
    )
    text = text.replace(
        "prompt_token_ids=requests,\n                sampling_params=sampling_params,",
        "prompts=[TokensPrompt(prompt_token_ids=req) for req in requests],\n                sampling_params=sampling_params,",
    )

    if text == original:
        if "TokensPrompt(prompt_token_ids=req)" in text:
            print(f"already patched: {path}")
            return 0
        raise SystemExit(f"patch did not match expected lm_eval source: {path}")

    backup = path.with_suffix(path.suffix + f".ztare_pre_vllm_prompt_patch_{lm_eval_version}_{vllm_version}")
    if not backup.exists():
        backup.write_text(original, encoding="utf-8")
    path.write_text(text, encoding="utf-8")
    print(f"patched {path} for lm_eval {lm_eval_version} + vllm {vllm_version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
