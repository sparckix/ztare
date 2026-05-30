#!/usr/bin/env python3
"""v31_gap_report_generator.py — Layer-5 gap reports on open Lean sorries.

Path C deliverable from session 2026-05-15. After GP-233 §7 architecture
killed and GP-235 dropped, the v31 substantive deliverable is a structured
gap report per sorry-miner candidate — designed to save a Mathlib PR
contributor's time vs `git grep sorry`.

For each candidate, the report contains:
  1. Goal signature + file location + line number
  2. Local hypothesis context (variables, instances, hypotheses in scope)
  3. Adjacent Mathlib lemmas (top-level type matches, but NOT paraphrases)
  4. Operation type guess from L2 structural catalog (advisory)
  5. Predicted L4 archetype + anti-pattern flags (advisory)
  6. Proof skeleton sketch (template, not actual proof)
  7. Reference pointers (paper/textbook citations from docstring)

No LLM calls. Deterministic extraction from Lean source + L2/L3/L4 catalogs.

Usage:
  v31_gap_report_generator.py --in /tmp/open_sorries_v31_candidates.json
                              --out analytics/.../v31_gap_reports.md
"""
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
from typing import Optional

ROOT = Path(__import__("os").environ.get("ZTARE_REPO_ROOT", ".")).resolve()
sys.path.insert(0, str(ROOT / "scripts/public/control"))

try:
    from archetype_classifier import classify  # type: ignore
    HAVE_CLASSIFIER = True
except Exception:
    HAVE_CLASSIFIER = False


def extract_hypothesis_context(file_path: str, line_number: int) -> dict:
    """Read the file and extract: variable declarations + open/import lines +
    the theorem's own parameter/hypothesis list.

    Returns {variables, imports, opens, parameters, hypotheses}.
    """
    p = Path(file_path)
    if not p.exists():
        return {"error": f"file not found: {file_path}"}

    lines = p.read_text().splitlines()

    imports = [l.strip() for l in lines if l.strip().startswith("import ")]
    opens = [l.strip() for l in lines if l.strip().startswith("open ")]
    variables = [l.strip() for l in lines if l.strip().startswith("variable ")]

    # Theorem-local parameters/hypotheses: look at lines containing the theorem signature
    # (lines around line_number that start with theorem/lemma/example).
    sig_start = None
    for i in range(max(0, line_number - 10), min(len(lines), line_number)):
        ln = lines[i].lstrip()
        if ln.startswith(("theorem ", "lemma ", "example ", "def ")):
            sig_start = i
            break
    parameters: list[str] = []
    hypotheses: list[str] = []
    if sig_start is not None:
        # Walk forward until we hit `:= by` or `:=`
        sig_block = []
        for j in range(sig_start, min(len(lines), sig_start + 30)):
            sig_block.append(lines[j])
            if ":= by" in lines[j] or lines[j].rstrip().endswith(":="):
                break
        sig_text = " ".join(sig_block)
        # Pull `(h : ...)` and `(name : type)` style parens
        paren_groups = re.findall(r"\(([^()]+?)\)", sig_text)
        for g in paren_groups:
            if " : " in g:
                # heuristic: if the LHS is `h` / `h1` / `h_lt` style, it's a hypothesis
                lhs = g.split(":", 1)[0].strip()
                if re.match(r"^h[\w_]*$", lhs) or re.match(r"^[a-z]+\d+$", lhs):
                    hypotheses.append(f"({g})")
                else:
                    parameters.append(f"({g})")
            else:
                parameters.append(f"({g})")

    return {
        "imports": imports[:5],
        "opens": opens[:5],
        "variables": variables[:5],
        "parameters": parameters,
        "hypotheses": hypotheses,
    }


