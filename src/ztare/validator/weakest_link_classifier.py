"""GP-149 I-2 / I-3 runtime weakest-link classifier.

Lightweight regex-based classifier for weakest-point strings. Used at runtime
by autoresearch_loop.py for two opt-in behaviors:

  1. Class-aware stagnation threshold (I-2): suppress stagnation-triggered
     pivots until N distinct weakest-link classes have been observed.

  2. Pivot-ineffective-class skip (I-3): before firing topological pivots,
     classify the current weakest-point; if the class has empirically-
     negative pivot effect (tail_generalization, unverified_bound), skip
     the pivot OR log-observe depending on rubric mode.

Design commitments:
  - Standard-library-only. No external deps. Cheap per-call.
  - Covers the subset of classes with actionable runtime implications.
    Full 25+ class taxonomy lives in scripts/public/mine_weakest_link_taxonomy.py
    for mining purposes; this module is the runtime subset.
  - Patterns ordered by priority (most-specific first); first match wins.
  - Returns None when no class matches — caller treats as "unclassified,"
    which is safe (doesn't trigger class-specific actions).

Empirical source for the patterns: regex taxonomy from Stage 2 mining
(2026-04-24). See GP-149 seam §2 for frequency / lift data per class.
"""
from __future__ import annotations

import re
from typing import Optional


# Pivot-ineffective classes per GP-149 §2.2 — pivots have non-positive mean Δ
# on iterations weakest-linked to these classes. When skip_pivot_on_ineffective_classes
# mode is "suppress," autoresearch_loop should NOT fire topological pivot for
# these classes. When mode is "observe," still fire but log the class.
PIVOT_INEFFECTIVE_CLASSES: frozenset[str] = frozenset({
    "tail_generalization",      # 25 events, mean Δ -0.7, 20% regress
    "unverified_bound",          # 18 events, mean Δ +1.4, 28% regress — lukewarm
})

# Pivot-effective classes (for positive observability when logging)
PIVOT_EFFECTIVE_CLASSES: frozenset[str] = frozenset({
    "catastrophic_assumption",   # 51% climb, mean Δ +14.4
    "exhaustiveness_claim",      # 52% climb, mean Δ +10.4
})


