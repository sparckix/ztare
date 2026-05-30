#!/usr/bin/env python3
"""Rubric scaffolder — emit a canonical-format skeleton (2026-05-02).

Mechanizes the canonical rubric layout (see
`docs/concepts/rubric_specification.md` and the `validate_rubric.py`
pre-flight gate) so that authoring a NEW rubric never starts from a
blank file or the legacy `criteria{}`-only shape. Eliminates the
recurring "make loop fails on missing dimensions" cycle.

Usage:
    python scripts/public/utilities/scaffold_rubric.py <project_slug>
    python scripts/public/utilities/scaffold_rubric.py <project_slug> --mode qualitative
    python scripts/public/utilities/scaffold_rubric.py <project_slug> --mode numerical
    python scripts/public/utilities/scaffold_rubric.py <project_slug> --mode qualitative --force

Modes:
    qualitative — audit/topology/criteria-stress-test substrates with
        no numeric I_model. Sets cage_observe_mode + disable_evidence_fit_gate
        + audit cage_meta. Default rubric_mode=kepler. Five placeholder
        dimensions summing to 100.
    numerical — formal-recovery / curve-fit substrates with a real
        I_model + holdout dataset. Default rubric_mode=newton with
        Generative Yield dimension at weight 15. Six placeholder
        dimensions summing to 100.

Behavior:
    - Writes to `rubrics/<slug>.json`.
    - Refuses to overwrite an existing rubric unless --force is set.
    - Validates the emitted file against `scripts/public/validators/validate_rubric.py`
      before declaring success.
    - Exits 0 on PASS / 1 on validator FAIL / 2 on invocation error.
"""
from __future__ import annotations

import argparse
import json
import sys
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RUBRIC_DIR = REPO / "rubrics"
VALIDATOR = REPO / "scripts" / "validate_rubric.py"


def _qualitative_skeleton(slug: str) -> dict:
    return {
        "name": f"{slug} — qualitative audit substrate",
        "project": slug,
        "description": (
            "REPLACE: one-paragraph description of the substrate, the "
            "eigenquestion it audits, and the load-bearing failure modes "
            "the rubric is designed to catch."
        ),
        "rubric_mode": "kepler",
        "rubric_mode_reason": (
            "Audit/calibration substrate; not aiming at new-science "
            "discovery. Kepler avoids the newton-mode requirement of a "
            "Generative Yield dimension with weight ≥ 15."
        ),
        "falsification_mode": "qualitative_thesis",
        "enable_fit_primitive": False,
        "enable_fit_primitive_features": False,
        "holdout_hard_gate": False,
        "holdout_hard_gate_reason": (
            "Qualitative audit; no numeric I_model and no holdout dataset."
        ),
        "disable_evidence_fit_gate": True,
        "disable_evidence_fit_gate_reason": (
            "No numeric ground truth. evidence.txt is a qualitative brief."
        ),
        "disable_uniqueness_gap_gate": True,
        "disable_uniqueness_gap_gate_reason": (
            "Uniqueness-gap gate requires numeric I_model residuals; "
            "structurally inapplicable to qualitative substrates."
        ),
        "cage_observe_mode": True,
        "cage_observe_mode_reason": (
            "Cage gates run in observe-mode so the apparatus does not "
            "block iterations on numeric-harness violations from a "
            "non-numeric I_model. The rubric judge is the load-bearing scorer."
        ),
        "cage_meta": {
            "type": "qualitative_audit",
            "class": "audit",
            "target_convention_homogeneity": "homogeneous",
            "min_rows_per_category": 0,
            "near_miss_factor": 0.0,
            "frame_invariant_y": True,
            "review_type": "REPLACE_with_audit_descriptor"
        },
        "require_i_model_in_submission": False,
        "require_i_model_in_submission_reason": (
            "Audit / qualitative-thesis substrate. Without this flag the "
            "R1 mutation_suite_guard rejects every submission for missing "
            "I_model — the bug that ate gp168 v3 + gp169 launches."
        ),
        "farther_tail_region": None,
        "farther_tail_region_disable_reason": (
            "No numeric domain → no tail region."
        ),
        "enable_cold_llm_erdos_seed": True,
        "enable_erdos_requery_on_stagnation": True,
        "erdos_requery_stagnation_threshold": 2,
        "erdos_requery_max_per_run": 3,
        "enable_qualitative_stagnation_detection": True,
        "qualitative_stagnation_threshold": 3,
        "qualitative_stagnation_reason": (
            "Qualitative substrates do not produce score==0 or "
            "PARAMETRIC_FORM AST bucket lock. The qualitative-stagnation "
            "trigger uses weakest_point gate-name fingerprint repetition "
            "+ sub-baseline drift (forced_reframe.py Trigger 4)."
        ),
        "dimensions": [
            {
                "name": "REPLACE Hard Gate 1",
                "weight": 25,
                "description": "REPLACE — typically the highest-leverage hard gate."
            },
            {
                "name": "REPLACE Hard Gate 2",
                "weight": 20,
                "description": "REPLACE — second hard gate."
            },
            {
                "name": "REPLACE Mechanism Coverage",
                "weight": 20,
                "description": "REPLACE — worked mechanism vs assertion."
            },
            {
                "name": "REPLACE Counterfactual Discipline",
                "weight": 15,
                "description": "REPLACE — contrast against named alternatives."
            },
            {
                "name": "REPLACE Falsification + Revision Path",
                "weight": 10,
                "description": "REPLACE — falsifying observation + revision plan."
            },
            {
                "name": "REPLACE Rubric-Gaming Self-Diagnosis",
                "weight": 10,
                "description": "REPLACE — name gaming surface + propose external check."
            }
        ],
        "persona": (
            "REPLACE: an adversarial-judge persona description. State the "
            "judge's expertise, what they reward, what they attack, and "
            "what counts as a tautological/gamed answer. 2-4 sentences."
        ),
        "criteria": {
            "REPLACE Hard Gate 1": "REPLACE — full prose for the gate.",
            "REPLACE Hard Gate 2": "REPLACE — full prose for the gate."
        }
    }