def predict_l2_op(goal_text: str) -> str:
    """Heuristic L2 operation-type prediction (no LLM). Same logic as
    route_c_archetype_runner's predict_l2_op."""
    g = goal_text.lower()
    if "‖" in goal_text or "norm" in g or "triangle" in g:
        return "core_03_decomposition"
    if "continuous" in g or "deriv" in g or "fderiv" in g:
        return "PDE_op_11_external_theorem_typed_import"
    if "lintegral" in g or "∫" in goal_text or "Lp" in goal_text or "eLpNorm" in goal_text:
        return "broad_01_estimate_chain (Lp / Hölder-style)"
    if re.search(r"\bnat\b|ℕ|\binduction\b", g):
        return "core_02_generalization_abstraction"
    if "summable" in g or "tsum" in g:
        return "broad_01_estimate_chain (summability)"
    if re.search(r"≤|<|≥|>|inequal", goal_text):
        return "PDE_op_05_sharpness_failure_witness"
    return "core_03_decomposition"


def predict_proof_skeleton(archetype: str, op_type: str) -> list[str]:
    """Return a tactic-template skeleton, not an actual proof."""
    if "ARCH-007" in archetype or "holder" in op_type.lower() or "Lp" in op_type:
        return [
            "-- Hölder / duality skeleton",
            "have h_holder : ∫ ... ≤ (∫ ...)^(1/p) * (∫ ...)^(1/q) := by",
            "  apply MeasureTheory.lintegral_mul_le_Lp_mul_Lq <conjugate-witness>",
            "calc ... ≤ ... := h_holder",
            "  _ ≤ ... := by gcongr; <bound-each-factor>",
        ]
    if "ARCH-005" in archetype:
        return [
            "induction n with",
            "  | zero => <base case>",
            "  | succ k ih => <inductive step using ih>",
        ]
    if "ARCH-004" in archetype:
        return [
            "refine ⟨?_, ?_⟩",
            "· <first conjunct>",
            "· <second conjunct>",
        ]
    if "ARCH-002" in archetype or "estimate_chain" in op_type:
        return [
            "calc <goal LHS>",
            "  _ ≤ <intermediate-1> := by <step-1>",
            "  _ ≤ <intermediate-2> := by <step-2>",
            "  _ ≤ <goal RHS> := by <step-final>",
        ]
    if "ARCH-008" in archetype:
        return [
            "measurability",
            "-- OR:",
            "fun_prop",
        ]
    return [
        "-- Direct application skeleton",
        "exact <named-lemma> <args>",
        "-- OR:",
        "apply <named-lemma>",
        "<discharge side conditions>",
    ]


def extract_docstring_refs(file_path: str, line_number: int) -> list[str]:
    """Look 30 lines back from the theorem for `/-- ... -/` docstring;
    extract anything that looks like a paper/textbook citation."""
    p = Path(file_path)
    if not p.exists():
        return []
    lines = p.read_text().splitlines()
    doc_text = ""
    for i in range(max(0, line_number - 30), line_number):
        ln = lines[i]
        if "-/" in ln or "/-" in ln or doc_text:
            doc_text += ln + "\n"
            if "-/" in ln:
                break
    if not doc_text:
        return []
    refs: list[str] = []
    # Author-year patterns
    for m in re.finditer(r"\b([A-Z][a-z]+(?:[-,]\s*[A-Z][a-z]+)*)\s*\(?(\d{4})\)?", doc_text):
        refs.append(f"{m.group(1)} ({m.group(2)})")
    # Paper / book named references
    for m in re.finditer(r"(?:Lemma|Theorem|Proposition|Corollary)\s+[\d.]+(?:\s+of\s+([A-Z][\w\s]+))?", doc_text):
        if m.group(1):
            refs.append(f"{m.group(0)}")
    # arXiv refs
    for m in re.finditer(r"arXiv[:\s]*(\d{4}\.\d{4,5})", doc_text):
        refs.append(f"arXiv:{m.group(1)}")
    # Mathlib lemma cross-refs in docstring
    for m in re.finditer(r"`([A-Z][\w'.]+(?:\.[A-Z][\w'.]+)*)`", doc_text):
        refs.append(f"see: `{m.group(1)}`")
    # de-dup
    return sorted(set(refs))[:8]


