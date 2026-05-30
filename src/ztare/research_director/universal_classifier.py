"""GP-216 universal classifier: keyword-heuristic classifier for v5.

Replaces two_cultures.classify_arc with a 6-shared-core + 8-broadly +
4-specific classifier. Heuristic-only; for production-grade per-text op
assignment, use an LLM mapping pass against
universal_research_ops.VOCABULARY_V5.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class V5Classification:
    """Classification of an arc / stall / seam against vocabulary v5."""

    dominant_op: Optional[str]
    op_signals: Dict[str, int]
    tier_distribution: Dict[str, int]
    confidence: str
    rationale: str


# Backward-compatible name for older imports.
V4Classification = V5Classification


# Keyword bags per universal op. This is a rough Director-routing surface, not a
# substitute for the paper-5b cross-walk methodology.
OP_KEYWORDS = {
    # Shared core
    "core_01": [  # Problem Reformulation & Reduction
        "reformulat", "reduce to", "reduction", "surrogate", "sufficient condition",
        "equivalent problem", "logically connected", "hardness transfer", "tractable",
    ],
    "core_02": [  # Generalization & Abstraction
        "generaliz", "abstraction", "broaden", "relax constraint", "unify cases",
        "framework", "scheme", "topos", "categorif", "object class", "axiomatiz",
    ],
    "core_03": [  # Decomposition & Recomposition
        "decompose", "decomposition", "partition", "split into",
        "structured + pseudorandom", "regularity", "tree-decomposit",
        "split branch", "branch coverage", "case decomposition", "reassemble",
    ],
    "core_04": [  # Local-to-Global Assembly
        "local to global", "patch together", "gluing", "sheaf",
        "stalk", "covering", "local data", "globaliz", "sheaf-theoret",
        "local proof", "Mayer-Vietoris", "assemble",
    ],
    "core_05": [  # Canonical Form & Invariance
        "canonical", "normal form", "invariant", "equivalence class",
        "unique representative", "quotient", "coordinate-free", "gauge",
        "stable property", "remove redundancy",
    ],
    "core_06": [  # Cross-Domain Translation
        "translate", "translation", "transfer", "correspondence", "equivalent form",
        "via modul", "embedding into", "transport", "isomorph",
        "ergodic correspondence", "functor", "bridge domains",
    ],
    # Broadly shared
    "broad_01": [  # Iterative Refinement
        "iterate", "iteration", "increment", "monotone", "potential function",
        "tower of twos", "energy increment", "density increment", "refine",
        "fixed point", "converge", "bound chain", "estimate chain",
    ],
    "broad_02": [  # Recursive Decomposition
        "recursion", "recursive", "base case", "induction on", "self-similar",
        "structural rank", "complexity measure", "divide and conquer",
    ],
    "broad_03": [  # Duality & Adversarial Framing
        "duality", "dual", "primal-dual", "dual problem", "min-max",
        "minimax", "LP duality", "game", "adversarial",
    ],
    "broad_04": [  # Layered Approximation & Convergence
        "approximation", "convergence", "limit of", "sequence of", "successive",
        "layered", "staged", "asymptotic",
    ],
    "broad_05": [  # Extremal Method
        "extremal", "minimal counterexample", "maximal", "worst case",
        "tight bound", "tight example", "extremal configuration",
        "minimal", "maximal element", "special case", "decisive case",
    ],
    "broad_06": [  # Probabilistic & Stochastic Methods
        "probabilistic method", "random construction", "exists with positive probability",
        "expectation argument", "first moment", "second moment", "stochastic",
    ],
    "broad_07": [  # Dimensional & Structural Lifting
        "lift to higher dimension", "dimensional shift", "Z^d", "lift problem",
        "higher-dimensional", "structural lifting",
    ],
    "broad_08": [  # Constraint Imposition & Propagation
        "force the form", "covarianc", "conserv", "field equation",
        "axiom", "constraint", "must satisfy", "structural constraint",
    ],
    # Peripheral / subfield-specific
    "spec_01": ["excluded minor", "forbidden subgraph", "minor-closed", "obstruction", "forbidden structure"],
    "spec_02": ["diagonal", "self-referen", "fixed point", "godel", "gödel", "kleene", "halt",
                "internaliz", "system itself"],
    "spec_03": ["foundational repair", "ground rules", "axiom", "paradox", "consistency",
                "monster-bar", "lemma incorpor", "exception bar"],
    "spec_04": ["forcing", "independent proposition", "universe extension", "Cohen", "Solovay",
                "controlled extension"],
}


OP_TIER = {
    "core_01": "shared_core", "core_02": "shared_core", "core_03": "shared_core",
    "core_04": "shared_core", "core_05": "shared_core", "core_06": "shared_core",
    "broad_01": "broadly_shared", "broad_02": "broadly_shared", "broad_03": "broadly_shared",
    "broad_04": "broadly_shared", "broad_05": "broadly_shared", "broad_06": "broadly_shared",
    "broad_07": "broadly_shared", "broad_08": "broadly_shared",
    "spec_01": "subfield_specific", "spec_02": "subfield_specific",
    "spec_03": "subfield_specific", "spec_04": "subfield_specific",
}


def classify_text(text: str, *, min_signal: int = 2) -> V5Classification:
    """Classify text via keyword-heuristic per universal op."""
    txt = text.lower()
    op_signals: Counter[str] = Counter()
    for op_id, keywords in OP_KEYWORDS.items():
        for kw in keywords:
            count = len(re.findall(re.escape(kw.lower()), txt))
            if count > 0:
                op_signals[op_id] += count
    if not op_signals or sum(op_signals.values()) < min_signal:
        return V5Classification(
            dominant_op=None,
            op_signals=dict(op_signals),
            tier_distribution={},
            confidence="low",
            rationale=f"insufficient signal: total {sum(op_signals.values())} < {min_signal}",
        )

    dominant_op = op_signals.most_common(1)[0][0]
    tier_dist: Counter[str] = Counter()
    for op_id, count in op_signals.items():
        tier_dist[OP_TIER.get(op_id, "?")] += count
    total = sum(op_signals.values())
    top_share = op_signals[dominant_op] / total if total else 0
    confidence = "high" if total >= 8 and top_share >= 0.40 else ("medium" if total >= 4 else "low")
    return V5Classification(
        dominant_op=dominant_op,
        op_signals=dict(op_signals),
        tier_distribution=dict(tier_dist),
        confidence=confidence,
        rationale=f"total={total} top={dominant_op}({op_signals[dominant_op]}) share={top_share:.2f}",
    )


__all__ = ["classify_text", "V5Classification", "V4Classification", "OP_KEYWORDS", "OP_TIER"]


if __name__ == "__main__":
    cases = [
        ("Wiles proved FLT by reformulating the problem as a sufficient-condition reduction to modularity", "core_01"),
        ("Iterative refinement with potential function bounded by tower of twos", "broad_01"),
        ("Decompose graph into structured + pseudorandom partition via regularity lemma", "core_03"),
        ("Local stalks glued together via sheaf cohomology", "core_04"),
        ("Use invariance to choose a canonical representative of each equivalence class", "core_05"),
        ("Translate algebraic geometry into topology through a functorial correspondence", "core_06"),
        ("Generalize from sets to schemes; categorify the framework", "core_02"),
    ]
    for text, expected in cases:
        c = classify_text(text)
        ok = "PASS" if c.dominant_op == expected else "FAIL"
        print(f"  {ok} expected={expected} got={c.dominant_op} ({c.confidence})")
