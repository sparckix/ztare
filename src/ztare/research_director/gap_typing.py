"""Reusable gap-typing primitives for hard mathematical proof work.

This module owns the pure taxonomy and local classifier. CLI tools may add
LLM calls, Mathlib shelf retrieval, or prompt rendering on top, but callers
should not need to import from `scripts/public/lean` just to classify a gap.
"""
from __future__ import annotations

from typing import Any


GAP_TYPES: dict[str, dict[str, Any]] = {
    "SOBOLEV": {
        "description": "control by higher-derivative norm; bounds of form ||f||_{L^q} <= C ||f||_{W^{k,p}}",
        "shape_tags": ["SOBOLEV", "LE"],
        "rank_hints": ["Sobolev", "embedding", "ContDiff", "WithDeriv"],
        "key_lemmas_hint": "sobolev embedding, gagliardo-nirenberg, ContDiff bounds",
    },
    "INTERPOLATION": {
        "description": "bounds between two function-space norms via interpolation",
        "shape_tags": ["INTERPOLATION", "LE"],
        "key_lemmas_hint": "Riesz-Thorin, Marcinkiewicz, interpolation_inequality",
    },
    "COERCIVITY": {
        "description": "lower bound on quadratic / bilinear form (Garding-type)",
        "shape_tags": ["COERCIVITY", "LE"],
        "key_lemmas_hint": "Garding inequality, positivity, ellipticity",
    },
    "COMMUTATOR": {
        "description": "[A, B] error-term bound; Calderon-Zygmund-style",
        "shape_tags": ["NORM_LE"],
        "key_lemmas_hint": "Calderon-Zygmund, commutator_estimate",
    },
    "PROPAGATION": {
        "description": "property preserved under time evolution",
        "shape_tags": ["PROPAGATION", "LE"],
        "key_lemmas_hint": "finite_speed_of_propagation, energy_estimate",
    },
    "LIMIT_PASSAGE": {
        "description": "property transferred from finite stages to limit object",
        "shape_tags": ["LIMINF", "LE"],
        "shape_tag_groups": [
            ["LIMINF", "LE"],
            ["LOWER_SEMICONTINUOUS"],
            ["CAUCHY", "TENDSTO"],
            ["TENDSTO", "INTEGRAL"],
        ],
        "rank_hints": [
            "LowerSemicontinuous", "lowerSemicontinuous", "liminf",
            "eLpNorm", "Lp", "CauchySeq", "tendsto", "Tendsto",
            "integral", "lintegral",
        ],
        "key_lemmas_hint": "liminf bounds, lower semicontinuity, Cauchy/tendsto, dominated convergence, weak limit",
    },
    "HOLDER": {
        "description": "Holder / mean-inequality bound on products of functions",
        "shape_tags": ["HOLDER", "LE"],
        "key_lemmas_hint": "Holder, Young, Cauchy-Schwarz",
    },
    "PACKING": {
        "description": "sparse/Carleson packing, bounded multiplicity, or pair-to-owner currency conversion",
        "shape_tags": ["PACKING", "LE"],
        "rank_hints": ["PairwiseDisjoint", "Disjoint", "Finite", "tsum", "sum_le_sum", "measure_iUnion"],
        "key_lemmas_hint": "finite additivity, disjoint union bounds, Carleson embedding, sparse domination",
    },
    "AUXILIARY": {
        "description": "requires constructing a tailored test object (barrier, weight, gauge, carrier, localizer)",
        "shape_tags": [],
        "key_lemmas_hint": "no specific lemma family; construction-driven (pec_a)",
    },
    "UNKNOWN": {
        "description": "no recognized gap type; caller should describe the gap",
        "shape_tags": [],
        "key_lemmas_hint": "n/a",
    },
}


def rank_mathlib_entries(entries: list[dict[str, Any]], gap_type: str) -> list[dict[str, Any]]:
    """Rank retrieved Mathlib entries by gap-specific lexical relevance."""
    hints = GAP_TYPES.get(gap_type, {}).get("rank_hints", [])
    if not hints:
        return sorted(entries, key=lambda e: e.get("name", ""))
    scored = []
    for entry in entries:
        haystack = " ".join([
            entry.get("name", ""),
            entry.get("file", ""),
            entry.get("preview", ""),
        ]).lower()
        score = sum(1 for hint in hints if hint.lower() in haystack)
        scored.append((score, entry.get("name", ""), entry))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [entry for _, _, entry in scored]


