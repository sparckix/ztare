"""Negative-prompting wrapper — iterative method-exhaustion (PDF §2.7, §6.1).

Per Google's "Accelerating Scientific Research with Gemini" (arXiv:2602.03837v3,
2026), the most successful methodological-diversity technique was iterative
NEGATIVE PROMPTING:

  > "By explicitly instructing the model, 'One way of solving this problem
     is to use the following method... DO NOT use this method. Reflect on
     your plan and try a different plan,' the AI autonomously discovered
     six distinct analytical methods to solve the integral."

This wrapper mechanizes that pattern. Given a target problem, it:
  1. Asks the LLM to produce a method/approach
  2. Records the method as a "method to forbid" in subsequent calls
  3. Asks again: "DO NOT use any method already tried. Find a NEW one."
  4. Repeats until N distinct methods OR LLM gives up

The point is not to find one good method — `typed_endpoint_pack.py` already
does that. The point is to AUTONOMOUSLY ENUMERATE the methodological space
so Codex can pick the most promising one.

# Why out-of-loop (RD-callable, not autoresearch_loop wired)

The autoresearch_loop already has `parallel_mutator` (GP-174) for K-way
candidate branching. That's tree-search-shaped diversity at the EXPRESSION
level. This script is a different kind of diversity: METHODOLOGICAL DIVERSITY
at the strategy level, useful for closure attempts where Codex is stuck and
wants to see what other approaches exist before committing. Different scope;
different invocation point.

# Where ZTARE doesn't already do this

`autoresearch_loop` has `forbidden_re` patterns (line 1431) — they reject
specific FORMS, not whole METHODS. `cold_llm_seed.py` has a "DO NOT use"
section but for canonical naming, not for methodological exhaustion. The
specific pattern of "iterate negative prompts to enumerate distinct
strategies" is the gap this script fills.

# Substrate-agnostic

Default prompt template is PDE-flavored but accepts arbitrary problem
statements. Use for any closure attempt where Codex wants method-space
exhaustion before committing to one approach.

Usage:
    python scripts/public/utilities/negative_prompting_wrapper.py \\
        --problem "Bound the third moment of the Leray self-tax profile" \\
        --max-methods 5
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
INITIAL_PROMPT = """You are working on a mathematical research problem. Propose ONE SPECIFIC METHODOLOGICAL APPROACH to attack it.

# Problem

{problem}

# Constraints

- Pick ONE concrete method (e.g. "energy estimate via cutoff partition", "Fourier expansion + Plancherel", "Lagrangian density variation").
- Name the method explicitly: "Method: <name>"
- Describe the high-level strategy in 2-3 sentences (not a full proof).
- Identify the KEY MATHEMATICAL TOOL or OBSERVATION that makes this method work.

Format:

Method: <name>
Strategy: <2-3 sentences>
Key tool: <the load-bearing observation>

Output ONLY this format. No preamble."""


NEGATIVE_PROMPT_TEMPLATE = """You are still working on the same mathematical research problem. Previous turns proposed these methods:

{prior_methods}

Your task: propose a NEW method that is GENUINELY DIFFERENT from all the above. DO NOT use any of those methods. Reflect on your plan and try a different plan — different toolkit, different reframing, different perspective.

# Problem

{problem}

# Constraints

- The new method must use a STRUCTURALLY DIFFERENT mathematical tool than any prior method.
- If you cannot find a new method without overlapping the prior ones, output `# METHOD-SPACE EXHAUSTED` followed by why.
- Same format as before:

