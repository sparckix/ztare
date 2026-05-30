#!/usr/bin/env python3
"""
closure_claim_discipline_linter_tier2.py — LLM-based semantic Tier-2 check
for closure-claim artifacts.

Companion to the deterministic Tier-1 linter (`closure_claim_discipline_linter.py`).
Tier-1 catches token-level discipline gaps (no enumeration block, no scope
coverage section). Tier-2 catches SEMANTIC gaps — the artifact has the right
tokens but the chain has a direction/quantifier/inclusion flip that
token-matching can't detect.

Uses gpt-4.1-mini (cheap) via the OpenAI client following the same pattern as
`scripts/public/audits/cross_provider_ns_packet_rescore.py`.

Status: EXPERIMENTAL. Tier-1 must demonstrate sustained value first; this is
parallel infrastructure for when Tier-1 catches plateau.

Usage:
  python3 closure_claim_discipline_linter_tier2.py check <path-to-artifact>
  python3 closure_claim_discipline_linter_tier2.py check <path> --model gpt-4.1-mini
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional


REPO = Path(__file__).resolve().parents[3]


SEMANTIC_PROMPT_TEMPLATE = """You are auditing a closure-claim artifact (a markdown note or Lean file)
against the substrate's discipline rules. Be SHARPLY ADVERSARIAL.

The artifact claims a closure or partial closure of a PDE / formal-math
residual via a chain of arguments. Your task: verify that the chain has been
audited at each transition step PER THE SUBSTRATE'S 6-POINT VERIFICATION
PROTOCOL (ANTI-PATTERN-012 mitigation).

The 6 verification points (the artifact must explicitly verify each at each
transition step, not just mention them as tokens):

1. FORM: name the 1-form / operator / subspace at the input and output sides.
2. DIRECTION: verify the direction of implication / inclusion / containment.
3. QUANTIFIER: verify the quantifier scope (∀ vs ∃; pointwise vs a.e.;
   local vs global; limsup vs ∀n).
4. DOMAIN: verify domain / neighborhood / cylinder / ball.
5. DIMENSION: verify dimension / norm class / parabolic vs spatial.
6. INCLUSION: for kernel / annihilator / orthogonal-complement, check
   whether the relevant vector IS or IS NOT in the named subspace.

ADDITIONAL CHECKS (META-PATTERN-023 4-scope coverage):
- LOCAL scope: each transition step explicitly verified.
- CHAIN scope: overall chain's load-bearing piece named.
- RECURSIVE scope: sub-chains audited; recursion stabilized before encoding.
- META scope: cross-scope failure modes examined; strategic framing audited.

ARTIFACT CONTENT:
```
{artifact_text}
```

Return STRICT JSON with this schema:
{{
  "tier2_verdict": "PASS" | "PARTIAL" | "FAIL",
  "semantic_issues": [
    {{
      "step": "<short description of step>",
      "issue_type": "direction_flip" | "quantifier_flip" | "dimension_flip" | "inclusion_flip" | "missing_verification" | "vocabulary_only" | "other",
      "severity": 0-9,
      "excerpt": "<short quote from artifact>",
      "explanation": "<1-sentence explanation>"
    }}
  ],
  "scope_coverage": {{
    "local": "explicit" | "implicit" | "missing",
    "chain": "explicit" | "implicit" | "missing",
    "recursive": "explicit" | "implicit" | "missing",
    "meta": "explicit" | "implicit" | "missing"
  }},
  "ops_enumeration_quality": {{
    "ops_named": ["op1", "op2"],
    "ops_actually_applied": ["op1"],
    "vocabulary_only_ops": ["op2"]
  }},
  "verdict_rationale": "<2-3 sentences>"
}}

Be strict: PASS requires explicit per-step verification AND 4-scope coverage
AND ops actually applied (not just named). PARTIAL = most checks pass with
some semantic gaps. FAIL = significant violations.

Output the JSON now.
"""


# ---------------------------------------------------------------------------
# PATTERN-026 semantic check (added 2026-05-15)
#
# Tier-1 Check #5 catches lexical PATTERN-026 violations: missing artifact-
# citation, missing pass-gate, missing measurement, presence of launderable
# vocabulary like "first pass is crude" / "TBD" / "research thread".
#
# Tier-2 catches SEMANTIC equivalents that Tier-1's regex misses:
# - paraphrased deferrals ("v1 is approximate", "we'll refine later",
#   "the initial attempt is rough", "marked for future iteration")
# - face-saving "honest limitations" sections that name issues without
#   binding the author to retract
# - layers cited as architecturally load-bearing without measured pass-gates
# - corrective bias (artifact written in response to prior kill, biased
#   toward survival of current attempt)
# ---------------------------------------------------------------------------

PATTERN_026_PROMPT_TEMPLATE = """You are auditing a document against PATTERN-026 (primitive_before_architecture_gate).

