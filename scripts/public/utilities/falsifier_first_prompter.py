#!/usr/bin/env python3
"""Falsifier-first prompter — pec_e generator (sharpness-witness construction).

Active falsifier generation: instead of trying to PROVE the obligation,
try to FALSIFY it on toy cases. The shape of the falsifier reveals what
bound HAS to hold (and what can't).

Per GP-219 Phase 1: pec_e (Sharpness / Failure-Witness Construction) is
weakly mechanized. We have falsifier gates downstream but no generator.
This script supplies it.

# Architecture

Inverts the standard typed-endpoint pack flow:

  Standard:    LLM proposes patch → lake-build verifies
  Falsifier:   LLM proposes counterexample / hostile case →
               lake-build verifies the falsifier compiles +
               its `theorem no_X : ¬ X := ...` form rejects the obligation
               in the named sub-case

# When to use

  - When the obligation feels too strong; suspect a sub-case is false
  - When typed-endpoint patch attempts fail with `llm_refused` repeatedly
  - When Codex wants to scope down the obligation by ruling out branches

# Reuse

  - Same typed-endpoint resolution machinery (decl index, type lookup)
  - Lake-build verifier (lean_proof_gate)
  - Same Stage 4 failure-category accumulator

# Substrate-agnostic

Default falsifier prompts target NS PDE-style obligations. The
falsifier-class taxonomy (concentration / vanishing / blowup-from-below /
discrete-counterexample) is general-purpose for any substrate where
"the obligation might fail in some sub-case" is a meaningful question.

Usage:
    python scripts/public/utilities/falsifier_first_prompter.py \\
        --target TrackBProfileLipschitzControlObligation \\
        --field generated_quartic_survival_projection \\
        --falsifier-class concentration
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))


class FalsifierClass(str, Enum):
    CONCENTRATION = "concentration"
    VANISHING = "vanishing"
    BLOWUP_FROM_BELOW = "blowup_from_below"
    DISCRETE_COUNTEREXAMPLE = "discrete_counterexample"
    SCALING = "scaling"
    BOUNDARY = "boundary"


FALSIFIER_DESCRIPTIONS = {
    FalsifierClass.CONCENTRATION: """CONCENTRATION FALSIFIER

Construct a candidate that concentrates mass / energy at a point or
region the obligation is supposed to bound. The obligation should
require a uniform bound across all configurations; if it fails on a
concentrating sequence, the obligation is too strong.

Shape: theorem no_<obligation>_under_concentration
    (h_concentrated : <field>_concentrates_at_point) :
    ¬ <obligation_property> := by ...""",

    FalsifierClass.VANISHING: """VANISHING FALSIFIER

Construct a candidate where the bounded quantity vanishes (or becomes
arbitrarily small) but the bound still has to hold by other means.
The obligation may not be testable on vanishing cases; if so, it needs
a positivity / non-degeneracy hypothesis.

Shape: theorem no_<obligation>_in_vanishing_limit
    (h_vanish : Tendsto <field> 0) : ¬ <obligation_property> := by ...""",

    FalsifierClass.BLOWUP_FROM_BELOW: """BLOWUP-FROM-BELOW FALSIFIER

Construct a candidate where a putatively bounded quantity grows
unboundedly, despite the obligation claiming it stays bounded.

Shape: theorem no_<obligation>_under_unbounded_growth
    (h_unbounded : ∀ M, ∃ t, <field>(t) > M) :
    ¬ <obligation_property> := by ...""",

    FalsifierClass.DISCRETE_COUNTEREXAMPLE: """DISCRETE COUNTEREXAMPLE

Construct an explicit finite-dimensional discrete instance that
violates the obligation. Useful when the continuous obligation has a
discrete analog whose counterexamples are easier to construct.

Shape: theorem no_<obligation>_on_<specific_discrete_case>
    : ¬ <obligation_property> := by exact <explicit_construction>""",

    FalsifierClass.SCALING: """SCALING FALSIFIER

Construct a 1-parameter family rescaling the obligation; show that the
bound's constant explodes as the scale parameter goes to a critical
value. The obligation must be scale-invariant; if it isn't, there's a
violating scale.

Shape: theorem no_<obligation>_at_critical_scale
    (h_scale : <scale_parameter> = critical_value) :
    ¬ <obligation_property> := by ...""",

    FalsifierClass.BOUNDARY: """BOUNDARY FALSIFIER

Construct a candidate concentrated at a domain boundary or at infinity.
Useful when the obligation has implicit interior assumptions that fail
at the boundary.

Shape: theorem no_<obligation>_at_boundary
    (h_boundary : <field>_supported_near_boundary) :
    ¬ <obligation_property> := by ...""",
}


PROMPT_TEMPLATE = """You are constructing a FALSIFIER for the NS Track B obligation `{target}`. Your job is NOT to prove the obligation; it is to find an explicit case where the obligation FAILS.

# Why we're doing this

Standard typed-endpoint patch attempts have failed with `llm_refused`. Either the obligation is genuinely true and we need missing primitives, OR a specific sub-case violates the obligation and the closure should narrow to the remaining cases. This falsifier-first probe tests the second option.

# Falsifier class

{falsifier_description}

