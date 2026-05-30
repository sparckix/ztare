"""Structural-language fingerprint for RD/workbench use.

This is the executable version of the GP-216/GP-219 "what language do we use?"
surface. It is intentionally a routing and closure primitive, not a theorem
prover and not a replacement for expert judgment.

Use it outside the autoresearch loop to label a closure attempt, F-row, advisor
brief, or gate report with:

  - universal research operations (GP-216 v5)
  - theory-builder/problem-solver culture signal
  - PDE estimate-craft signal (GP-219) when relevant
  - portable GP-219 receipt candidates when their receipt form appears outside PDE
  - which deterministic gates, if any, should be run or cited

The output should help decide placement:

  - crisp contract -> deterministic workbench gate
  - fuzzy recognition -> Director-side routing language
  - scope/frontier choice -> principal/RD decision
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

from .two_cultures import classify_arc
from .universal_classifier import OP_TIER, classify_text
from .universal_research_ops import get as get_universal_op
from .pde_estimate_craft_ops import get as get_pde_op
from .pde_estimate_craft_ops import PORTABLE_RECEIPT_OVERLAP_MAP


# --- consumer_feedback_contract canonical constants (2026-05-16) ---
# The contract previously REQUIRED a `next_lever` field but never defined
# the canonical residual_class -> next_lever map, so consumers forked it.
# Kernel now owns both (operator-authorized kernel improvement). The
# residual_to_lever primitive imports these — single source of truth.
ALLOWED_RESIDUAL_CLASSES = [
    "none_closed",
    "theorem_or_pde_gap",
    "gate_contract_not_crisp",
    "vocabulary_gap",
    "new_channel_or_residual_measure_needed",
    "apparatus_or_source_mismatch",
]

RESIDUAL_TO_LEVER = {
    # CLOSED is UNVERIFIED until governance ratifies (strict two-scoreboard;
    # xpanel discipline + operator_inversion for idea-truth).
    "none_closed": "ratify_closure",
    "theorem_or_pde_gap": "prove_missing_lemma",
    "gate_contract_not_crisp": "restate_target",
    "vocabulary_gap": "operator_review_gp233",
    "new_channel_or_residual_measure_needed": "operator_review_gp233",
    "apparatus_or_source_mismatch": "fix_replay_import_context",
}


PDE_OP_KEYWORDS: dict[str, tuple[str, ...]] = {
    "pec_a": (
        "auxiliary object",
        "comparison object",
        "barrier",
        "majorant",
        "certificate",
        "test function",
        "intertwiner",
        "measure carrier",
        "defect measure",
    ),
    "pec_b": (
        "regime",
        "sub-regime",
        "scope",
        "class scoping",
        "bounded morse",
        "track b",
        "fixed observable",
        "type-i",
        "type i",
        "typei",
        "amplitude envelope",
    ),
    "pec_c": (
        "threshold",
        "dichotomy",
        "either",
        "or collapse",
        "positive variation",
        "channel split",
        "branch coverage",
    ),
    "pec_d": (
        "limit passage",
        "limit-passage",
        "lower semicontinuity",
        "lower-semicontinuity",
        "inheritance",
        "finite prefix",
        "finite-stage",
        "profile limit",
    ),
    "pec_e": (
        "sharpness",
        "failure witness",
        "counterexample",
        "falsifier",
        "adversary",
        "scalar-only",
        "hostile packet",
        "no such object",
    ),
    "pec_f": (
        "proof-surface",
        "obligation list",
        "compress proof",
        "single obligation",
        "closure obligation",
    ),
    "pec_h": (
        "weak-l",
        "weak l",
        "weak_l",
        "tail",
        "distribution",
        "reverse holder",
        "reverse-holder",
        "anti-concentration",
        "anticoncentration",
        "level-set",
        "level set",
        "positive part",
        "signed average",
        "conditional average",
        "critical source square",
        "source-square",
        "source square",
        "source carleson",
        "source-carleson",
        "annular renewal budget",
        "duhamel source square",
        "paraproduct source",
    ),
    "pec_i": (
        "nonadaptive",
        "non-adaptive",
        "fixed before",
        "before payoff",
        "preselected",
        "predeclared",
        "source selection",
        "stopping-time",
        "stopping time",
        "no post hoc",
        "posthoc",
    ),
    "pec_j": (
        "same-carrier",
        "same carrier",
        "fresh capacity",
        "fresh annular",
        "no reuse",
        "no-reuse",
        "rebilling",
        "rebill",
        "packing",
        "injection",
        "bounded overlap",
        "monotone reserve",
        "reserve drop",
    ),
    "pec_k": (
        "phase-space",
        "phase space",
        "microlocal",
        "packet ownership",
        "owner map",
        "owner atom",
        "owner preimage",
        "owned event",
        "owned event prefix",
        "event prefix budget",
        "bounded multiplicity",
        "littlewood-paley",
        "lp tile",
        "material tube",
        "global selected-tree",
        "output-scale",
        "output scale",
        "output packet",
        "full packet",
        "product tile",
        "bilinear packet",
        "factor reuse",
        "factor owner",
        "catalyst",
        "low-high",
        "pressure sheath",
    ),
    "pec_l": (
        "skew",
        "skew-symmetry",
        "energy cancellation",
        "signed cancellation",
        "null-form",
        "null form",
        "symbol vanishing",
        "bilinear cancellation",
        "projection cancellation",
        "leray projection cancellation",
        "commutator cancellation",
        "signed-to-positive",
        "positive source square",
        "high-high",
    ),
    "cand_g": (
        "representation",
        "coordinate",
        "coordinate reformulation",
        "re-express",
        "conjugation",
        "rescale",
        "frame",
        "local-energy identity",
    ),
}

PORTABLE_RECEIPT_OP_IDS = {"pec_a", "pec_b", "pec_e", "cand_g"}


GATE_BY_SIGNAL: dict[str, dict[str, str]] = {
    "broad_01": {
        "gate": "PotentialFunctionMonotonicityGate / BoundChainConsistencyGate",
        "path": "src/ztare/gates/potential_function_monotonicity_gate.py; src/ztare/gates/bound_chain_consistency_gate.py",
        "placement": "workbench_gate_if_rubric_declares_potential_or_bound_chain",
    },
    "pec_a": {
        "gate": "AuxiliaryObjectDeclarationGate",
        "path": "src/ztare/gates/auxiliary_object_declaration_gate.py",
        "placement": "workbench_gate",
    },
    "pec_c": {
        "gate": "ThresholdDichotomyBranchCoverageGate",
        "path": "src/ztare/gates/threshold_dichotomy_branch_coverage_gate.py",
        "placement": "workbench_gate",
    },
    "pec_d": {
        "gate": "LimitPassageInheritanceLemmaGate",
        "path": "src/ztare/gates/limit_passage_inheritance_lemma_gate.py",
        "placement": "workbench_gate",
    },
}


@dataclass(frozen=True)
class OperationSignal:
    op_id: str
    name: str
    family: str
    score: int
    tier: str
    placement: str
    gate: Optional[str] = None
    gate_path: Optional[str] = None
    required_schema_fields: tuple[str, ...] = ()
    nearest_universal_ops: tuple[str, ...] = ()
    overlap_status: str = ""
    promotion_rule: str = ""


@dataclass(frozen=True)
class StructuralFingerprint:
    substrate: Optional[str]
    evidence_pointer: Optional[str]
    universal_ops: list[OperationSignal]
    tb_ps_culture: dict[str, Any]
    pde_ops_or_not_applicable: str | list[OperationSignal]
    portable_receipt_ops: list[OperationSignal]
    mechanization_placement: list[str]
    residual_language_feedback: dict[str, Any]
    next_move_effect: Optional[str]
    caveat: str


def _count_keywords(text: str, keywords: Iterable[str]) -> int:
    lower = text.lower()
    return sum(lower.count(keyword.lower()) for keyword in keywords)


def _looks_pde(substrate: Optional[str], text: str) -> bool:
    haystack = f"{substrate or ''} {text}".lower()
    if any(token in haystack for token in ("non-pde", "non pde", "not pde")):
        return False
    return any(
        token in haystack
        for token in (
            "ns",
            "navier",
            "stokes",
            "pde",
            "millennium",
            "analysis",
            "estimate",
            "sobolev",
            "local energy",
            "defect measure",
        )
    )


def _universal_signals(text: str, *, max_ops: int) -> list[OperationSignal]:
    classification = classify_text(text, min_signal=1)
    ranked = sorted(
        classification.op_signals.items(),
        key=lambda item: (-item[1], item[0]),
    )[:max_ops]
    signals: list[OperationSignal] = []
    for op_id, score in ranked:
        op = get_universal_op(op_id)
        if not op:
            continue
        gate_info = GATE_BY_SIGNAL.get(op_id)
        signals.append(
            OperationSignal(
                op_id=op_id,
                name=op.name,
                family="universal_v5",
                score=score,
                tier=OP_TIER.get(op_id, op.tier),
                placement=gate_info["placement"] if gate_info else "director_side_recognition",
                gate=gate_info.get("gate") if gate_info else None,
                gate_path=gate_info.get("path") if gate_info else None,
            )
        )
    return signals


def _estimate_craft_signals(
    text: str,
    *,
    max_ops: int,
    op_ids: set[str] | None = None,
    family: str = "gp219_pde_estimate_craft",
) -> list[OperationSignal]:
    allowed = op_ids or set(PDE_OP_KEYWORDS)
    counts: Counter[str] = Counter()
    for op_id, keywords in PDE_OP_KEYWORDS.items():
        if op_id not in allowed:
            continue
        count = _count_keywords(text, keywords)
        if count:
            counts[op_id] = count

    signals: list[OperationSignal] = []
    for op_id, score in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:max_ops]:
        op = get_pde_op(op_id)
        if not op:
            continue
        gate_info = GATE_BY_SIGNAL.get(op_id)
        signals.append(
            OperationSignal(
                op_id=op_id,
                name=op.name,
                family=family,
                score=score,
                tier=op.tier,
                placement=gate_info["placement"] if gate_info else "director_side_recognition",
                gate=gate_info.get("gate") if gate_info else None,
                gate_path=gate_info.get("path") if gate_info else None,
                required_schema_fields=op.portable_receipt_fields,
                nearest_universal_ops=tuple(
                    PORTABLE_RECEIPT_OVERLAP_MAP.get(op_id, {}).get(
                        "nearest_universal_ops", ()
                    )
                ),
                overlap_status=str(
                    PORTABLE_RECEIPT_OVERLAP_MAP.get(op_id, {}).get(
                        "overlap_status", ""
                    )
                ),
                promotion_rule=str(
                    PORTABLE_RECEIPT_OVERLAP_MAP.get(op_id, {}).get(
                        "promotion_rule", ""
                    )
                ),
            )
        )
    return signals


def _pde_signals(text: str, *, max_ops: int) -> list[OperationSignal]:
    return _estimate_craft_signals(text, max_ops=max_ops)


def _portable_receipt_signals(text: str, *, max_ops: int) -> list[OperationSignal]:
    return _estimate_craft_signals(
        text,
        max_ops=max_ops,
        op_ids=PORTABLE_RECEIPT_OP_IDS,
        family="gp219_portable_receipt_candidate",
    )


def build_structural_fingerprint(
    text: str,
    *,
    substrate: Optional[str] = None,
    evidence_pointer: Optional[str] = None,
    next_move_effect: Optional[str] = None,
    max_ops: int = 5,
) -> StructuralFingerprint:
    """Return a structural-language fingerprint for a research artifact.

    The result is deliberately conservative: no signal means "unclassified",
    not "no structure." Callers should cite this as a routing/fingerprint
    artifact, not as independent validation of a mathematical claim.
    """
    universal = _universal_signals(text, max_ops=max_ops)
    culture = classify_arc(text, min_signal=1)
    pde_applicable = _looks_pde(substrate, text)
    pde_ops = _pde_signals(text, max_ops=max_ops) if pde_applicable else []
    portable_ops = _portable_receipt_signals(text, max_ops=max_ops)

    placements: list[str] = []
    placement_seen: set[tuple[str, str]] = set()
    for signal in [*universal, *pde_ops, *portable_ops]:
        key = (signal.family, signal.op_id)
        if key in placement_seen:
            continue
        placement_seen.add(key)
        if signal.gate:
            placements.append(
                f"{signal.op_id}: run/cite {signal.gate} ({signal.placement})"
            )
        else:
            placements.append(f"{signal.op_id}: {signal.placement}")
    if not placements:
        placements.append("no deterministic gate suggested; keep Director-side")

    residual_feedback = {
        "required_from_consumer": True,
        "rule": (
            "Use universal language to route, math/PDE language to act, gates "
            "or portable receipt fields to act, gates only when the local contract is crisp, "
            "and residuals to decide "
            "whether the language must extend."
        ),
        "allowed_residual_classes": ALLOWED_RESIDUAL_CLASSES,
        "residual_to_lever": RESIDUAL_TO_LEVER,
        "minimum_feedback_fields": [
            "residual_class",
            "residual_summary",
            "did_language_change_next_action",
            "evidence_pointer",
            "next_lever",
        ],
        "extension_trigger": (
            "If a residual is decision-changing and cannot be classified by "
            "the current universal/PDE vocabulary without stretching a term, "
            "log vocabulary_gap or new_channel_or_residual_measure_needed and "
            "route through GP-233 plus a seam/spec update before promoting the "
            "language as reusable."
        ),
    }

    return StructuralFingerprint(
        substrate=substrate,
        evidence_pointer=evidence_pointer,
        universal_ops=universal,
        tb_ps_culture={
            "dominant": culture.dominant,
            "confidence": culture.confidence,
            "tb_signal": culture.tb_signal,
            "ps_signal": culture.ps_signal,
            "rationale": culture.rationale,
        },
        pde_ops_or_not_applicable=pde_ops if pde_applicable else "not_applicable",
        portable_receipt_ops=portable_ops,
        mechanization_placement=placements,
        residual_language_feedback=residual_feedback,
        next_move_effect=next_move_effect,
        caveat=(
            "Heuristic RD/workbench fingerprint only. Use it to choose gates, "
            "closure language, and Director routing; do not treat it as proof "
            "that the system generated or validated the underlying research claim."
        ),
    )


def fingerprint_to_dict(fingerprint: StructuralFingerprint) -> dict[str, Any]:
    return asdict(fingerprint)


def render_fingerprint(fingerprint: StructuralFingerprint) -> str:
    data = fingerprint_to_dict(fingerprint)
    return json.dumps(data, indent=2, sort_keys=True)


def _read_text(args: argparse.Namespace) -> str:
    parts: list[str] = []
    if args.text:
        parts.append(args.text)
    if args.text_file:
        parts.append(args.text_file.read_text(encoding="utf-8"))
    if args.json_file:
        data = json.loads(args.json_file.read_text(encoding="utf-8"))
        parts.append(json.dumps(data, sort_keys=True))
    return "\n\n".join(parts).strip()


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build a GP-216/GP-219 structural-language fingerprint")
    parser.add_argument("--text", default=None, help="Text to fingerprint")
    parser.add_argument("--text-file", type=Path, default=None, help="Markdown/text file to fingerprint")
    parser.add_argument("--json-file", type=Path, default=None, help="JSON artifact to fingerprint")
    parser.add_argument("--substrate", default=None, help="Substrate hint, e.g. ns_millennium_hunt")
    parser.add_argument("--evidence-pointer", default=None, help="Evidence row/path/id to preserve in output")
    parser.add_argument("--next-move-effect", default=None, help="What this fingerprint changes about the next move")
    parser.add_argument("--max-ops", type=int, default=5)
    args = parser.parse_args(argv)

    text = _read_text(args)
    if not text:
        parser.error("provide --text, --text-file, or --json-file")

    fingerprint = build_structural_fingerprint(
        text,
        substrate=args.substrate,
        evidence_pointer=args.evidence_pointer,
        next_move_effect=args.next_move_effect,
        max_ops=args.max_ops,
    )
    print(render_fingerprint(fingerprint))
    return 0


__all__ = [
    "OperationSignal",
    "StructuralFingerprint",
    "build_structural_fingerprint",
    "fingerprint_to_dict",
    "render_fingerprint",
]


if __name__ == "__main__":
    raise SystemExit(main())
