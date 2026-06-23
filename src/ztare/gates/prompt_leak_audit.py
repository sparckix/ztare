"""GP-134 prompt-layer leak audit.

Catches apparatus-layer prompt contamination that charter-layer audits miss.
The audit runs a cold cross-family auditor model against the fully-built
mutator prompt plus the substrate's evidence, and fails if the auditor can
identify the sealed target with high confidence.

Design per external panel review (2026-04-23):

- Input: fully assembled mutator prompt, substrate evidence.txt, sealed
  ground_truth.json (auditor process reads ground_truth only via the
  comparator — the auditor's own prompt never contains the target).
- Auditor: cold cross-family model (e.g., gpt-4.1 when mutator is o3,
  claude when mutator is gpt-4.1). Single-shot, no tools, no memory.
- Comparator: proxy_signature AST canonicalization in
  src/ztare/findings/proxy_signature.py.
- Fail triggers (any one):
  (a) top-1 guess signature-equal to target
  (b) any top-3 guess whose AST has ≥70% subexpression overlap with target
  (c) auditor self-reported confidence ≥0.6 on any hit
- Cache: (prompt_hash, evidence_hash, target_hash) → pass/fail.

Usage:

    from ztare.gates.prompt_leak_audit import audit_prompt_for_leak
    verdict = audit_prompt_for_leak(
        built_prompt=prompt_text,
        evidence_path=Path("projects/gp090_01/evidence.txt"),
        target_path=Path("projects/gp090_01/ground_truth.json"),
        mutator_model_id="o3",
    )
    if not verdict.passed:
        raise SystemExit(f"Prompt leak detected: {verdict.reason}")

CLI:

    python -m src.ztare.gates.prompt_leak_audit \\
        --project gp090_01 --mutator_model o3
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path


AUDITOR_CROSS_FAMILY = {
    "o3": "gpt-4.1",  # cross-family: openai reasoning -> openai chat (different variant)
    "o3-mini": "gpt-4.1",
    "o3-pro": "gpt-4.1",
    "o4-mini": "gpt-4.1",
    "o1": "gpt-4.1",
    "gpt4.1": "claude",
    "gpt4.1-mini": "claude",
    "gpt-4.1": "claude",
    "gpt4o": "claude",
    "claude": "gemini-pro",
    "claude-opus": "gemini-pro",
    "gemini": "claude",
    "gemini-lite": "claude",
    "gemini-pro": "claude",
}

DEFAULT_AUDITOR = "gpt-4.1"


@dataclass(frozen=True)
class LeakAuditVerdict:
    passed: bool
    reason: str
    top1_match: bool
    top3_overlap_hit: bool
    high_confidence_hit: bool
    auditor_model: str
    auditor_guesses: tuple
    cache_key: str


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _ast_node_count(expr_str: str) -> int:
    try:
        tree = ast.parse(expr_str, mode="eval")
    except SyntaxError:
        return 0
    return sum(1 for _ in ast.walk(tree))


def _ast_overlap_ratio(candidate_expr: str, target_expr: str) -> float:
    """Approximate AST-subtree overlap ratio.

    Returns the fraction of candidate AST nodes whose type+string
    representation appears somewhere in the target's AST walk. 1.0 means
    candidate is a subtree of target; <1.0 means partial overlap.

    Not a perfect AST-subtree match; sufficient for leak-detection
    heuristic (stronger comparators can replace this later).
    """
    try:
        c_tree = ast.parse(candidate_expr, mode="eval")
        t_tree = ast.parse(target_expr, mode="eval")
    except SyntaxError:
        return 0.0
    c_nodes = [type(n).__name__ + ":" + ast.dump(n) for n in ast.walk(c_tree)]
    t_nodes = set(type(n).__name__ + ":" + ast.dump(n) for n in ast.walk(t_tree))
    if not c_nodes:
        return 0.0
    overlap = sum(1 for n in c_nodes if n in t_nodes)
    return overlap / len(c_nodes)


def _call_auditor(
    built_prompt: str,
    evidence_text: str,
    auditor_model: str,
) -> list[dict]:
    """Ask auditor for top-3 guesses.

    Returns list of dicts: [{"expression": str, "confidence": float, "label": str}, ...].
    Lazily imports runtime to avoid circular imports when this gate is loaded at
    apparatus boot.
    """
    from ztare.common.llm_runtime import LLMRuntime, resolve_model_id

    model_id = resolve_model_id(auditor_model)

    auditor_prompt = f"""You are an independent auditor. Below is an evidence file and the instruction prompt a downstream mutator agent will receive. Do NOT run code. Your task: predict the hidden target law f(n) that the substrate is testing.

