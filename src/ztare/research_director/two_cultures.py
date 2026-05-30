"""GP-216 / paper 5b — Two-Cultures classifier and cross-distribution registry.

Combines theory_building_ops + problem_solving_ops into a unified two-cultures
view of mathematical research moves. Provides:

  - 2x2 corpus-vocabulary cross-coverage table (empirical)
  - per-op tier assignment (TB-specific / PS-specific / shared-core)
  - classify_arc(text) — given an arc / stall / seam description, return the
    dominant culture and a confidence score

Empirical basis (paper 5b):
  - TB vocab on TB corpus: 58.1% h+m
  - TB vocab on PS corpus: 20.7% h+m
  - PS vocab on TB corpus: 19.1% h+m
  - PS vocab on PS corpus: 65.9% h+m
  - Average own-corpus advantage: 42.1 pp (symmetric)
  - 11 of 18 ops are culture-specific (zero opposite-corpus instances)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .theory_building_ops import VOCABULARY_V3 as TB_VOCAB
from .problem_solving_ops import VOCABULARY_PS_V1 as PS_VOCAB


# 2×2 cross-distribution table (empirical, paper 5b)
CROSS_DISTRIBUTION_2X2: Dict[str, Dict[str, float]] = {
    "tb_vocab": {
        "tb_corpus_pct": 58.1,
        "ps_corpus_pct": 20.7,
        "own_advantage_pp": 37.4,
    },
    "ps_vocab": {
        "tb_corpus_pct": 19.1,
        "ps_corpus_pct": 65.9,
        "own_advantage_pp": 46.8,
    },
}


# Per-op cross-distribution tier assignments (empirical, paper 5b §4.2)
OP_TIERS: Dict[str, str] = {
    # Theory-builder-specific (8 ops, zero PS instances)
    "tb_04": "TB-specific",
    "tb_08": "TB-specific",
    "tb_09": "TB-specific",
    "tb_11": "TB-specific",
    "tb_NEW_HOF": "TB-specific",
    "tb_NEW_POLYA": "TB-specific",
    "tb_LAK1": "TB-specific",
    "tb_LAK2": "TB-specific",
    # TB-mostly (1+ PS instance, but <2 PS arcs)
    "tb_01": "TB-mostly",
    "tb_02": "TB-mostly",
    # Shared-core (TB ops with ≥1 PS instance and ≥1 PS arc)
    "tb_03": "shared-core",
    "tb_06": "shared-core",
    # Problem-solver-specific (3 ops, zero TB instances)
    "ps_02": "PS-specific",
    "ps_05": "PS-specific",
    "ps_06": "PS-specific",
    # Shared-core (PS ops with non-zero TB instances)
    "ps_01": "shared-core",
    "ps_03": "shared-core",
    "ps_04": "shared-core",
}


# Strongest cross-cultural overlap pairs (paper 5b §4.2)
CROSS_CULTURAL_PAIRS: List[Tuple[str, str, str]] = [
    ("tb_02", "ps_03", "Cross-Domain Unification ↔ Formal Equivalence Transfer (strongest)"),
    ("tb_06", "ps_01", "Tacit Pattern Formalization ↔ Structural Partitioning (related)"),
    ("tb_03", "ps_04", "Surrogate Problem Substitution ↔ Black-Box Theorem Application (leverage moves)"),
    ("tb_NEW_POLYA", "ps_04", "Strategic Specialization ↔ Black-Box Theorem Application (special-case leverage)"),
]


# ─── Classification ───

@dataclass
class CultureClassification:
    """Result of classifying an arc/stall/seam by culture."""

    dominant: str  # "theory_building" | "problem_solving" | "mixed" | "unclassified"
    tb_signal: int  # count of theory-builder keyword matches
    ps_signal: int  # count of problem-solver keyword matches
    confidence: str  # "high" | "medium" | "low"
    matched_keywords: Dict[str, List[str]]
    rationale: str


# Keyword bags derived from the vocabulary mechanisms + arc descriptions.
# Heuristic-only; for production-grade classification, use an LLM that reads
# the full arc description against the vocabulary registry.
TB_KEYWORDS = {
    "object redefinition": ["scheme", "category", "topos", "manifold", "object class", "redefine", "ontolog"],
    "deformation": ["deformation", "moduli", "parametric family", "family of", "deformation ring"],
    "diagonal": ["diagonal", "self-referen", "fixed point", "godel", "gödel", "kleene", "halt"],
    "limitative": ["incomplete", "undecidable", "limitative", "impossib", "no_.*_with"],
    "framework": ["framework", "vocabulary lift", "categorif", "infinity-categor", "∞-categor"],
    "lakatos": ["monster-bar", "monster bar", "lemma incorpor", "exception bar", "concept reviion"],
    "constraint forcing": ["covarianc", "conserv", "field equation", "axiomatiz", "tensor"],
    "functorial": ["functor", "natural transform", "yoneda", "adjoint", "universal property"],
}
PS_KEYWORDS = {
    "iterative refinement": ["density increment", "energy increment", "potential function", "iterate", "refine", "tower"],
    "estimate chaining": ["bound", "chain of", "fourier", "estimate", "L^p", "sobolev", "inequality"],
    "structural partition": ["regularity", "structured", "pseudorandom", "partition", "decompose", "chaotic"],
    "transference": ["transfer", "correspondence", "translate", "ergodic", "majorant"],
    "induction on rank": ["induction on", "structural rank", "tower height", "complexity measure", "depth"],
    "black-box theorem": ["szemerédi", "szemeredi", "as black-box", "treat as module", "preconditions"],
    "combinatorial": ["combinator", "ramsey", "extremal", "probabilistic method", "double-count"],
    "polymath": ["polymath", "blog", "open collaborative"],
}


def classify_arc(text: str, *, min_signal: int = 2, ratio_threshold: float = 1.5) -> CultureClassification:
    """Classify an arc / stall / seam description as theory-building, problem-solving, mixed, or unclassified.

    Heuristic-only. For each culture's keyword bags, count match instances
    (case-insensitive). The dominant culture is the one with more total matches,
    provided the ratio exceeds threshold AND minimum signal threshold is met.

    Returns: CultureClassification with dominant, signals, confidence, matched keywords.

    Args:
        text: arc / stall / seam description (any length)
        min_signal: minimum total keyword matches to classify (else "unclassified")
        ratio_threshold: dominant_signal / minor_signal must exceed this to be "dominant" (else "mixed")
    """
    txt = text.lower()
    matched: Dict[str, List[str]] = {"theory_building": [], "problem_solving": []}
    tb_signal = 0
    ps_signal = 0

    for category, keywords in TB_KEYWORDS.items():
        for kw in keywords:
            count = len(re.findall(re.escape(kw.lower()), txt))
            if count > 0:
                matched["theory_building"].append(f"{category}:{kw}({count})")
                tb_signal += count

    for category, keywords in PS_KEYWORDS.items():
        for kw in keywords:
            count = len(re.findall(re.escape(kw.lower()), txt))
            if count > 0:
                matched["problem_solving"].append(f"{category}:{kw}({count})")
                ps_signal += count

    total = tb_signal + ps_signal
    if total < min_signal:
        return CultureClassification(
            dominant="unclassified",
            tb_signal=tb_signal,
            ps_signal=ps_signal,
            confidence="low",
            matched_keywords=matched,
            rationale=f"insufficient signal: total {total} < {min_signal}",
        )

    if tb_signal == 0:
        ratio = float("inf") if ps_signal > 0 else 1.0
    elif ps_signal == 0:
        ratio = float("inf")
    else:
        ratio = max(tb_signal, ps_signal) / min(tb_signal, ps_signal)

    if ratio < ratio_threshold:
        return CultureClassification(
            dominant="mixed",
            tb_signal=tb_signal,
            ps_signal=ps_signal,
            confidence="medium",
            matched_keywords=matched,
            rationale=f"signals comparable: TB={tb_signal} PS={ps_signal} ratio={ratio:.2f} < {ratio_threshold}",
        )

    if tb_signal > ps_signal:
        dominant = "theory_building"
    else:
        dominant = "problem_solving"
    confidence = "high" if total >= 6 and ratio >= 2.5 else "medium"
    return CultureClassification(
        dominant=dominant,
        tb_signal=tb_signal,
        ps_signal=ps_signal,
        confidence=confidence,
        matched_keywords=matched,
        rationale=f"TB={tb_signal} PS={ps_signal} ratio={ratio:.2f}",
    )


def render_two_cultures_summary() -> str:
    """Render the empirical two-cultures cross-distribution as a markdown summary."""
    lines = ["# Two Cultures of Mathematics, Operationalized — empirical summary", ""]
    lines.append("## 2×2 corpus-vocabulary cross-coverage")
    lines.append("")
    lines.append("|  | TB corpus | PS corpus |")
    lines.append("|---|---|---|")
    lines.append(f"| **TB vocab (12 ops)** | **{CROSS_DISTRIBUTION_2X2['tb_vocab']['tb_corpus_pct']}%** | {CROSS_DISTRIBUTION_2X2['tb_vocab']['ps_corpus_pct']}% |")
    lines.append(f"| **PS vocab (6 ops)** | {CROSS_DISTRIBUTION_2X2['ps_vocab']['tb_corpus_pct']}% | **{CROSS_DISTRIBUTION_2X2['ps_vocab']['ps_corpus_pct']}%** |")
    lines.append("")
    avg_gap = (CROSS_DISTRIBUTION_2X2['tb_vocab']['own_advantage_pp'] + CROSS_DISTRIBUTION_2X2['ps_vocab']['own_advantage_pp']) / 2
    lines.append(f"**Average own-corpus advantage: {avg_gap:.1f} percentage points** (symmetric in both directions)")
    lines.append("")
    lines.append("## Per-op tier assignment (paper 5b §4.2)")
    lines.append("")
    by_tier: Dict[str, List[str]] = {}
    for op_id, tier in OP_TIERS.items():
        by_tier.setdefault(tier, []).append(op_id)
    for tier in ("TB-specific", "TB-mostly", "shared-core", "PS-specific"):
        ops = by_tier.get(tier, [])
        lines.append(f"- **{tier}** ({len(ops)}): {', '.join(sorted(ops))}")
    lines.append("")
    lines.append("## Strongest cross-cultural pairs")
    for tb, ps, label in CROSS_CULTURAL_PAIRS:
        lines.append(f"- **{tb} ↔ {ps}** — {label}")
    return "\n".join(lines)


__all__ = [
    "CROSS_DISTRIBUTION_2X2",
    "OP_TIERS",
    "CROSS_CULTURAL_PAIRS",
    "CultureClassification",
    "classify_arc",
    "render_two_cultures_summary",
    "TB_VOCAB",
    "PS_VOCAB",
]


if __name__ == "__main__":
    print(render_two_cultures_summary())
    print()
    print("=== Self-test ===")
    test_cases = [
        ("Wiles proved Fermat's Last Theorem by establishing modularity of semistable elliptic curves via deformation theory of Galois representations and an R=T isomorphism.", "theory_building"),
        ("Roth proved any subset of {1..N} with density at least C/log log N contains a 3-term arithmetic progression by Fourier analysis and density increment iteration with bound on density.", "problem_solving"),
        ("Grothendieck replaced varieties with schemes constructed from prime spectra of commutative rings, glued along sheaves; introduced étale cohomology; demanded functorial constructions characterized by universal properties.", "theory_building"),
        ("Szemerédi proved every dense graph admits a partition into approximately equal parts where almost all pairs are pseudorandom; the proof uses iterative refinement and mean-square energy as a potential function bounded by tower-of-twos depth.", "problem_solving"),
    ]
    for text, expected in test_cases:
        c = classify_arc(text)
        ok = "✓" if c.dominant == expected else "✗"
        print(f"  {ok} expected={expected:18s} got={c.dominant:18s} (TB={c.tb_signal}, PS={c.ps_signal}, conf={c.confidence})")
