#!/usr/bin/env python3
# !! DEPRECATED 2026-05-06 !!
# Closure-utility result: 0/22 novelty rate per Codex panel marking.
# Novelty prompt produces different *slogans* (0% theorem-name overlap with
# standard prompt) but every nomination is hallucinated objects, ignored
# endpoint exposure, or dimensionally-incoherent bounds.
# RETAINED for diagnostic use ONLY (falsifier of LLM novelty claims).
# DO NOT use for closure work. Use scripts/public/analytics_shared/idea_feliz_generator.py instead
# for compressed structural insights Codex can translate to typed Lean.
"""LLM novelty-nomination test — closure-utility framing.

Per Codex's finding (2026-05-06): standard LLM nominations rediscover
spine-existing edges. The right closure-utility metric is:
"does this nominate a theorem Codex would NOT have considered?"

This script reruns llm_graph_analyst-style nomination with an
adversarial-novelty prompt that explicitly instructs the LLM to
target SURPRISE — distant-cluster pairings, edges outside the
obvious receipt-tree extensions, candidates the domain expert
would not have thought of.

Then compares novelty-prompted output to standard-prompt output to
measure whether prompt engineering alone unlocks a novelty mode.

# What "success" looks like

  - Novelty-prompted nominations DIFFER substantially from standard
    nominations → there IS a surprise signal accessible
  - Both prompts produce same nominations → LLM has no novelty mode;
    closure-utility ceiling for LLM-as-graph-analyst is structural

Usage:
    python scripts/public/analytics_shared/llm_novelty_nomination.py
    python scripts/public/analytics_shared/llm_novelty_nomination.py --providers gemini,claude
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


NOVELTY_PROMPT_PREFIX = """Codex is currently hardening direct profile / Lipschitz obligations for NS Track B Clay closure. He has just confirmed that standard graph-analyst nominations (typical centrality + link-prediction surfacing) tend to rediscover edges already covered by existing theorems in the spine — they are predictively accurate but practically useless for closure.

Your job is the OPPOSITE: nominate **3 theorems a domain expert in his position would NOT have considered**. Specifically target:

  1. SURPRISING structural pairings — quantities sitting in DIFFERENT Louvain communities or DIFFERENT k-core levels that the structural diagnostics suggest should be related but currently are not
  2. CROSS-CLUSTER bridges — edges between the angular-moment/sheath cluster and the adaptive/pricing cluster (the Fiedler-bisection-identified halves) that aren't currently mediated by the Low*Receipt bridges
  3. RECEIPT-TREE OUTLIERS — quantities adjacent to currently-open obligations but not in the same theorem family — places where a non-obvious bound would unlock a structural shortcut

For each, explain WHY a domain expert would have missed it (e.g. "viscosity is structurally important but disconnected from sharpTarget by orientation, easy to overlook"; "this cross-cluster bridge requires admitting that pec_b regime-scoping at the Lipschitz level applies to the LP shell case too").

Return 3 nominations in the same Lean-block + justification format. If you can only nominate fewer that meet the SURPRISE bar, do that — padding with obvious nominations defeats the test.

---

Below are the structural signals from the constraint-basin graph (same diagnostic suite as before):

