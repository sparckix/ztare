#!/usr/bin/env python3
"""
closure_claim_discipline_linter_tier3.py — multi-LLM cross-validation
linter for closure-claim artifacts.

Tier-3 = Tier-2 run against MULTIPLE LLMs in parallel, with agreement
analysis. Catches Tier-2 single-model bias (one model hallucinating a
catch, missing a real one) by requiring cross-model agreement.

Models used (following `scripts/public/audits/cross_provider_ns_packet_rescore.py`):
- openai/gpt-4.1-mini
- anthropic/claude-haiku-4.5
- google/gemini-2.5-flash-lite

Cross-validation logic:
- Per discipline check, count how many of 3 models flag an issue.
- 3/3 = high-confidence catch.
- 2/3 = likely catch (single-model outlier ignored).
- 1/3 = low-confidence catch (single-model bias possible).
- 0/3 = clean.

Status: EXPERIMENTAL Tier-3, on top of Tier-2 EXPERIMENTAL.
Promote to default only after Tier-1 + Tier-2 sustained-value tests.

Usage:
  python3 closure_claim_discipline_linter_tier3.py check <path>
  python3 closure_claim_discipline_linter_tier3.py check <path> --providers openai,anthropic
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple


REPO = Path(__file__).resolve().parents[3]


# Reuse the same prompt template as Tier-2 (defined inline for portability)
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
      "step": "<short>",
      "issue_type": "direction_flip" | "quantifier_flip" | "dimension_flip" | "inclusion_flip" | "missing_verification" | "vocabulary_only" | "other",
      "severity": 0-9,
      "excerpt": "<short>",
      "explanation": "<1-sentence>"
    }}
  ],
  "scope_coverage": {{
    "local": "explicit" | "implicit" | "missing",
    "chain": "explicit" | "implicit" | "missing",
    "recursive": "explicit" | "implicit" | "missing",
    "meta": "explicit" | "implicit" | "missing"
  }},
  "verdict_rationale": "<2-3 sentences>"
}}

Output the JSON now.
"""


def score_openai(prompt: str, model: str = "gpt-4.1-mini") -> Dict[str, Any]:
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


def score_anthropic(
    prompt: str, model: str = "claude-haiku-4-5-20251001"
) -> Dict[str, Any]:
    import anthropic

    client = anthropic.Anthropic()
    res = client.messages.create(
        model=model,
        max_tokens=2048,
        temperature=0.2,
        messages=[
            {"role": "user", "content": prompt + "\n\nOutput ONLY the JSON object."}
        ],
    )
    text = "".join(b.text for b in res.content if hasattr(b, "text"))
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.MULTILINE)
    m = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if m:
        text = m.group(0)
    return json.loads(text)


def score_gemini(
    prompt: str, model: str = "gemini-2.5-flash-lite"
) -> Dict[str, Any]:
    import google.generativeai as genai  # type: ignore

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    genai.configure(api_key=api_key)
    m = genai.GenerativeModel(
        model,
        generation_config={
            "temperature": 0.2,
            "response_mime_type": "application/json",
        },
    )
    res = m.generate_content(prompt)
    return json.loads(res.text)


PROVIDERS: List[Tuple[str, Callable[[str], Dict[str, Any]]]] = [
    ("openai/gpt-4.1-mini", score_openai),
    ("anthropic/claude-haiku-4.5", score_anthropic),
    ("google/gemini-2.5-flash-lite", score_gemini),
]