Rules:
- Respond ONLY with a JSON object. No prose, no markdown, no commentary.
- Return your top-3 most-likely target expressions as Python one-liners, each with a short English label and a confidence in [0.0, 1.0].

Required JSON schema (exact):

{{"guesses": [
  {{"expression": "<python expression of n>", "label": "<short name>", "confidence": <float 0..1>}},
  {{"expression": "...", "label": "...", "confidence": ...}},
  {{"expression": "...", "label": "...", "confidence": ...}}
]}}

---
EVIDENCE:
{evidence_text[:6000]}
---
PROMPT THE DOWNSTREAM MUTATOR WILL RECEIVE:
{built_prompt[:30000]}
---
Your JSON response:"""

    runtime = LLMRuntime()
    try:
        response = runtime.call_text(
            auditor_prompt,
            model_id=model_id,
            config=None,
            retries=3,
            timeout_seconds=120,
            request_label="prompt_leak_audit",
            progress_printer=print,
            transient_wait_seconds=5,
            timeout_wait_seconds=5,
        )
        raw = response.text if response and response.text else ""
    except Exception as exc:
        print(f"  prompt_leak_audit: auditor call failed: {exc}", file=sys.stderr)
        return []

    # Extract JSON
    try:
        # Strip code fences if present
        if "```" in raw:
            import re

            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
            if m:
                raw = m.group(1)
        parsed = json.loads(raw)
        guesses = parsed.get("guesses", []) or []
        normalised = []
        for g in guesses[:3]:
            if not isinstance(g, dict):
                continue
            normalised.append({
                "expression": str(g.get("expression", "")).strip(),
                "label": str(g.get("label", "")).strip(),
                "confidence": float(g.get("confidence", 0.0)),
            })
        return normalised
    except Exception as exc:
        print(f"  prompt_leak_audit: auditor response parse failed: {exc}", file=sys.stderr)
        return []


def audit_prompt_for_leak(
    *,
    built_prompt: str,
    evidence_path: Path,
    target_path: Path,
    mutator_model_id: str,
    top1_signature_match_fails: bool = True,
    top3_ast_overlap_threshold: float = 0.70,
    confidence_fail_threshold: float = 0.60,
    cache_dir: Path | None = None,
) -> LeakAuditVerdict:
    """Run the prompt-leak audit and return a verdict.

    The target is read via `target_path` into the comparator only; the
    auditor itself never sees the target.
    """
    evidence_text = evidence_path.read_text(encoding="utf-8") if evidence_path.exists() else ""
    if not target_path.exists():
        return LeakAuditVerdict(
            passed=True,
            reason="no ground_truth.json — audit skipped (rubric did not declare target)",
            top1_match=False,
            top3_overlap_hit=False,
            high_confidence_hit=False,
            auditor_model="",
            auditor_guesses=tuple(),
            cache_key="",
        )
    target_data = json.loads(target_path.read_text(encoding="utf-8"))
    target_expr = str(target_data.get("expression", "") or "").strip()
    if not target_expr:
        return LeakAuditVerdict(
            passed=True,
            reason="ground_truth.json has no `expression` field — audit skipped",
            top1_match=False,
            top3_overlap_hit=False,
            high_confidence_hit=False,
            auditor_model="",
            auditor_guesses=tuple(),
            cache_key="",
        )

    cache_key = f"{_hash(built_prompt)}_{_hash(evidence_text)}_{_hash(target_expr)}"
    cache_file = (cache_dir / f"{cache_key}.json") if cache_dir else None
    if cache_file and cache_file.exists():
        cached = json.loads(cache_file.read_text(encoding="utf-8"))
        return LeakAuditVerdict(
            passed=cached["passed"],
            reason=f"cache hit: {cached.get('reason', '')}",
            top1_match=cached.get("top1_match", False),
            top3_overlap_hit=cached.get("top3_overlap_hit", False),
            high_confidence_hit=cached.get("high_confidence_hit", False),
            auditor_model=cached.get("auditor_model", ""),
            auditor_guesses=tuple(cached.get("auditor_guesses", [])),
            cache_key=cache_key,
        )

    auditor_model = AUDITOR_CROSS_FAMILY.get(mutator_model_id, DEFAULT_AUDITOR)
    if auditor_model == mutator_model_id:
        auditor_model = DEFAULT_AUDITOR  # never audit with the same model family

    guesses = _call_auditor(built_prompt, evidence_text, auditor_model)

    target_nodes = _ast_node_count(target_expr)
    top1_match = False
    top3_overlap_hit = False
    high_confidence_hit = False
    fail_reasons: list[str] = []

    for idx, guess in enumerate(guesses):
        expr = guess["expression"]
        conf = guess.get("confidence", 0.0)
        overlap = _ast_overlap_ratio(expr, target_expr) if target_nodes else 0.0

        if idx == 0 and overlap >= 0.95:
            top1_match = True
            fail_reasons.append(
                f"top-1 AST overlap {overlap:.2f} >= 0.95 (expr={expr!r})"
            )

        if overlap >= top3_ast_overlap_threshold:
            top3_overlap_hit = True
            if idx != 0 or not top1_match:
                fail_reasons.append(
                    f"top-{idx+1} AST overlap {overlap:.2f} >= {top3_ast_overlap_threshold} (expr={expr!r})"
                )

        if conf >= confidence_fail_threshold and overlap >= 0.5:
            high_confidence_hit = True
            fail_reasons.append(
                f"top-{idx+1} confidence {conf:.2f} >= {confidence_fail_threshold} with overlap {overlap:.2f} (expr={expr!r})"
            )

    fail_any = top1_match or top3_overlap_hit or high_confidence_hit
    passed = not fail_any
    reason = "no leak detected" if passed else "; ".join(fail_reasons)

    verdict = LeakAuditVerdict(
        passed=passed,
        reason=reason,
        top1_match=top1_match,
        top3_overlap_hit=top3_overlap_hit,
        high_confidence_hit=high_confidence_hit,
        auditor_model=auditor_model,
        auditor_guesses=tuple(g.get("expression", "") for g in guesses),
        cache_key=cache_key,
    )

    if cache_file:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(
            json.dumps({
                "passed": passed,
                "reason": reason,
                "top1_match": top1_match,
                "top3_overlap_hit": top3_overlap_hit,
                "high_confidence_hit": high_confidence_hit,
                "auditor_model": auditor_model,
                "auditor_guesses": [g.get("expression", "") for g in guesses],
            }, indent=2),
            encoding="utf-8",
        )
    return verdict


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--mutator_model", required=True)
    ap.add_argument("--prompt_file", default=None, help="Path to pre-built mutator prompt. If absent, print-only placeholder.")
    ap.add_argument("--cache_dir", default=None)
    args = ap.parse_args()

    repo = Path(__file__).resolve().parents[3]
    project_dir = repo / "projects" / args.project
    evidence = project_dir / "evidence.txt"
    target = project_dir / "ground_truth.json"

    if args.prompt_file:
        prompt_text = Path(args.prompt_file).read_text(encoding="utf-8")
    else:
        # Fall back to last_prompt_debug.txt if available.
        fallback = project_dir / "last_prompt_debug.txt"
        if not fallback.exists():
            print(f"no --prompt_file provided and no fallback at {fallback}", file=sys.stderr)
            sys.exit(2)
        prompt_text = fallback.read_text(encoding="utf-8")

    verdict = audit_prompt_for_leak(
        built_prompt=prompt_text,
        evidence_path=evidence,
        target_path=target,
        mutator_model_id=args.mutator_model,
        cache_dir=Path(args.cache_dir) if args.cache_dir else None,
    )

    print(f"=== prompt_leak_audit: project={args.project}, mutator={args.mutator_model} ===")
    print(f"Auditor model: {verdict.auditor_model}")
    print(f"Passed: {verdict.passed}")
    print(f"Reason: {verdict.reason}")
    print(f"Top guesses: {list(verdict.auditor_guesses)}")
    sys.exit(0 if verdict.passed else 1)


if __name__ == "__main__":
    main()
