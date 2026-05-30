#!/usr/bin/env python3
"""Patch-class auto-selector — meta-prompt that picks the right class.

Removes operator judgment from the typed-endpoint loop. Given a
(target, field) pair, asks the LLM to look at the field's type +
nearby theorems + obligation context, and decide which of the 4 patch
classes fits best (or output `# CANNOT CLASSIFY` and a reason).

# Selection heuristics the LLM is told to use

  TRANSITIVITY_ADAPTER     when the field is an inequality / Prop bound
                           and ≥2 nearby theorems share variables with it
  BRANCH_WISE_FALSIFIER    when the obligation is suspected of being
                           false in some sub-case (e.g. has a `branch`
                           or `case` field, or sibling `no_X` falsifiers)
  SOURCE_PROVENANCE_BRIDGE when the field is bounded by a ParentStruct
                           projection that exists but isn't named
  INSTANCE_WITH_EVIDENCE   when the field type is itself a structure
                           that needs construction with field-evidence

# Output

  Single JSON line with: {"chosen_class": "...", "rationale": "...",
                            "confidence": "high|medium|low"}

  Or "# CANNOT CLASSIFY" + reason if no class fits.

# Usage

  python scripts/public/lean/patch_class_selector.py \\
      --target TrackBProfileLipschitzControlObligation \\
      --field profile_obligation

  # or auto-select + run typed_endpoint_pack:
  python scripts/public/lean/patch_class_selector.py \\
      --target X --field Y --then-run
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


SELECTOR_PROMPT = """You are an apparatus that classifies a Lean obligation field into ONE of 4 well-defined patch classes. Pick the BEST-FIT class (or refuse) based on the typed context below. Do NOT generate a Lean patch — only classify.

# The 4 patch classes

  TRANSITIVITY_ADAPTER
    When the field is a Prop / inequality and ≥2 existing theorems share
    its quantities. Glue them with le_trans / linarith.

  BRANCH_WISE_FALSIFIER
    When the obligation is suspected of being FALSE in some sub-case.
    Look for: branch / case fields in obligation; sibling `no_X` files
    in the spine; inductive cases the obligation discriminates on.

  SOURCE_PROVENANCE_BRIDGE
    When the field is bounded by a ParentStruct projection that exists
    but isn't named as a separate theorem.

  INSTANCE_WITH_EVIDENCE
    When the field's TYPE is itself a structure that needs to be
    constructed by supplying evidence for each of ITS fields.

# Heuristic priority (use in order)

  1. Inspect the RETURN type, not arbitrary premise text.  If the returned
     type is itself a resolved structure → INSTANCE_WITH_EVIDENCE.
  2. If the returned type is an inequality / equality / scalar bound →
     TRANSITIVITY_ADAPTER.
  3. If obligation has multiple branches/cases → BRANCH_WISE_FALSIFIER.
  4. If the returned type is a named predicate/provenance object and the
     inequality/equality appears only in premises → SOURCE_PROVENANCE_BRIDGE.
  5. Default fallback when none clearly fits → SOURCE_PROVENANCE_BRIDGE.

# Target context

Target obligation: {target_name}
File: {target_file}
Field name: {field_name}
Field type: {field_type}
Type head: {type_head}

# Resolved type (constructors of {type_head})

{constructors}

# Nearby existing theorems (top-{n_nearby} by uses)

{nearby}

# Sibling files matching falsifier patterns

{falsifier_files}

---

Return EXACTLY ONE line of JSON. Do not include other text.

Schema:
{{"chosen_class": "transitivity_adapter|branch_wise_falsifier|source_provenance_bridge|instance_with_evidence",
  "rationale": "<1-2 sentences citing specific structural evidence above>",
  "confidence": "high|medium|low"}}