"""


def call_gemini(prompt, max_tokens=16000):
    if not os.environ.get("GEMINI_API_KEY"):
        return "ERROR: no GEMINI_API_KEY"
    from google import genai
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model="gemini-3-pro-preview", contents=prompt,
        config={"max_output_tokens": max_tokens},
    )
    parts = []
    for cand in response.candidates or []:
        if cand.content and cand.content.parts:
            for p in cand.content.parts:
                if hasattr(p, "text") and p.text:
                    parts.append(p.text)
    return "\n".join(parts) if parts else "(empty)"


def call_claude(prompt, max_tokens=8000):
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return "ERROR: no ANTHROPIC_API_KEY"
    import anthropic
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


CALLERS = {"gemini": call_gemini, "claude": call_claude}


def gather_signals():
    import llm_graph_analyst as lga
    return lga.gather_signals(include_transitivity=False)


def build_signal_block(signals):
    """Same diagnostic block as standard prompt."""
    parts = []
    for k, v in signals.items():
        parts.append(f"# {k}\n\n{v}")
    return "\n\n".join(parts)


THEOREM_NAME_RE = re.compile(r"theorem\s+([A-Za-z_][A-Za-z0-9_]*)")
LEAN_BLOCK_RE = re.compile(r"```lean\s*\n([\s\S]*?)\n\s*```")


def extract_nominations(text):
    out = []
    for m in LEAN_BLOCK_RE.finditer(text):
        block = m.group(1)
        nm = THEOREM_NAME_RE.search(block)
        out.append({
            "theorem_name": nm.group(1) if nm else "anon",
            "lean_block": block.strip(),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--providers", default="gemini,claude")
    ap.add_argument("--out-dir", type=Path,
                    default=REPO / "analytics" / "public" / "queries" / "novelty" / "novelty_nominations")
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    providers = [p.strip() for p in args.providers.split(",") if p.strip()]

    print("=== novelty-prompted nomination test ===")
    print("[1] gathering signals...")
    signals = gather_signals()
    signal_block = build_signal_block(signals)
    novelty_prompt = NOVELTY_PROMPT_PREFIX + signal_block

    # Also load the standard nominations from prior cross-LLM run for comparison
    cross_dir = REPO / "analytics" / "public" / "queries" / "novelty" / "cross_llm_nominations"
    standard_noms = {}
    for prov in providers:
        std_file = cross_dir / f"{prov}_raw.md"
        if std_file.exists():
            standard_noms[prov] = extract_nominations(std_file.read_text())

    novelty_noms = {}
    for prov in providers:
        if prov not in CALLERS:
            print(f"  unknown provider: {prov}")
            continue
        print(f"\n[{prov}] calling with novelty prompt ...")
        try:
            output = CALLERS[prov](novelty_prompt)
        except Exception as e:
            print(f"  failed: {e}")
            continue
        (args.out_dir / f"{prov}_novelty_raw.md").write_text(output)
        noms = extract_nominations(output)
        novelty_noms[prov] = noms
        print(f"  {len(noms)} novelty nominations")
        for n in noms:
            print(f"    - {n['theorem_name']}")

    # Compare names: novelty vs standard
    print(f"\n=== novelty vs standard comparison ===")
    for prov in providers:
        std = {n["theorem_name"] for n in standard_noms.get(prov, [])}
        nov = {n["theorem_name"] for n in novelty_noms.get(prov, [])}
        overlap = std & nov
        only_novel = nov - std
        only_std = std - nov
        print(f"\n  {prov}:")
        print(f"    standard nominations: {sorted(std)}")
        print(f"    novelty nominations:  {sorted(nov)}")
        print(f"    overlap (same theorem in both): {sorted(overlap)}")
        print(f"    novel-prompt-only:    {sorted(only_novel)}")
        if not std:
            print(f"    (no standard nominations on file to compare against)")
            continue
        if overlap == nov:
            print(f"    → VERDICT: prompt engineering didn't unlock novelty; "
                  f"LLM produced same theorems")
        elif not overlap:
            print(f"    → VERDICT: novelty prompt produced ENTIRELY DIFFERENT "
                  f"theorems; prompt-engineering surface real")
        else:
            ratio = len(only_novel) / max(len(nov), 1)
            print(f"    → VERDICT: {ratio:.0%} of novelty-prompted nominations "
                  f"differ from standard")

    summary_path = args.out_dir / "novelty_test_summary.json"
    summary_path.write_text(json.dumps({
        "providers": providers,
        "standard_noms": {p: [n["theorem_name"]
                                for n in standard_noms.get(p, [])]
                            for p in providers},
        "novelty_noms": {p: [n["theorem_name"] for n in novelty_noms.get(p, [])]
                            for p in providers},
    }, indent=2))
    print(f"\nwrote {summary_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
