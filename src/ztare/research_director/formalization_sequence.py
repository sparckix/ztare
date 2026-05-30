"""Formalization sequencing precheck.

Classify whether a proof tick should start with informal theorem-surface
reasoning or go directly to formal proof work.  The primitive is intentionally
lexical and deterministic: it is a cheap guard against formalizing unstable
statements before the carrier/observable has been audited.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = (
    REPO / "analytics" / "public" / "queries" / "formalization_sequence" / "latest.json"
)

GOWERS_FIRST_TERMS = {
    "carrier",
    "observable",
    "same carrier",
    "same-carrier",
    "positive flux",
    "positive cutoff",
    "signed flux",
    "pressure l2",
    "pressure-l2",
    "duchon robert",
    "duchon-robert",
    "countermodel",
    "no go",
    "no-go",
    "shear",
    "same window",
    "same-window",
    "cancellation",
    "telescoping",
    "telescope",
    "scale power",
    "multiplicity",
    "visibility",
    "invisible",
    "critical tail",
    "missing hypothesis",
    "functional mismatch",
    "theorem surface",
    "statement unstable",
    "wrong statement",
    "wrong observable",
}

LEAN_FIRST_TERMS = {
    "routine formalization",
    "known theorem",
    "compiled theorem",
    "constructor wiring",
    "scalar transitivity",
    "algebra only",
    "rewrite",
    "simp",
    "exact",
    "lake build",
    "no sorry",
    "no admit",
    "known statement",
}

WRAPPER_RISK_TERMS = {
    "field",
    "receipt",
    "source",
    "producer",
    "obligation",
    "assume",
    "conditional",
    "visibility",
    "charge",
    "pays",
    "lower payment",
}


@dataclass(frozen=True)
class FormalizationSequenceReport:
    generated_at: str
    branch_text: str
    verdict: str
    gowers_first_score: int
    lean_first_score: int
    wrapper_risk_score: int
    matched_gowers_first_terms: list[str]
    matched_lean_first_terms: list[str]
    matched_wrapper_risk_terms: list[str]
    vocabulary_fingerprint: dict[str, list[str]]
    recommended_next_steps: list[str]
    output_path: str | None = None


def _normalize(text: str) -> str:
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", text)
    text = text.lower().replace("_", " ").replace("`", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _matched_terms(text: str, terms: set[str]) -> list[str]:
    norm = _normalize(text)
    matches = []
    for term in sorted(terms):
        if term in norm:
            matches.append(term)
    return matches


def _vocabulary_fingerprint(verdict: str) -> dict[str, list[str]]:
    if verdict == "gowers_first_required":
        return {
            "universal_research_ops": [
                "core_03 decomposition and recomposition",
                "broad_05 extremal/countermodel case analysis",
                "core_02 generalization only after the survivor is stable",
            ],
            "theory_building_ops": [
                "tb_06 tacit pattern formalization after informal surface discovery",
                "tb_LAK2 proof-analysis under counter-example",
            ],
            "problem_solving_ops": [
                "ps_06 proof by estimate chaining after the right observable is fixed",
            ],
            "pde_estimate_craft_ops": [
                "pec_a auxiliary comparison object",
                "pec_c threshold/channel split",
                "pec_e sharpness or failure witness",
                "cand_g observable reformulation",
            ],
        }
    if verdict == "lean_first_ok":
        return {
            "universal_research_ops": ["broad_01 iterative refinement"],
            "theory_building_ops": ["tb_06 tacit pattern formalization"],
            "problem_solving_ops": ["ps_06 proof by estimate chaining"],
            "pde_estimate_craft_ops": ["formal verification of fixed endpoint"],
        }
    return {
        "universal_research_ops": ["core_03 decomposition", "broad_05 extremal audit"],
        "theory_building_ops": ["tb_06 tacit pattern formalization"],
        "problem_solving_ops": ["ps_06 estimate chaining"],
        "pde_estimate_craft_ops": ["pec_a auxiliary object", "pec_e failure witness"],
    }


def classify_formalization_sequence(
    branch_text: str,
    *,
    output_path: Path | None = None,
) -> FormalizationSequenceReport:
    gowers_matches = _matched_terms(branch_text, GOWERS_FIRST_TERMS)
    lean_matches = _matched_terms(branch_text, LEAN_FIRST_TERMS)
    wrapper_matches = _matched_terms(branch_text, WRAPPER_RISK_TERMS)

    gowers_score = len(gowers_matches) + min(len(wrapper_matches), 4)
    lean_score = len(lean_matches)
    wrapper_score = len(wrapper_matches)

    if gowers_score >= max(4, lean_score + 2):
        verdict = "gowers_first_required"
        next_steps = [
            "write a 10-30 line informal proof or countermodel before editing formal code",
            "name observable, carrier, sign, scale, telescope, and failure model",
            "formalize only the survivor: corrected primitive, route consequence, and no-go guard",
        ]
    elif lean_score >= max(3, gowers_score + 2):
        verdict = "lean_first_ok"
        next_steps = [
            "proceed directly to formal proof work",
            "keep the theorem surface fixed and verify no new wrapper field is introduced",
        ]
    else:
        verdict = "mixed_sequence"
        next_steps = [
            "do a short informal surface audit, then formalize the scalar or constructor step",
            "record whether the informal pass found proof route, no-go, or missing hypothesis",
        ]

    report = FormalizationSequenceReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        branch_text=branch_text,
        verdict=verdict,
        gowers_first_score=gowers_score,
        lean_first_score=lean_score,
        wrapper_risk_score=wrapper_score,
        matched_gowers_first_terms=gowers_matches,
        matched_lean_first_terms=lean_matches,
        matched_wrapper_risk_terms=wrapper_matches,
        vocabulary_fingerprint=_vocabulary_fingerprint(verdict),
        recommended_next_steps=next_steps,
        output_path=None,
    )

    output_path = (output_path or DEFAULT_OUTPUT).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(report)
    payload["output_path"] = str(output_path.relative_to(REPO))
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return FormalizationSequenceReport(**payload)


def render_text(report: FormalizationSequenceReport) -> str:
    lines = [
        "  formalization_sequence_ok = True",
        f"  verdict: {report.verdict}",
        (
            "  scores: "
            f"gowers_first={report.gowers_first_score}, "
            f"lean_first={report.lean_first_score}, "
            f"wrapper_risk={report.wrapper_risk_score}"
        ),
    ]
    if report.output_path:
        lines.append(f"  artifact: {report.output_path}")
    if report.matched_gowers_first_terms:
        lines.append(
            "  gowers-first triggers: "
            + ", ".join(report.matched_gowers_first_terms[:16])
        )
    if report.matched_lean_first_terms:
        lines.append(
            "  lean-first triggers: " + ", ".join(report.matched_lean_first_terms[:16])
        )
    if report.matched_wrapper_risk_terms:
        lines.append(
            "  wrapper-risk triggers: "
            + ", ".join(report.matched_wrapper_risk_terms[:16])
        )
    lines.append("  vocabulary fingerprint:")
    for family, ops in report.vocabulary_fingerprint.items():
        lines.append(f"    - {family}: {', '.join(ops)}")
    lines.append("  next steps:")
    for step in report.recommended_next_steps:
        lines.append(f"    - {step}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch-text", required=True)
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args(argv)
    report = classify_formalization_sequence(
        args.branch_text,
        output_path=Path(args.output),
    )
    print(render_text(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