# Target context

Target: {target}
Field: {field}
Field type: {field_type}

# Existing falsifier-style theorems in the spine (for reference patterns)

{existing_falsifiers}

# Resolved type info

{type_info}

# Strict constraints

- Output ONE Lean file in a single ```lean fenced block
- Theorem name MUST start with `no_` (matches existing falsifier-guard convention)
- Reference ONLY declarations in the resolved set above
- Do NOT use sorry/admit/axiom/native_decide
- If you cannot construct a falsifier (i.e., the obligation seems genuinely true), output `# CANNOT FALSIFY` followed by a one-paragraph diagnosis: which sub-case did you try to violate, and why does the obligation hold there?

# Honest scope

A successful falsifier is a real mathematical finding: it tells Codex which sub-case to scope OUT of the obligation's claim. A `# CANNOT FALSIFY` outcome is also signal: the apparatus has tried to break the obligation in this class and could not.

Return your falsifier in a single ```lean fenced block, OR `# CANNOT FALSIFY` with diagnosis."""


# 2026-05-06 PM: was hardcoded gemini-3-pro-preview; switched to
# LLMRuntime + pick_default_model_id_for_scripts.
from src.ztare.common.llm_runtime import (
    LLMRuntime,
    pick_default_model_id_for_scripts,
)

_RUNTIME = LLMRuntime()


def call_gemini(prompt: str, max_tokens: int = 6000) -> str:
    """Provider-agnostic LLM call (legacy name preserved)."""
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
            request_label="falsifier_first_prompter",
        )
        return response.text or "(empty)"
    except Exception as exc:
        return f"ERROR: {type(exc).__name__}: {exc}"


def find_existing_falsifiers(target_name_substring: str, top_n: int = 6) -> list[dict]:
    """Find existing 'no_X' theorems in the spine."""
    out = []
    decl_re = re.compile(r"^(theorem|lemma)\s+(no_[A-Za-z0-9_]+)", re.MULTILINE)
    for path in (REPO / "ztare_proofs" / "ZtareProofs").glob("ns_*.lean"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for m in decl_re.finditer(text):
            tname = m.group(2)
            # Quick relevance: prefer ones that reference the target
            relevance = (target_name_substring.lower() in tname.lower()
                         or target_name_substring.lower() in path.stem.lower())
            start = m.start()
            preview = text[start:start + 250].replace("\n", " ")
            out.append({"name": tname, "file": path.stem,
                        "preview": preview,
                        "relevance": 1 if relevance else 0})
    out.sort(key=lambda r: -r["relevance"])
    return out[:top_n]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("--field", required=True)
    ap.add_argument("--falsifier-class",
                    choices=[c.value for c in FalsifierClass],
                    default=FalsifierClass.CONCENTRATION.value)
    ap.add_argument("--max-revisions", type=int, default=2)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out-dir", type=Path,
                    default=REPO / "analytics" / "public" / "queries" / "falsifier_runs")
    args = ap.parse_args()
    args.falsifier_class = FalsifierClass(args.falsifier_class)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== falsifier-first prompter ===")
    print(f"  target: {args.target}")
    print(f"  field:  {args.field}")
    print(f"  class:  {args.falsifier_class.value}")

    from typed_endpoint_pack import (
        load_workmap_target, resolve_field, find_type_constructors,
        load_decl_index,
    )
    target_obj = load_workmap_target(args.target)
    if not target_obj:
        print(f"  target not in workmap")
        return 1
    field_info = resolve_field(target_obj, args.field)
    if not field_info:
        print(f"  field not in target")
        return 1
    decl_index = load_decl_index()
    constructors = find_type_constructors(field_info["type_head"], decl_index)
    existing_falsifiers = find_existing_falsifiers(args.target[:25])

    type_info_block = "\n".join(
        f"- {c['kind']} {c['type_head']} ({c['file']}.lean): {len(c['fields'])} fields"
        for c in constructors) or "(no constructors resolved)"
    falsifier_block = "\n".join(
        f"- {f['name']} ({f['file']}.lean):\n  {f['preview'][:120]}"
        for f in existing_falsifiers) or "(no existing falsifiers found)"

    prompt = PROMPT_TEMPLATE.format(
        target=args.target, field=args.field,
        field_type=field_info["field_type"],
        falsifier_description=FALSIFIER_DESCRIPTIONS[args.falsifier_class],
        type_info=type_info_block,
        existing_falsifiers=falsifier_block,
    )
    print(f"  prompt size: {len(prompt)} chars")

    if args.dry_run:
        print(f"\n[dry-run] skipping LLM call + lake build")
        return 0

    print(f"\n[calling Gemini for falsifier]")
    response = call_gemini(prompt)
    out_path = args.out_dir / f"{args.target}_{args.field}_{args.falsifier_class.value}.md"
    out_path.write_text(response)
    print(f"  response: {len(response)} chars → {out_path}")

    if "# CANNOT FALSIFY" in response.upper():
        print(f"\n  Gemini reported CANNOT FALSIFY — meaningful negative result")
        print(f"  the obligation appears genuinely true in this falsifier class")
        return 0

    print(f"\n  falsifier candidate produced. Codex should validate before lake-build.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