def find_adjacent_mathlib_lemmas(goal_signature: str) -> list[str]:
    """Heuristic: name a few Mathlib lemmas in adjacent namespaces that the
    goal's keywords suggest are RELATED but NOT paraphrases. No grep against
    full Mathlib (would be expensive); use a hand-curated heuristic for the
    common adjacent-namespace cases.

    These are intentionally listed as 'building blocks the contributor may
    want to apply or generalize', NOT as paraphrases of the goal.
    """
    g = goal_signature
    adjacent: list[str] = []
    if "lintegral" in g or "eLpNorm" in g:
        adjacent.extend([
            "MeasureTheory.lintegral_mul_le_Lp_mul_Lq (Hölder for lintegral, finite-norm case)",
            "MeasureTheory.eLpNorm_add_le (Minkowski sum form)",
            "MeasureTheory.Lp.snorm_add_le (older API)",
            "Tonelli's theorem: MeasureTheory.lintegral_lintegral_swap",
        ])
    if "convolution" in g.lower():
        adjacent.extend([
            "MeasureTheory.MemLp.convolution (existence + Lp bound)",
            "MeasureTheory.convolution_assoc",
        ])
    if "rearrangement" in g.lower() or "decreasing" in g.lower():
        adjacent.extend([
            "MeasureTheory.Measure.measure_lt_eq_measure_lt_of_finite (level-set equivalence)",
            "Tice's notes Lemmas 1.1.22-23 (standard rearrangement layer-cake)",
        ])
    if "antitone" in g.lower() or "monotone" in g.lower():
        adjacent.extend([
            "Antitone.smul_le_smul (basic monotonicity)",
            "Real.rpow_le_rpow (exponent monotonicity)",
            "MeasureTheory.lintegral_mono (integral monotonicity)",
        ])
    if "summable" in g.lower() or "tsum" in g.lower():
        adjacent.extend([
            "Summable.add",
            "Summable.tsum_le_tsum (compare tsums by pointwise bound)",
            "ENNReal.tsum_mul_le_Lp_mul_Lq (Hölder for tsum form)",
        ])
    if not adjacent:
        # Generic fallback
        adjacent = [
            "(No namespace-specific adjacent lemmas identified by heuristic; suggest grep in goal's namespace + nearest siblings)",
        ]
    return adjacent[:6]