**STEP 0 — APPLICABILITY GATE (load-bearing; check FIRST):**

PATTERN-026 only applies to documents that CLAIM TO BE AN ARCHITECTURE OR
LOAD-BEARING COMPONENT SPEC. It does NOT apply to:

- Documentation, user guides, README files explaining how to use existing tools
- Structured intelligence reports (gap reports, status reports, audits)
- Memory entries, project history, narrative writeups
- Bundles of patterns, catalogs, indexes
- Tutorials, how-to guides, FAQs
- Test results, benchmark outputs, calibration summaries

It DOES apply to:

- Architecture seams claiming a multi-component design as load-bearing
- Design proposals where named components compose into a system claim
- Primitive-validation seams (must pass-gate the primitive, not architect on it)
- Spec documents that downstream work cites as authoritative

If the document is NOT claiming architectural load-bearing, return immediately:
{{
  "pattern_026_tier2_verdict": "NOT_APPLICABLE",
  "applicability_rationale": "<one sentence on why this is not an architecture artifact>",
  "paraphrase_laundered_deferrals": [],
  "face_saving_limitations": [],
  "corrective_bias_detected": {{"is_post_kill_corrective": false, "treats_as_inheriting_authority": false, "severity": 0}},
  "load_bearing_components_without_pass_gate": [],
  "circular_validation": {{"detected": false, "excerpt": ""}},
  "verdict_rationale": "Not applicable — this is <document type>, not an architectural load-bearing spec."
}}

Only proceed to the laundering checks below if the document IS architecture.

**STEP 1 — ARCHITECTURE LAUNDERING CHECKS (only if Step 0 returns architecture):**

Be SHARPLY ADVERSARIAL — assume the artifact is over-claiming load-bearingness on
unvalidated components.

PATTERN-026 rule (mechanical):
  An architectural artifact passes iff EVERY named component (Layer / Stage /
  Phase / Route / Op / Component / Tier — anything whose failure would cause
  architecture-level claim retraction) satisfies:
  (a) artifact-citation present (concrete code file / schema / decision rule)
  (b) pass-gate defined (numeric threshold / pre-registered acceptance criterion)
  (c) measurement reported (numeric output against the pass-gate)

ADDITIONAL SEMANTIC CHECKS (the ones Tier-1 regex misses):

1. PARAPHRASE-LAUNDERED DEFERRALS. Tier-1 catches "first pass is crude" /
   "TBD" / "research thread". You catch paraphrases of the same:
   "v1 implementation is approximate" / "we'll refine later" / "marked for
   future iteration" / "the initial attempt is rough" / "scope will be
   sharpened post-hoc" / "exploratory implementation" / "subject to revision".

2. FACE-SAVING "HONEST LIMITATIONS". A section titled "honest limitations"
   or "open issues" that NAMES failure modes WITHOUT binding the author to
   retract under specific measurable conditions. Compare to: "this is
   automatically retracted iff measurement X < threshold Y" (good) vs
   "this might fail in edge cases" (bad — face-saving).

3. CORRECTIVE BIAS. Is the artifact written in response to a previous kill
   on the same topic? Look for phrases like "addresses the prior [killed]
   architecture" / "corrective to [previous seam]" / "demoted [previous]".
   If yes: is the author treating the current attempt as if it inherits the
   prior's authority? Or as if it must independently re-validate?

4. LAYER NAMING THAT HIDES COMPOSITIONALITY. "Sub-component" / "auxiliary
   step" / "helper" / "fallback path" can hide a load-bearing layer behind
   weaker language. Flag any such component whose failure would still
   retract architecture-level claims.

5. CIRCULAR VALIDATION. Pass-gate defined as "the architecture works iff
   the architecture's own audit says it works" — using self-audit as the
   measurement.

ARTIFACT CONTENT:
```
{artifact_text}
```

Return STRICT JSON:
{{
  "pattern_026_tier2_verdict": "PASS" | "PARTIAL_LAUNDERING" | "FAIL" | "NOT_APPLICABLE",
  "paraphrase_laundered_deferrals": [
    {{
      "excerpt": "<quote>",
      "paraphrase_of": "<which Tier-1 marker this paraphrases>",
      "severity": 0-9
    }}
  ],
  "face_saving_limitations": [
    {{
      "section_title": "<section name>",
      "names_issue_without_retract_bind": true | false,
      "severity": 0-9,
      "excerpt": "<quote of the unbound limitation>"
    }}
  ],
  "corrective_bias_detected": {{
    "is_post_kill_corrective": true | false,
    "prior_killed_artifact": "<seam/file referenced as previous>",
    "treats_as_inheriting_authority": true | false,
    "severity": 0-9
  }},
  "load_bearing_components_without_pass_gate": [
    {{
      "component_name": "<name>",
      "why_load_bearing": "<one sentence>",
      "missing": ["artifact_citation" | "pass_gate" | "measurement"]
    }}
  ],
  "circular_validation": {{
    "detected": true | false,
    "excerpt": "<quote>"
  }},
  "verdict_rationale": "<3-5 sentences>"
}}