def _numerical_skeleton(slug: str) -> dict:
    return {
        "name": f"{slug} — numerical recovery substrate",
        "project": slug,
        "description": (
            "REPLACE: one-paragraph description of the formal-recovery "
            "target, the substrate class (e.g. continuous_chaotic, "
            "scaling_law, algebraic_constant), and the load-bearing "
            "anti-pattern the rubric is designed to catch."
        ),
        "rubric_mode": "newton",
        "rubric_mode_reason": (
            "Numerical-recovery substrate aiming at a generative new-science "
            "yield (a falsifiable functional form, an exponent, an invariant). "
            "Newton-mode requires the Generative Yield dimension at weight ≥ 15."
        ),
        "falsification_mode": "bounded_discriminator",
        "enable_fit_primitive": True,
        "enable_fit_primitive_features": True,
        "holdout_hard_gate": True,
        "holdout_hard_gate_reason": (
            "Real holdout dataset present; the apparatus must enforce "
            "out-of-sample recovery, not training-set fit."
        ),
        "target_convention_homogeneity": True,
        "inject_antipattern_catalog": True,
        "structural_blocker_enforcement": True,
        "underidentified_after": 3,
        "cage_meta": {
            "class": "REPLACE_substrate_class",
            "review_type": "numerical_recovery"
        },
        "dimensions": [
            {
                "name": "Generative Yield",
                "weight": 20,
                "description": "REPLACE — newton-mode load-bearing dim. Concrete falsifiable claim that survives holdout."
            },
            {
                "name": "Mechanism Concreteness",
                "weight": 20,
                "description": "REPLACE — worked mechanism vs ad-hoc fit."
            },
            {
                "name": "REPLACE Substrate-Specific Hard Gate",
                "weight": 20,
                "description": "REPLACE — domain-load-bearing gate (e.g. PPN compatibility, ergodicity, Buckingham-π scaling)."
            },
            {
                "name": "Holdout MRE / OOD Recovery",
                "weight": 15,
                "description": "REPLACE — out-of-sample MRE bound."
            },
            {
                "name": "Falsification Surface",
                "weight": 15,
                "description": "REPLACE — concrete falsifying observation + revision path."
            },
            {
                "name": "Rubric-Gaming Self-Diagnosis",
                "weight": 10,
                "description": "REPLACE — name gaming surface + propose external check."
            }
        ],
        "persona": (
            "REPLACE: an adversarial-judge persona for the substrate's "
            "domain. Domain expertise + adversarial skepticism + intolerance "
            "for ad-hoc fits and tautological mechanisms."
        ),
        "criteria": {
            "Generative Yield": "REPLACE — full prose.",
            "Mechanism Concreteness": "REPLACE — full prose."
        }
    }


def _validate(rubric_path: Path, slug: str) -> bool:
    if not VALIDATOR.exists():
        print(f"⚠️  validator not found at {VALIDATOR}; skipping pre-flight check")
        return True
    r = subprocess.run(
        [sys.executable, str(VALIDATOR), slug, "--rubric", str(rubric_path)],
        cwd=REPO, capture_output=True, text=True,
    )
    print(r.stdout)
    if r.stderr:
        print(r.stderr, file=sys.stderr)
    return r.returncode == 0


def main() -> int:
    p = argparse.ArgumentParser(description="Scaffold a canonical-format rubric")
    p.add_argument("slug", help="Project slug (e.g. gp169_consciousness_audit)")
    p.add_argument("--mode", choices=["qualitative", "numerical"],
                   default="qualitative",
                   help="Rubric mode (default: qualitative)")
    p.add_argument("--force", action="store_true",
                   help="Overwrite existing rubric file")
    args = p.parse_args()

    target = RUBRIC_DIR / f"{args.slug}.json"
    if target.exists() and not args.force:
        print(f"❌ rubric already exists: {target} (pass --force to overwrite)")
        return 2

    skeleton = (
        _qualitative_skeleton(args.slug) if args.mode == "qualitative"
        else _numerical_skeleton(args.slug)
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(skeleton, indent=2) + "\n", encoding="utf-8")
    print(f"✅ wrote canonical-format skeleton: {target}")
    print(f"   mode: {args.mode}")
    print(f"   dimensions: {len(skeleton['dimensions'])}, "
          f"weight sum: {sum(d['weight'] for d in skeleton['dimensions'])}")
    print()
    print("Now: replace every REPLACE marker with project-specific content,")
    print(f"then re-run `python scripts/public/validators/validate_rubric.py {args.slug}` to confirm PASS.")
    print()
    print("Pre-flight validation:")
    ok = _validate(target, args.slug)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
