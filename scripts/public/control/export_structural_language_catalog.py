#!/usr/bin/env python3
"""Export GP-216/GP-219 structural language as machine-readable JSON."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]  # scripts/public/control/<file>
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from src.ztare.research_director import pde_estimate_craft_ops, two_cultures, universal_classifier, universal_research_ops  # noqa: E402


# Canonical TRACKED long-term home (sibling of the rendered .md in
# docs/reference/). The prior default lived under /workingpapers/ which is
# gitignored (ephemeral) yet many runtime readers + AGENTS.md + 3
# org/patterns hard-code it — a dead-path fragility. This is a RENDER of
# the canonical Python registries (universal_research_ops etc.); regenerate
# via this script, do not hand-edit.
DEFAULT_OUT = REPO / "docs/reference/structural_language_catalog.json"
LEGACY_OUT = REPO / "workingpapers/epistemic-generation/evidence/structural_language_catalog_20260514.json"


def _universal_ops() -> list[dict]:
    return [
        {
            **asdict(op),
            "family": "gp216_structural_v5",
            "validation_status": "saved_output_verified",
            "paper_claim_status": "portable_system_bound_structural_language",
        }
        for op in universal_research_ops.VOCABULARY_V5.values()
    ]


def _meta_meta_ops() -> list[dict]:
    rows = []
    for op in universal_research_ops.META_META_VOCABULARY.values():
        status = op.validation_status.lower()
        if status == "warranted_narrow":
            paper_status = "warranted_narrow_model_mediated_human_audit_owed"
        elif status == "refuted":
            paper_status = "refuted_descriptive_retained_only_as_caution_or_functional_arm"
        else:
            paper_status = "pre_warrant_do_not_use_as_validated_paper_claim"
        rows.append({
            **asdict(op),
            "family": "gp216_meta_meta_game_layer",
            "paper_claim_status": paper_status,
        })
    return rows


def _pde_ops() -> list[dict]:
    return [
        {
            **asdict(op),
            "family": "gp219_pde_estimate_craft",
            "paper_claim_status": (
                "companion_boundary_language"
                if op.tier != "v5_candidate"
                else "candidate_do_not_promote_without_validation"
            ),
        }
        for op in pde_estimate_craft_ops.VOCABULARY_GP219
    ]


def build_catalog() -> dict:
    return {
        "schema_version": "gp216_structural_language_catalog_v2",
        "generated_date": date.today().isoformat(),
        "source_modules": {
            "universal_v5": "src/ztare/research_director/universal_research_ops.py",
            "pde_estimate_craft": "src/ztare/research_director/pde_estimate_craft_ops.py",
            "two_cultures": "src/ztare/research_director/two_cultures.py",
            "heuristic_classifier": "src/ztare/research_director/universal_classifier.py",
            "fingerprint_surface": "src/ztare/research_director/structural_fingerprint.py",
        },
        "usage_rule": (
            "Use GP-216 v5 to route structural research moves; use GP-219 only "
            "when PDE/estimate-craft is substantively in scope; use meta_meta "
            "ops as game-layer/frame/object primitives with their per-op "
            "validation_status; log residuals instead of stretching labels."
        ),
        "claim_guardrails": [
            "not a complete ontology",
            "not autonomous theory generation",
            "not expert validation",
            "not medicine/law/biology coverage",
            "not a license to promote OOD residuals without audit",
        ],
        "universal_v5_ops": _universal_ops(),
        "pde_estimate_craft_ops": _pde_ops(),
        "meta_meta_ops": _meta_meta_ops(),
        "meta_meta_pre_warrant_ops": _meta_meta_ops(),
        "two_cultures_empirical_table": two_cultures.CROSS_DISTRIBUTION_2X2,
        "two_cultures_op_tiers": two_cultures.OP_TIERS,
        "two_cultures_cross_cultural_pairs": [
            {"tb_op": tb, "ps_op": ps, "description": description}
            for tb, ps, description in two_cultures.CROSS_CULTURAL_PAIRS
        ],
        "heuristic_classifier": {
            "op_keywords": universal_classifier.OP_KEYWORDS,
            "op_tier": universal_classifier.OP_TIER,
            "warning": "keyword routing surface only; not paper-grade tagging",
        },
        "consumer_feedback_contract": {
            "rule": (
                "Use universal language to route. Use math/PDE language to act. "
                "Use gates only when the local contract is crisp. Use residuals "
                "to decide whether the language must extend."
            ),
            "allowed_residual_classes": [
                "none_closed",
                "theorem_or_domain_gap",
                "gate_contract_not_crisp",
                "vocabulary_gap",
                "new_channel_or_residual_measure_needed",
                "apparatus_or_source_mismatch",
            ],
            "minimum_fields": [
                "residual_class",
                "residual_summary",
                "did_language_change_next_action",
                "evidence_pointer",
                "next_lever",
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    catalog = build_catalog()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(catalog, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