def aggregate_pattern_026_verdicts(
    per_model: List[Tuple[str, Dict[str, Any]]],
) -> Dict[str, Any]:
    """Aggregate PATTERN-026 response shape across providers."""
    valid = [(name, r) for name, r in per_model if "error" not in r]
    n = len(valid)
    if n == 0:
        return {"agreement": 0, "consensus_verdict": "ERROR", "n_models": 0}

    verdicts = [r.get("pattern_026_tier2_verdict", "?") for _, r in valid]
    counts: Dict[str, int] = {}
    for v in verdicts:
        counts[v] = counts.get(v, 0) + 1
    consensus = max(counts.items(), key=lambda kv: kv[1])[0]

    # Cross-provider count of: paraphrase deferrals, face-saving limits,
    # corrective-bias detection, load-bearing-without-pass-gate items.
    deferrals_counts = [len(r.get("paraphrase_laundered_deferrals", [])) for _, r in valid]
    facesave_counts = [len(r.get("face_saving_limitations", [])) for _, r in valid]
    corrective_bias_yes = sum(
        1 for _, r in valid
        if r.get("corrective_bias_detected", {}).get("is_post_kill_corrective") is True
    )
    inheriting_authority_yes = sum(
        1 for _, r in valid
        if r.get("corrective_bias_detected", {}).get("treats_as_inheriting_authority") is True
    )
    load_bearing_counts = [
        len(r.get("load_bearing_components_without_pass_gate", [])) for _, r in valid
    ]
    circular_yes = sum(
        1 for _, r in valid if r.get("circular_validation", {}).get("detected") is True
    )

    # --- verdict-scope guard (added 2026-05-16, RC-A of the Birkhoff
    # false-negative incident) ---
    # A PATTERN-026 laundering verdict is scoped to ARTIFACT FRAMING
    # ("is this file face-saving?"). It does NOT adjudicate whether the
    # underlying scientific/mathematical idea is valid. A genuine-but-
    # unproved idea encoded as decorative theorems and a vacuous/circular
    # idea produce the SAME verdict here. Inferring "idea is dead /
    # settled-negative / delete" from a laundering verdict is the
    # conflation that caused the incident. Emit explicit scope +
    # disposition so the verdict cannot be silently read as idea-
    # falsification.
    is_laundering = consensus not in ("PASS", "NOT_APPLICABLE", "ERROR")
    verdict_scope = "artifact_framing_only__NOT_idea_validity"
    if is_laundering:
        disposition = (
            "RE-ENCODE-OR-ROUTE-TO-INDEPENDENT-SCIENTIFIC-REVIEW. This "
            "flags the ENCODING as face-saving (e.g. trivial theorems "
            "wrapped in narrative, isolate-and-defer). It does NOT imply "
            "the underlying idea is dead/circular/impossible. Deleting "
            "the artifact is correct; recording the IDEA as a settled "
            "negative from this verdict alone is ANTI-PATTERN-014 "
            "(verdict_scope_conflation). Before any scientific settled-"
            "negative: steelman-first review + >=2 independent adversaries "
            "OR operator inversion-reflex."
        )
    else:
        disposition = "no_laundering_in_framing__verdict_says_nothing_about_idea_merit"

    return {
        "schema": "pattern_026",
        "n_models": n,
        "consensus_verdict": consensus,
        "verdict_scope": verdict_scope,
        "disposition": disposition,
        "verdict_agreement": f"{counts[consensus]}/{n}",
        "verdict_counts": counts,
        "paraphrase_laundered_deferrals_per_model": deferrals_counts,
        "face_saving_limitations_per_model": facesave_counts,
        "corrective_bias_models_agreeing": f"{corrective_bias_yes}/{n}",
        "inheriting_authority_models_agreeing": f"{inheriting_authority_yes}/{n}",
        "load_bearing_components_without_pass_gate_per_model": load_bearing_counts,
        "circular_validation_models_agreeing": f"{circular_yes}/{n}",
    }


def aggregate_verdicts(
    per_model: List[Tuple[str, Dict[str, Any]]],
    schema: str = "closure_claim",
) -> Dict[str, Any]:
    """Cross-validate model outputs: count agreement on verdict and issues."""
    if schema == "pattern_026":
        return aggregate_pattern_026_verdicts(per_model)

    valid = [(name, r) for name, r in per_model if "error" not in r]
    n = len(valid)
    if n == 0:
        return {"agreement": 0, "consensus_verdict": "ERROR", "n_models": 0}

    verdicts = [r.get("tier2_verdict", "?") for _, r in valid]
    verdict_counts: Dict[str, int] = {}
    for v in verdicts:
        verdict_counts[v] = verdict_counts.get(v, 0) + 1
    consensus_verdict = max(verdict_counts.items(), key=lambda kv: kv[1])[0]
    consensus_count = verdict_counts[consensus_verdict]

    # Scope coverage agreement
    scope_keys = ["local", "chain", "recursive", "meta"]
    scope_consensus = {}
    for k in scope_keys:
        vals = [r.get("scope_coverage", {}).get(k, "?") for _, r in valid]
        counts: Dict[str, int] = {}
        for v in vals:
            counts[v] = counts.get(v, 0) + 1
        scope_consensus[k] = {
            "consensus": max(counts.items(), key=lambda kv: kv[1])[0],
            "agreement": max(counts.values()),
            "all_values": vals,
        }

    # Severity-aggregate issues
    all_issues = []
    for _, r in valid:
        for iss in r.get("semantic_issues", []):
            all_issues.append(iss)
    high_severity_count = sum(1 for i in all_issues if i.get("severity", 0) >= 7)

    # verdict-scope guard (RC-A, see aggregate_pattern_026_verdicts):
    # this verdict is about the ARTIFACT's closure-discipline framing,
    # never about whether the underlying idea is scientifically valid.
    return {
        "n_models": n,
        "consensus_verdict": consensus_verdict,
        "verdict_scope": "artifact_framing_only__NOT_idea_validity",
        "disposition": (
            "A discipline verdict adjudicates ENCODING/FRAMING only. Do "
            "NOT infer idea-dead / settled-negative from it; that is "
            "ANTI-PATTERN-014 (verdict_scope_conflation). Scientific "
            "settled-negative requires steelman-first + >=2 independent "
            "adversaries OR operator inversion-reflex."
        ),
        "verdict_agreement": f"{consensus_count}/{n}",
        "verdict_counts": verdict_counts,
        "scope_consensus": scope_consensus,
        "high_severity_issues_total": high_severity_count,
        "all_issues_count": len(all_issues),
    }