# Ordered regex rules. First match wins per input string.
# Each tuple: (class_id, list_of_regex_patterns)
# Patterns are applied to lowercased input.
_RULES: list[tuple[str, list[str]]] = [
    # Tier 0: runtime-meaningful fast-kill classes (structural blockers)
    (
        "harness_defect",
        [
            r"harness\s+defect",
            r"fail_runtime",
            r"filenotfounderror",
            r"modulenotfounderror",
            r"importerror",
            r"syntaxerror",
            r"nameerror",
            r"test_model\.py.*(?:crash|fail|error)",
            r"traceback\s*\(most\s+recent",
        ],
    ),
    (
        "circularity",
        [
            r"self.?refer(?:ence|ential)",
            r"tautolog",
            r"circular\s+(?:reasoning|definition|argument)",
            r"begs?\s+the\s+question",
            r"prior\s+encodes\s+what\s+is\s+being\s+proven",
            r"hard\s+self.?reference",
        ],
    ),
    (
        "unfalsifiable_claim",
        [
            r"unfalsifiable",
            r"no\s+operational\s+test",
            r"no\s+discriminator",
            r"no\s+falsifier",
            r"cannot\s+be\s+tested",
            r"no\s+observable\s+consequence",
        ],
    ),
    (
        "unfalsifiable_claim",
        [
            r"no\s+falsifiers?",
            r"placeholder\s+(?:stub|thesis)",
            r"no\s+concrete\s+(?:failure\s+modes|gates|inversions|falsifiers)",
        ],
    ),
    # Tier 1a': catastrophic_fit_failure — cross-LLM stable at 0.538 in the
    # 2026-05-04 audit (highest among all classes); the only class greenlit for
    # GP-214 I-5 Mode B auto-injection. MUST precede catastrophic_assumption since
    # fit-failure phrasing often co-occurs with "load-bearing assumption" pinging.
    (
        "catastrophic_fit_failure",
        [
            r"(?:fit_quality_visible|structural\s+fit)\s*[:.]?\s*(?:the\s+)?(?:model|candidate|law)",
            r"(?:fit_quality_visible|fit\s+quality)[^.]{0,40}(?:zero|no)\s+(?:observed|exact)\s+(?:matches|points)",
            r"matches?\s+zero\s+of\s+the\s+(?:supplied|provided)\s+(?:data\s+points|evidence)",
            r"reproduces?\s+(?:zero|none)\s+of\s+(?:the\s+)?evidence",
            r"f\(\s*[a-z]\s*\)\s*=\s*0\s+for\s+all",
            r"output\s+is\s+universally\s+incorrect",
            r"fails?\s+to\s+reproduce\s+any\s+evidence",
            r"falsified\s+immediately\s+and\s+decisive",
            r"analytically\s+equivalent\s+to[^.]+matches?\s+zero",
        ],
    ),
    # Tier 1a: catastrophic (MUST precede unverified_bound / exhaustiveness since
    # these often co-occur with "unproven" or "without proof" phrasing)
    (
        "catastrophic_assumption",
        [
            r"catastrophic\s+(?:assumption|dependence|epistemic\s+error|false\s+assumption|under.?estimation)",
            r"fatal\s+(?:if|flaw|premise|assumption)",
            r"load.?bearing\s+(?:premise|assumption)\s+(?:not\s+justified|without)",
            r"entire\s+guarantee\s+(?:depends|hinges)",
            r"if\s+(?:this\s+)?assumption\s+fails",
            r"entire\s+completeness.?and.?runtime\s+guarantee\s+hinges",
            r"every\s+downstream\s+section",
        ],
    ),
    # Tier 1b: exhaustiveness (MUST precede unverified_bound since "without proof"
    # appears in both)
    (
        "exhaustiveness_claim",
        [
            r"exhaustiveness",
            r"exhaustive(?!ly)",
            r"completeness\s+(?:over.?)?claim",
            r"coverage\s+proof",
            r"assumes?\s+every",
            r"all\s+(?:possible|relevant)\s+(?:cases|modes|scenarios)",
            r"no\s+(?:coverage|completeness)\s+(?:proof|guarantee|argument)",
            r"(?:assumes?|asserts?)\s+exhaustiveness",
            r"exhaust\s+all",
        ],
    ),
    # Tier 1c: pivot-ineffective classes (data-critical for I-3)
    (
        "tail_generalization",
        [
            r"farther.?tail",
            r"tail\s+(?:generali|extrapol|predict|behavi|ratio|decay|scaling|region)",
            r"(?:poor|fail|weak|bad|no)\s+(?:farther.?)?tail\s+(?:generali|fit|predict|extrapol)",
            r"beyond\s+(?:the\s+)?(?:training|observed|visible|fitted)\s+(?:data|range|domain|region)",
            r"large.?(?:n|x|u|phi)\s+(?:behavi|scaling|asymptot|extrapol|limit)",
            r"(?:asymptot|scaling\s+law)\s+(?:assumption|claim|not\s+(?:valid|robust|support))",
            r"arbitrarily\s+large",
            r"indefinite\s+robustness.*(?:farther|tail|beyond)",
            r"extrapolat(?:es|ion)\s+(?:outside|beyond|off)",
        ],
    ),
    (
        "unverified_bound",
        [
            r"unproven",
            r"unverified",
            r"no\s+(?:explicit\s+)?derivation",
            r"non.?constructive",
            r"without\s+(?:explicit\s+)?(?:proof|derivation|justification|verification)",
            r"asserted?\s+without",
            r"claimed?\s+without\s+(?:proof|evidence|justification)",
            r"no\s+(?:formal\s+)?proof",
            r"lacks?\s+(?:formal\s+)?(?:proof|derivation|justification)",
            r"not\s+(?:formally\s+)?(?:derived|proven|justified|verified)",
            r"unjustified\s+(?:inference|claim|assumption|extrapolation)",
            r"empirically\s+observed\s+(?:bound|constant|threshold)",
            r"hinges?\s+on\s+(?:an?\s+)?unproved?",
        ],
    ),
    # Tier 3: LLM-discovered residual classes (for future routing)
    (
        "missing_counterfactual",
        [
            r"no\s+(?:rival|counterfactual|alternative)\s+(?:hypothesis|considered|explanation)",
            r"alternative\s+explanations?\s+not\s+addressed",
            r"rule\s+out\s+other\s+causes",
            r"did\s+not\s+canvass",
        ],
    ),
    (
        "missing_mechanism",
        [
            r"no\s+mechanism\s+(?:named|specified|given)",
            r"correlation\s+without\s+causation",
            r"phenomenological\s+(?:fit|description)",
            r"descriptive\s+but\s+not\s+mechanistic",
            r"cannot\s+explain\s+why",
            r"kepler.?class\s+fit",
        ],
    ),
    (
        "overclaimed_scope",
        [
            r"overclaim(?:ed|ing)?\s+scope",
            r"generalizes?\s+beyond\s+evidence",
            r"scope\s+overreach",
            r"applies\s+broadly\s+without",
            r"universal\s+claim\s+from\s+bounded",
        ],
    ),
]