Method: <name>
Strategy: <2-3 sentences>
Key tool: <the load-bearing observation>"""


# 2026-05-06: was hardcoded gemini-3-pro-preview; switched to the
# existing src/ztare/common/llm_runtime.LLMRuntime + the new
# pick_default_model_id_for_scripts() helper. Operator with only
# OpenAI / Anthropic credentials no longer has this script silently
# fail. Preference order: claude > gpt > gemini by default;
# overridable via LLM_DISPATCH_PREF env var (e.g.
# `LLM_DISPATCH_PREF=gpt,claude,gemini`).
from src.ztare.common.llm_runtime import (
    LLMRuntime,
    pick_default_model_id_for_scripts,
)

_RUNTIME = LLMRuntime()


def call_llm_provider(prompt: str, max_tokens: int = 2000) -> str:
    """Dispatch the prompt to whichever LLM provider is configured.

    Returns the text completion or an "ERROR: ..." string on total
    failure (no providers configured OR all configured providers
    errored). Uses LLMRuntime's existing fallback chain so a flaky
    provider transparently falls back to the next configured one.
    """
    model_id = pick_default_model_id_for_scripts()
    if model_id is None:
        return (
            "ERROR: no LLM provider available — set ANTHROPIC_API_KEY, "
            "OPENAI_API_KEY, or GEMINI_API_KEY"
        )
    try:
        response = _RUNTIME.call_text(
            prompt,
            model_id=model_id,
            max_tokens=max_tokens,
            request_label="negative_prompting_wrapper",
        )
        return response.text
    except Exception as exc:
        return f"ERROR: {type(exc).__name__}: {exc}"


METHOD_RE = re.compile(r"Method:\s*([^\n]+)\nStrategy:\s*([\s\S]*?)\nKey tool:\s*([^\n]+)",
                         re.IGNORECASE)


def parse_method(response: str) -> dict | None:
    if "METHOD-SPACE EXHAUSTED" in response.upper():
        return None
    m = METHOD_RE.search(response)
    if not m:
        return None
    return {
        "method_name": m.group(1).strip(),
        "strategy": m.group(2).strip(),
        "key_tool": m.group(3).strip(),
        "raw": response.strip(),
    }


def format_prior_methods(methods: list[dict]) -> str:
    return "\n\n".join(
        f"{i + 1}. **{m['method_name']}** — key tool: {m['key_tool']}\n"
        f"   strategy: {m['strategy'][:200]}"
        for i, m in enumerate(methods))


def run_negative_prompting(problem: str, max_methods: int = 5) -> list[dict]:
    methods: list[dict] = []
    for round_idx in range(max_methods):
        if round_idx == 0:
            prompt = INITIAL_PROMPT.format(problem=problem)
        else:
            prompt = NEGATIVE_PROMPT_TEMPLATE.format(
                problem=problem,
                prior_methods=format_prior_methods(methods),
            )
        print(f"\n[round {round_idx + 1}/{max_methods}] requesting "
              f"{'first method' if round_idx == 0 else 'method ≠ ' + str(len(methods)) + ' prior'}...")
        response = call_llm_provider(prompt)
        method = parse_method(response)
        if method is None:
            print(f"  apparatus reports method-space exhausted (or parse fail)")
            break
        # Check duplication against prior methods (substring on key tool)
        is_dup = any(
            method["key_tool"].lower() in m["key_tool"].lower()
            or m["key_tool"].lower() in method["key_tool"].lower()
            for m in methods
        )
        if is_dup and methods:
            print(f"  duplicate key-tool detected ({method['key_tool'][:60]}); "
                  f"prompt failed to diversify; treating as exhaustion")
            break
        methods.append(method)
        print(f"  ✓ method {len(methods)}: {method['method_name']}")
        print(f"    key tool: {method['key_tool'][:120]}")
    return methods


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--problem", required=True,
                    help="problem statement to enumerate methods for")
    ap.add_argument("--max-methods", type=int, default=5)
    ap.add_argument("--out", type=Path,
                    default=REPO / "analytics" / "public" / "queries"
                              / "negative_prompting_runs")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    print(f"=== negative-prompting wrapper ===")
    print(f"  problem: {args.problem[:120]}")
    print(f"  max methods: {args.max_methods}")

    methods = run_negative_prompting(args.problem, args.max_methods)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    safe = re.sub(r"[^A-Za-z0-9]+", "_", args.problem)[:40].lower()
    out_path = args.out / f"{timestamp}_{safe}.json"
    out_path.write_text(json.dumps({
        "ts": datetime.now(timezone.utc).isoformat(),
        "problem": args.problem,
        "n_methods": len(methods),
        "methods": methods,
    }, indent=2))

    print(f"\n=== {len(methods)} distinct methods enumerated ===")
    for i, m in enumerate(methods, 1):
        print(f"\n  {i}. {m['method_name']}")
        print(f"     key tool: {m['key_tool']}")
    print(f"\nlog: {out_path}")
    print(f"\nCodex action: review enumerated methods, pick most promising for typed-endpoint")
    return 0


if __name__ == "__main__":
    sys.exit(main())