Or:
{{"chosen_class": "cannot_classify", "rationale": "<reason>", "confidence": "high"}}"""


def call_gemini(prompt: str, max_tokens: int = 600) -> str:
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


def return_type_segment(field_type: str) -> str:
    """Best-effort return-type extraction for Lean function field types.

    The selector should classify the object being produced, not every
    hypothesis in a dependent arrow chain.  This intentionally stays syntactic:
    it is a cheap guard before the typed endpoint pack and does not attempt
    full Lean parsing.
    """
    parts = [p.strip() for p in re.split(r"\s*→\s*", field_type) if p.strip()]
    return parts[-1] if parts else field_type.strip()


def looks_like_bound_type(type_text: str) -> bool:
    """Return True when the produced type itself is a scalar relation."""
    stripped = type_text.strip()
    if stripped.startswith(("≤", "<", "≥", ">", "=")):
        return True
    relation_re = r"(^|[)\]\w.])\s*(≤|<|≥|>|=)\s*([^=]|$)"
    return bool(re.search(relation_re, stripped))


def heuristic_select(target: str, field: str) -> dict:
    """Deterministic patch-class classifier.

    This is intentionally conservative: it avoids live LLM spend and returns
    a class only from field type, resolved constructors, and nearby theorem
    evidence.  Use the Gemini backend only when this local selector is too
    coarse for a high-value target.
    """
    from typed_endpoint_pack import (
        load_workmap_target, resolve_field, find_type_constructors,
        find_theorems_using_field, load_decl_index,
    )
    target_obj = load_workmap_target(target)
    if not target_obj:
        return {"chosen_class": "cannot_classify",
                "rationale": f"target {target!r} not in workmap",
                "confidence": "high"}
    field_info = resolve_field(target_obj, field)
    if not field_info:
        return {"chosen_class": "cannot_classify",
                "rationale": f"field {field!r} not in target",
                "confidence": "high"}
    decl_index = load_decl_index()
    constructors = find_type_constructors(field_info["type_head"], decl_index)
    nearby = find_theorems_using_field(field, field_info["type_head"], top_n=8)
    ftype = field_info["field_type"]
    return_type = return_type_segment(ftype)
    type_head = field_info["type_head"]
    field_l = field.lower()
    if constructors and type_head not in (None, "Prop"):
        return {
            "chosen_class": "instance_with_evidence",
            "rationale": (
                f"{field!r} returns resolved structure {type_head}; "
                "constructing an instance is the only non-decorative class."
            ),
            "confidence": "high",
            "backend": "heuristic",
        }
    if looks_like_bound_type(return_type):
        return {
            "chosen_class": "transitivity_adapter",
            "rationale": (
                "returned type is a scalar relation; try typed bound "
                "composition first"
            ),
            "confidence": "medium" if nearby else "low",
            "backend": "heuristic",
        }
    if ("branch" in field_l or "falsifier" in field_l or "case" in field_l
            or "dichotomy" in ftype.lower()):
        return {
            "chosen_class": "branch_wise_falsifier",
            "rationale": "field name/type indicates branch or dichotomy structure",
            "confidence": "medium",
            "backend": "heuristic",
        }
    if "Prop" in return_type or (type_head and type_head not in (None, "Prop")):
        return {
            "chosen_class": "source_provenance_bridge",
            "rationale": (
                "returned type is a named predicate/provenance object; "
                "premise inequalities should not force a transitivity patch."
            ),
            "confidence": "low",
            "backend": "heuristic",
        }
    return {
        "chosen_class": "cannot_classify",
        "rationale": "no resolved structure, inequality, or branch/provenance signal",
        "confidence": "medium",
        "backend": "heuristic",
    }


def llm_select(target: str, field: str) -> dict:
    """Classify (target, field) into a patch class via Gemini."""
    from typed_endpoint_pack import (
        load_workmap_target, resolve_field, find_type_constructors,
        find_theorems_using_field, load_decl_index,
    )
    target_obj = load_workmap_target(target)
    if not target_obj:
        return {"chosen_class": "cannot_classify",
                "rationale": f"target {target!r} not in workmap",
                "confidence": "high"}
    field_info = resolve_field(target_obj, field)
    if not field_info:
        return {"chosen_class": "cannot_classify",
                "rationale": f"field {field!r} not in target",
                "confidence": "high"}
    decl_index = load_decl_index()
    constructors = find_type_constructors(field_info["type_head"], decl_index)
    nearby = find_theorems_using_field(field, field_info["type_head"], top_n=8)

    # Find sibling falsifier files
    target_short = target.replace("Obligation", "").replace("Receipt", "")[:30]
    falsifier_files = []
    for path in (REPO / "ztare_proofs" / "ZtareProofs").glob("*.lean"):
        if "falsifier" in path.stem.lower() or "no_" in path.stem.lower():
            falsifier_files.append(path.stem)
    falsifier_files = falsifier_files[:6]

    constructors_block = "\n".join(
        f"- {c['kind']} {c['type_head']} ({c['file']}.lean): "
        f"{len(c['fields'])} fields"
        for c in constructors) or "(no constructors resolved)"
    nearby_block = "\n".join(
        f"- {t['name']} ({t['file']}.lean) score={t['score']}"
        for t in nearby) or "(no nearby theorems)"

    prompt = SELECTOR_PROMPT.format(
        target_name=target,
        target_file=target_obj.get("file", "?"),
        field_name=field,
        field_type=field_info["field_type"],
        type_head=field_info["type_head"],
        constructors=constructors_block,
        nearby=nearby_block,
        n_nearby=len(nearby),
        falsifier_files="\n".join(f"- {f}" for f in falsifier_files) or "(none)",
    )
    response = call_gemini(prompt)
    # Extract JSON
    json_match = re.search(r"\{[^{}]*\"chosen_class\"[^{}]*\}", response,
                            re.DOTALL)
    if not json_match:
        return {"chosen_class": "cannot_classify",
                "rationale": f"LLM returned no JSON: {response[:200]}",
                "confidence": "low"}
    try:
        out = json.loads(json_match.group(0))
        out["backend"] = "gemini"
        return out
    except json.JSONDecodeError as e:
        return {"chosen_class": "cannot_classify",
                "rationale": f"JSON parse failed: {e}",
                "confidence": "low"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target", required=True)
    ap.add_argument("--field", required=True)
    ap.add_argument("--backend", choices=["heuristic", "gemini"],
                    default="heuristic",
                    help="heuristic is free/local; gemini spends an API call")
    ap.add_argument("--then-run", action="store_true",
                    help="if class selected, run typed_endpoint_pack with it")
    ap.add_argument("--out", type=Path,
                    default=REPO / "analytics" / "public" / "queries" /
                              "patch_class_selections.jsonl")
    args = ap.parse_args()

    print(f"=== patch-class auto-selector ===")
    print(f"  target: {args.target}")
    print(f"  field:  {args.field}")
    print(f"  backend: {args.backend}")
    selection = (llm_select(args.target, args.field)
                 if args.backend == "gemini"
                 else heuristic_select(args.target, args.field))
    print(f"\n  chosen_class: {selection.get('chosen_class')}")
    print(f"  confidence:   {selection.get('confidence')}")
    print(f"  rationale:    {selection.get('rationale')}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    from datetime import datetime, timezone
    with args.out.open("a") as f:
        f.write(json.dumps({
            "ts": datetime.now(timezone.utc).isoformat(),
            "target": args.target, "field": args.field,
            **selection,
        }) + "\n")

    if args.then_run and selection.get("chosen_class") not in (
            "cannot_classify", None):
        print(f"\n  → running typed_endpoint_pack with class "
              f"{selection['chosen_class']}...")
        result = subprocess.run([
            "./venv/bin/python", "scripts/public/lean/typed_endpoint_pack.py",
            "--target", args.target, "--field", args.field,
            "--patch-class", selection["chosen_class"],
        ], cwd=REPO)
        return result.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