# Compile once
_COMPILED: list[tuple[str, list[re.Pattern[str]]]] = [
    (cid, [re.compile(p, re.IGNORECASE) for p in patterns])
    for cid, patterns in _RULES
]


def classify_weakest_point(text: Optional[str]) -> Optional[str]:
    """Classify a weakest-point string into one of the known classes.

    Returns the class_id string if matched, None otherwise.
    First-match semantics: patterns are checked in priority order
    (structural blockers first, then pivot-ineffective, then effective,
    then residual).

    Safe to call on None or empty input — returns None.
    """
    if not text:
        return None
    lowered = text.lower()
    for cid, patterns in _COMPILED:
        for p in patterns:
            if p.search(lowered):
                return cid
    return None


def is_pivot_ineffective_class(cid: Optional[str]) -> bool:
    """Is this class in the empirically pivot-ineffective set?

    Based on GP-148 Stage 2 Ticket B mining: tail_generalization (mean Δ −0.7,
    20% regress) and unverified_bound (mean Δ +1.4, 28% regress).
    """
    return cid in PIVOT_INEFFECTIVE_CLASSES


def is_pivot_effective_class(cid: Optional[str]) -> bool:
    return cid in PIVOT_EFFECTIVE_CLASSES


# Smoke-test entries (imported by tests, runnable as __main__)
def _smoke_test_inputs() -> list[tuple[str, str]]:
    """(weakest-point-text, expected-class). Used by self-test."""
    return [
        ("The entire completeness-and-runtime guarantee hinges on the highly fragile assumption λ_min > 0.02",
         "catastrophic_assumption"),
        ("Trajectory-level RMS-error fit over a 50-unit window is unlikely to hold in a positive-Lyapunov regime, far-tail behavior diverges",
         "tail_generalization"),
        ("Catastrophic dependence on the empirically observed bound κ̂ ≤ 10¹² which is unproven for arbitrary PSLQ runs",
         "catastrophic_assumption"),
        ("The thesis is essentially a placeholder stub: no concrete failure modes, gates, inversions, or falsifiers are provided",
         "unfalsifiable_claim"),
        ("Assumes exhaustiveness of the four irreversible transformations without proof of completeness",
         "exhaustiveness_claim"),
        ("Structured semantic-gate derivation classified the proof as hard self-reference",
         "circularity"),
        ("FileNotFoundError: [Errno 2] No such file or directory: 'projects/other/evidence.txt'",
         "harness_defect"),
        ("No rival considered — the thesis does not canvass alternative explanations",
         "missing_counterfactual"),
        ("This is a very interesting mathematical observation that the constants interrelate in a meaningful way",
         None),  # no match
    ]


if __name__ == "__main__":
    # Self-test
    cases = _smoke_test_inputs()
    ok = 0
    for text, expected in cases:
        got = classify_weakest_point(text)
        match = "✓" if got == expected else "✗"
        ok += 1 if got == expected else 0
        print(f"  {match}  expected={expected!r:30}  got={got!r:30}  text: {text[:60]}...")
    print(f"\n{ok}/{len(cases)} cases passed")