def heuristic_gap_type(field_type: str, target: str, field: str) -> dict[str, str]:
    """Cheap local classifier for no-key and preflight environments.

    The classifier is conservative: it commits only on strong field/type
    evidence. Container names such as `Source`, `Receipt`, or `Obligation`
    are treated as weaker packaging cues.
    """
    def match(text: str, needles: list[str]) -> bool:
        return any(needle in text for needle in needles)

    field_hay = f"{field} {field_type}".lower()
    target_hay = target.lower()

    analytic_rules = [
        ("LIMIT_PASSAGE", [
            "limit", "lsc", "lower_semicontinuous", "lowersemicontinuous",
            "liminf", "tendsto", "tail", "prefix_price", "weak",
            "relaxed_output", "measure_defect", "concentration_measure",
            "reynolds_defect", "cauchy", "subseq",
        ]),
        ("COMMUTATOR", ["commutator", "calderon", "bony", "paraproduct"]),
        ("SOBOLEV", ["sobolev", "contdiff", "withderiv", "h1", "h^1", "w14", "w^{"]),
        ("INTERPOLATION", ["interpolation", "interpolate", "lp", "l^", "l2", "l4", "linf"]),
        ("COERCIVITY", [
            "capacity", "coercive", "coercivity", "positive", "nonnegative",
            "lower", "bound", "estimate", "price", "reserve", "quadratic",
            "gram", "sos", "anti-concentration", "anticoncentration",
            "second_moment", "second moment", "secondmoment", "paley",
            "zygmund", "high_interface", "highinterface", "thresholdspike",
            "spike", "amplitudecap", "amplitude_cap", "amplitude cap",
            "physical_amplitude", "physicalamplitude", "pointwise cap",
            "pointwisecap", "pointwise_threshold", "pointwisethreshold",
            "paymentcap", "capmissing", "linf", "l∞",
            "m2overq", "m2_over_q", "m^2/q", "ratio",
            "size_sum_surplus", "sizesumsurplus", "overfill",
            "threshold_deficit", "thresholddeficit",
        ]),
        ("PROPAGATION", [
            "continuation", "recurrence", "evolution", "propagation",
            "budget", "handoff", "embeds", "embedded", "preserved",
        ]),
        ("PACKING", [
            "sparse", "carleson", "packing", "multiplicity", "bounded_overlap",
            "bounded overlap", "pair_to_owner", "pairtoowner", "domination",
            "disjoint", "injection", "injective", "no_reuse", "noreuse",
        ]),
        ("HOLDER", ["holder", "hölder", "product"]),
    ]
    for gap_type, needles in analytic_rules:
        if match(field_hay, needles):
            return {
                "gap_type": gap_type,
                "confidence": "medium",
                "rationale": (
                    f"Local lexical classifier matched {gap_type} evidence in "
                    "the field/type string."
                ),
                "classifier": "local_heuristic",
            }

    carrier_identity_needles = [
        "carrier", "eventtent", "event_tent", "freshregion", "fresh_region",
        "localized", "localization", "punctured", "region", "samecarrier",
        "same_carrier", "prefix", "preimage", "section", "sectionidentity",
        "section_identity", "fixedbefore", "fixed_before", "measure",
        "mass", "variation", "extensional", "loss", "projection",
        "payment", "eigenframe", "eigenvalue", "cone", "inclusion",
    ]
    if match(field_hay, carrier_identity_needles):
        return {
            "gap_type": "AUXILIARY",
            "confidence": "medium",
            "rationale": (
                "Local lexical classifier matched carrier/region identity "
                "language. These gaps usually need a tailored localization "
                "or test-object construction before Lean wiring."
            ),
            "classifier": "local_heuristic",
        }

    auxiliary_needles = ["receipt", "source", "obligation", "bundle", "witness", "catalog"]
    if match(field_hay, auxiliary_needles) or match(target_hay, auxiliary_needles):
        return {
            "gap_type": "AUXILIARY",
            "confidence": "low" if match(target_hay, auxiliary_needles) else "medium",
            "rationale": (
                "Local lexical classifier found packaging/object-construction "
                "language after no stronger analytic field/type cue matched."
            ),
            "classifier": "local_heuristic",
        }
    return {
        "gap_type": "UNKNOWN",
        "confidence": "low",
        "rationale": "No strong local lexical evidence for a supported gap type.",
        "classifier": "local_heuristic",
    }


__all__ = ["GAP_TYPES", "heuristic_gap_type", "rank_mathlib_entries"]