# Lazy import of the Tier-2 PATTERN-026 prompt template so Tier-3 can dispatch
# the architecture-laundering check across providers (per orchestration_menu
# post_kill_corrective_drafting chain step `external_reviewer_dispatch`).
def _load_pattern_026_prompt() -> str:
    import importlib.util as _u
    spec = _u.spec_from_file_location(
        "_t2", Path(__file__).with_name("closure_claim_discipline_linter_tier2.py")
    )
    if spec is None or spec.loader is None:
        return ""
    mod = _u.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return getattr(mod, "PATTERN_026_PROMPT_TEMPLATE", "")


def lint_artifact_tier3(
    path: Path,
    providers_filter: Optional[List[str]] = None,
    check_type: str = "closure_claim",
) -> Dict[str, Any]:
    """Multi-LLM cross-validation.

    check_type: "closure_claim" (default) or "pattern_026" (architecture-
    laundering audit). When pattern_026, prompts each provider with the
    Tier-2 PATTERN-026 template and aggregates the verdicts.
    """
    if not path.exists():
        return {"path": str(path), "error": "file not found"}
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return {"path": str(path), "error": f"read failed: {e}"}

    max_chars = 60000
    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[... truncated ...]"

    if check_type == "pattern_026":
        template = _load_pattern_026_prompt()
        if not template:
            return {"path": str(path), "error": "PATTERN-026 prompt template not available"}
        prompt = template.format(artifact_text=text)
    else:
        prompt = SEMANTIC_PROMPT_TEMPLATE.format(artifact_text=text)

    selected = PROVIDERS
    if providers_filter:
        selected = [
            (name, fn)
            for name, fn in PROVIDERS
            if any(p in name for p in providers_filter)
        ]

    per_model: List[Tuple[str, Dict[str, Any]]] = []
    for name, fn in selected:
        try:
            result = fn(prompt)
            per_model.append((name, result))
        except Exception as e:
            per_model.append((name, {"error": str(e)}))

    aggregate = aggregate_verdicts(
        per_model,
        schema="pattern_026" if check_type == "pattern_026" else "closure_claim",
    )
    return {
        "path": str(path),
        "check_type": check_type,
        "per_model": [{"provider": n, "result": r} for n, r in per_model],
        "aggregate": aggregate,
    }


def cmd_check(args: argparse.Namespace) -> int:
    path = Path(args.path).resolve()
    providers_filter = (
        [p.strip() for p in args.providers.split(",")] if args.providers else None
    )
    result = lint_artifact_tier3(
        path,
        providers_filter=providers_filter,
        check_type=getattr(args, "check_type", "closure_claim"),
    )
    print(json.dumps(result, indent=2))
    if "error" in result:
        return 2
    cv = result.get("aggregate", {}).get("consensus_verdict", "ERROR")
    return 0 if cv == "PASS" else 1


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Tier-3 multi-LLM cross-validation linter for closure-claim + "
            "architecture artifacts (PATTERN-026)"
        )
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("check", help="run Tier-3 multi-LLM check on artifact")
    p.add_argument("path", help="path to artifact")
    p.add_argument(
        "--providers",
        default=None,
        help="comma-separated provider filter (openai,anthropic,google)",
    )
    p.add_argument(
        "--check-type",
        default="closure_claim",
        choices=["closure_claim", "pattern_026"],
        help="Which semantic check to dispatch to all providers (default: closure_claim)",
    )
    p.set_defaults(func=cmd_check)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
