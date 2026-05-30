#!/usr/bin/env python3
"""Idea feliz generator — compressed structural insights for Codex.

Instead of asking the LLM to ship a Lean patch (failure mode: invents
non-existent objects, ignores type system, 0/22 closure utility), ask
it to ship a COMPRESSED IDEA — a 2-3 sentence structural hypothesis
Codex can translate to typed Lean himself.

# Division of labor (the right one)

  - Apparatus: surface structural patterns from graph diagnostics
  - LLM: articulate patterns as mathematical insights ("idea feliz")
  - Codex: translate insights to typed Lean + verify with lake build

The novelty-prompt failed because LLMs can't safely produce typed Lean.
The typed-patch route requires constructors/eliminators the LLM doesn't
have. The middle path: ask LLM only for the COMPRESSED IDEA.

# What an idea feliz looks like

NOT: "theorem foo : sharpTarget ≤ B.gamma * nu := by sorry"
  (typed Lean — LLM hallucinates)

YES: "The Fiedler bisection reveals that angular-moment quantities only
      reach the pricing-cluster through Low*Receipt bridge nodes. If
      `nu` (viscosity) is structurally important but disconnected from
      sharpTarget, the missing closure step is plausibly a Lipschitz-
      reserve bound that routes nu→sharpTarget via the receipt bridge."
  (compressed structural intuition — Codex translates)

# Output

  analytics/public/queries/novelty/idea_feliz/<provider>_brief.md — 3-5 ideas with:
    - One-line hypothesis
    - Structural signal that motivated it (citing diagnostic + node names)
    - Suggested NEXT MOVE Codex could attempt (in informal English)
    - Honest "what would falsify this" criterion

Codex reads in ~2 min, picks 0-N to attempt translation, ignores rest.

Usage:
    python scripts/public/analytics_shared/idea_feliz_generator.py
    python scripts/public/analytics_shared/idea_feliz_generator.py --provider claude
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))


PROMPT = """You are reading structural diagnostics from a constraint-basin graph extracted from the NS Track B Lean proof spine. Your job is NOT to write Lean code. Your job is to surface 3-5 COMPRESSED MATHEMATICAL INSIGHTS that Codex (the human-in-the-loop proof author) can decide whether to translate into typed Lean himself.

# Why this format

Past LLM-as-theorem-writer attempts (novel theorem nominations, typed-patch generation) failed at 0% closure utility because LLMs invent non-existent Lean objects, ignore endpoint exposure, and propose scalar shortcuts already ruled out by existing falsifier guards. Codex needs the STRUCTURAL INTUITION the apparatus surfaces, not a Lean signature he has to discard and rewrite.

# What each insight should look like

```
## Insight N: <one-line title>

**Structural pattern:** what the graph diagnostics reveal (cite which diagnostic + which specific quantities/clusters).

**Mathematical hypothesis:** what this pattern would mean if it lifted to a real theorem (informal mathematical English, NOT Lean).

**Suggested next move:** one concrete thing Codex could attempt — either a falsifier to construct, or a bridge theorem to derive, or an existing theorem to extend. Phrase as "Codex could try X" not "theorem foo := ...".

**Falsifier criterion:** what would tell Codex this insight is wrong (e.g. "if `nu` actually appears in the receipt-tree path to sharpTarget that I missed, this insight is false").
```

Bias toward FEWER insights of HIGHER quality. If you can only produce 2 strong ones, do that. Padding with weak insights breaks the format.

# Structural diagnostics (constraint-basin graph)

{signals}

---

Now produce 3-5 compressed insights. Each one must cite specific quantities/clusters from the diagnostics above. No Lean code."""


def gather_signals():
    import llm_graph_analyst as lga
    return lga.gather_signals(include_transitivity=False)


# 2026-05-06 PM: collapsed per-provider branches into LLMRuntime
# routing. The provider names map to canonical model IDs; LLMRuntime
# handles the API call shape per provider.
from src.ztare.common.llm_runtime import LLMRuntime

_RUNTIME = LLMRuntime()

_PROVIDER_TO_MODEL_ID = {
    "gemini": "gemini-3.1-pro-preview",
    "claude": "claude-opus-4-6",
    "gpt": "gpt-4.1",  # added 2026-05-06 PM — operator may have only OpenAI keys
}


def call_provider(provider: str, prompt: str, max_tokens: int = 8000) -> str:
    """Call the named provider through LLMRuntime. Returns text or ERROR string."""
    model_id = _PROVIDER_TO_MODEL_ID.get(provider)
    if model_id is None:
        return f"ERROR: unknown provider {provider}"
    if not _RUNTIME.model_is_configured(model_id):
        family = "ANTHROPIC" if provider == "claude" else (
            "OPENAI" if provider == "gpt" else "GEMINI"
        )
        return f"ERROR: {family}_API_KEY not set"
    try:
        response = _RUNTIME.call_text(
            prompt,
            model_id=model_id,
            max_tokens=max_tokens,
            request_label="idea_feliz_generator",
        )
        return response.text or "(empty)"
    except Exception as exc:
        return f"ERROR: {type(exc).__name__}: {exc}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="gemini",
                    choices=["gemini", "claude", "both"])
    ap.add_argument("--out-dir", type=Path,
                    default=REPO / "analytics" / "public" / "queries" / "novelty" / "idea_feliz")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print("=== idea feliz generator ===")
    print("[1] gathering structural signals...")
    signals = gather_signals()
    signal_block = "\n\n".join(f"## {k}\n{v}" for k, v in signals.items())
    prompt = PROMPT.format(signals=signal_block)
    print(f"  prompt size: {len(prompt)} chars")

    providers = ["gemini", "claude"] if args.provider == "both" else [args.provider]
    for prov in providers:
        print(f"\n[{prov}] generating compressed insights...")
        output = call_provider(prov, prompt)
        out_path = args.out_dir / f"{prov}_brief.md"
        # Add a header so Codex sees what this is
        out_path.write_text(
            f"# Idea-feliz brief from {prov} ({Path(__file__).name})\n\n"
            f"**Format:** compressed structural insights, NOT typed Lean. "
            f"Codex translates to Lean himself if any are worth pursuing.\n\n"
            f"---\n\n{output}\n\n"
            f"---\n\n## Codex action\n\n"
            f"For each insight, mark one of:\n"
            f"- `worth_translating` — Codex will attempt the typed Lean version\n"
            f"- `already_have` — equivalent insight already in spine/F-row\n"
            f"- `wrong_diagnosis` — structural pattern is misread\n"
            f"- `right_pattern_wrong_move` — structural fact correct but next-move suggestion off\n"
        )
        print(f"  wrote {out_path} ({len(output)} chars)")

    print(f"\n=== done ===")
    print(f"Codex reads briefs in ~2 min, picks 0-N to translate.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