PASS = no laundering, all load-bearing components fully validated, no
corrective bias, no circular validation.
PARTIAL_LAUNDERING = most components validated but ≥1 paraphrase-launderable
deferral or ≥1 face-saving limitation.
FAIL = ≥1 load-bearing component without pass-gate OR significant corrective
bias OR circular validation.

Be strict. The author of this artifact has incentive to ship; your job is to
catch the laundering before it ships. Output JSON now.
"""


def score_openai(prompt: str, model: str = "gpt-4.1-mini") -> Dict[str, Any]:
    """Same pattern as cross_provider_ns_packet_rescore.score_openai."""
    from openai import OpenAI

    client = OpenAI()
    res = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    text = res.choices[0].message.content or "{}"
    return json.loads(text)


def lint_artifact_tier2(
    path: Path,
    model: str = "gpt-4.1-mini",
    check_type: str = "closure_claim",
) -> Dict[str, Any]:
    """Run Tier-2 semantic check on a single artifact.

    check_type:
      "closure_claim"  — original ANTI-PATTERN-012 + META-PATTERN-023 + 022 audit
      "pattern_026"    — architectural laundering audit (added 2026-05-15)
      "both"           — run both and return combined result
    """
    if not path.exists():
        return {"path": str(path), "error": "file not found"}
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return {"path": str(path), "error": f"read failed: {e}"}

    # Truncate very long artifacts to fit context window comfortably
    max_chars = 60000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[... truncated ...]"

    results: Dict[str, Any] = {"path": str(path), "model": model, "check_type": check_type}

    if check_type in ("closure_claim", "both"):
        prompt = SEMANTIC_PROMPT_TEMPLATE.format(artifact_text=text)
        try:
            results["closure_claim_result"] = score_openai(prompt, model=model)
        except Exception as e:
            results["closure_claim_error"] = f"openai call failed: {e}"

    if check_type in ("pattern_026", "both"):
        prompt = PATTERN_026_PROMPT_TEMPLATE.format(artifact_text=text)
        try:
            results["pattern_026_result"] = score_openai(prompt, model=model)
        except Exception as e:
            results["pattern_026_error"] = f"openai call failed: {e}"

    # Backward-compat: when called with the legacy single-check default,
    # return the original shape (tier2_result keyed). When called with
    # pattern_026 or both, return the structured multi-check shape.
    if check_type == "closure_claim" and "closure_claim_result" in results:
        return {
            "path": str(path),
            "model": model,
            "tier2_result": results["closure_claim_result"],
        }
    if check_type == "closure_claim" and "closure_claim_error" in results:
        return {
            "path": str(path),
            "model": model,
            "error": results["closure_claim_error"],
        }
    return results


def cmd_check(args: argparse.Namespace) -> int:
    path = Path(args.path).resolve()
    result = lint_artifact_tier2(
        path, model=args.model, check_type=getattr(args, "check_type", "closure_claim")
    )
    print(json.dumps(result, indent=2))
    if "error" in result:
        return 2
    # Resolve verdict based on which check ran
    ct = result.get("check_type", "closure_claim")
    if ct == "closure_claim" or "tier2_result" in result:
        verdict = result.get("tier2_result", {}).get("tier2_verdict", "")
        return 0 if verdict == "PASS" else 1
    if ct == "pattern_026":
        verdict = result.get("pattern_026_result", {}).get("pattern_026_tier2_verdict", "")
        return 0 if verdict == "PASS" else 1
    if ct == "both":
        cc = result.get("closure_claim_result", {}).get("tier2_verdict", "")
        p26 = result.get("pattern_026_result", {}).get("pattern_026_tier2_verdict", "")
        return 0 if (cc == "PASS" and p26 == "PASS") else 1
    return 1


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Tier-2 LLM-based semantic linter for closure-claim + architecture artifacts"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("check", help="run Tier-2 semantic check on artifact")
    p.add_argument("path", help="path to artifact")
    p.add_argument(
        "--model", default="gpt-4.1-mini", help="model name (default: gpt-4.1-mini)"
    )
    p.add_argument(
        "--check-type",
        default="closure_claim",
        choices=["closure_claim", "pattern_026", "both"],
        help="Which semantic check to run (default: closure_claim for backward compat)",
    )
    p.set_defaults(func=cmd_check)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