def make_report_entry(candidate: dict) -> str:
    """Build a markdown gap-report section for one candidate."""
    rank = candidate.get("rank", "?")
    name = candidate.get("theorem_name", "?")
    file_path = candidate.get("file_path", "?")
    line = candidate.get("line_number", 0)
    sig = candidate.get("theorem_signature", "")
    desc = candidate.get("description", "")
    score = candidate.get("score", 0)
    archetype_hint = candidate.get("archetype", "?")

    # Run classifier
    classifier_out = {}
    if HAVE_CLASSIFIER and sig:
        try:
            classifier_out = classify(sig)
        except Exception as e:
            classifier_out = {"error": str(e)}

    pred_arch = classifier_out.get("predicted_L4_archetype", "ARCH-001_direct_library_chain (default)")
    pred_flags = classifier_out.get("predicted_L3_anti_pattern_flags", [])
    op_type = predict_l2_op(sig)
    skeleton = predict_proof_skeleton(pred_arch, op_type)
    adjacent = find_adjacent_mathlib_lemmas(sig)
    refs = extract_docstring_refs(file_path, line) if Path(file_path).exists() else []
    ctx = extract_hypothesis_context(file_path, line) if Path(file_path).exists() else {}

    out = []
    out.append(f"## Gap Report E{rank}: `{name}`")
    out.append("")
    out.append(f"**File:** `{file_path}:{line}`")
    out.append(f"**Sorry-miner score:** {score}")
    out.append(f"**Source-rated archetype:** {archetype_hint}")
    out.append(f"**Description:** {desc}")
    out.append("")
    out.append("### Theorem signature")
    out.append("```lean")
    out.append(sig.strip())
    out.append("```")
    out.append("")
    out.append("### Local context")
    if ctx.get("variables"):
        out.append("**Variables in scope:**")
        for v in ctx["variables"]:
            out.append(f"- `{v}`")
    if ctx.get("parameters"):
        out.append("**Theorem parameters:**")
        for p in ctx["parameters"][:8]:
            out.append(f"- `{p}`")
    if ctx.get("hypotheses"):
        out.append("**Hypotheses:**")
        for h in ctx["hypotheses"][:8]:
            out.append(f"- `{h}`")
    if not any(ctx.get(k) for k in ["variables", "parameters", "hypotheses"]):
        out.append("(no local context extracted)")
    out.append("")
    out.append("### Classifier predictions (advisory — 25% top-1 accuracy; treat as a starting hypothesis)")
    out.append(f"- **L4 archetype:** `{pred_arch}` (confidence {classifier_out.get('confidence', '?')})")
    out.append(f"- **L2 operation type:** `{op_type}`")
    if pred_flags:
        out.append("- **L3 anti-pattern flags to watch for:**")
        for f in pred_flags[:6]:
            out.append(f"  - `{f}`")
    out.append("")
    out.append("### Adjacent Mathlib lemmas (NOT paraphrases — building blocks)")
    for a in adjacent:
        out.append(f"- {a}")
    out.append("")
    out.append("### Proof skeleton (template, not actual proof)")
    out.append("```lean")
    for s in skeleton:
        out.append(s)
    out.append("```")
    out.append("")
    if refs:
        out.append("### References from docstring")
        for r in refs:
            out.append(f"- {r}")
        out.append("")
    out.append("### Honest caveats")
    out.append("- L4 archetype prediction is heuristic (25% top-1 accuracy on v3 ground truth).")
    out.append("- Adjacent-lemma list is hand-curated heuristic, not Mathlib-grep verified.")
    out.append("- Proof skeleton is a template — actual proof will diverge based on local structure.")
    out.append("- This report is a starting point for human-LLM collaboration, not an autonomous closure.")
    out.append("")
    out.append("---")
    out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    candidates = json.load(open(args.in_path))
    if isinstance(candidates, dict):
        candidates = candidates.get("candidates", candidates.get("rows", []))

    header = [
        "# v31 Gap Reports (Path C deliverable)",
        "",
        "**Generated:** 2026-05-15",
        "**Source:** `/tmp/open_sorries_v31_candidates.json` (10 sorry-miner candidates, ranked 0.65-0.95)",
        "**Purpose:** structured gap intelligence for Mathlib-PR-contribution work on open `sorry`s.",
        "",
        "## Why this exists",
        "",
        "GP-233 §7 (5-layer Route C architecture) was killed by external Meta-Darwin + 10-row ablation data (Mode D = Mode A, zero distinct signal). GP-235 (now: **Proof-Route Fingerprint Primitive Validation**) is ACTIVE in revised v1 form with narrowed scope (proof-route deduplication only, NOT theorem-novelty certification) + train/test split + cheap-baseline ablation dominance test. These gap reports are an INDEPENDENT v31 deliverable — designed to save a Mathlib PR contributor's time vs `git grep sorry`. They do not depend on GP-235 validating.",
        "",
        "## What each report contains",
        "",
        "Per candidate: file location, theorem signature, local hypothesis context, advisory L4 archetype + L2 op + L3 flag predictions (with 25% top-1 caveat), adjacent Mathlib lemmas (building blocks, NOT paraphrases), proof skeleton template, docstring references.",
        "",
        "## What this is NOT",
        "",
        "- Not an autonomous proof.",
        "- Not a paraphrase of an existing Mathlib lemma.",
        "- Not a closure verdict — the contributor decides whether the gap is genuinely open.",
        "- Not Meta-Darwin-audited (this report itself is unvalidated content — apply your own discipline).",
        "",
        "---",
        "",
    ]

    reports = [make_report_entry(c) for c in candidates]
    full = "\n".join(header + reports)
    Path(args.out).write_text(full)
    print(f"wrote {args.out} ({len(candidates)} reports, {len(full)} chars)")


if __name__ == "__main__":
    sys.exit(main() or 0)
