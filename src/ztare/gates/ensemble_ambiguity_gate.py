"""GP-144 Gate G7 — Ensemble Ambiguity (SPECULATIVE SHELL; largely implementable today).

Status: 2026-04-24 — core logic implementable today; only the upstream
Phase-C-returns-ensemble extension is blocked.

PURPOSE
-------
When Phase C produces multiple candidates whose scores are near-tied
(within margin_of_ambiguity), the Phase D writer must SURFACE THE
ENSEMBLE rather than silently select one. Silent selection hides
candidate-selection bias and creates the illusion of a unique champion
when the data does not support uniqueness.

DISCOVERY
---------
gp147 iter 2 meta-validation, H3.

CORE CHECK
----------
Given a candidate list with scores, identify candidates within
margin_of_ambiguity (default 5% of top score) of the leader. If ≥2 such
candidates exist, require the Phase D writer's output to contain an
`ensemble_members` field enumerating all of them; reject silent single-
candidate selection.

The check itself is implementable today. What's deferred: Phase C
currently emits a single candidate, not an ensemble, so this gate has
nothing to check in the current pipeline.
"""
from __future__ import annotations

from typing import Any

GATE_ID = "ensemble_ambiguity"
PRODUCER = "GP-144.G7"


def ambiguity_check(
    candidates: list[dict[str, Any]],
    margin_of_ambiguity_fraction: float = 0.05,
) -> dict[str, Any]:
    """Identify all candidates within margin*top_score of the best. Report
    the ambiguous subset.

    IMPLEMENTED TODAY. Operates on any list of {score: <float>, ...} dicts.
    """
    if not candidates:
        return {"ambiguous_set": [], "top_score": None, "margin": 0.0,
                "passed": True, "reason": "empty_candidate_list"}
    scored = [(i, c.get("score")) for i, c in enumerate(candidates)
              if isinstance(c.get("score"), (int, float))]
    if not scored:
        return {"ambiguous_set": [], "top_score": None, "margin": 0.0,
                "passed": False, "reason": "no_scored_candidates"}
    top = max(s for _, s in scored)
    threshold = top * (1.0 - margin_of_ambiguity_fraction)
    ambiguous = [i for i, s in scored if s >= threshold]
    return {
        "top_score": top,
        "margin": margin_of_ambiguity_fraction,
        "threshold": threshold,
        "ambiguous_set_indices": ambiguous,
        "ambiguous_set_size": len(ambiguous),
        "passed": None,  # verdict is about DISCLOSURE, not ambiguity itself
        "reason": f"{len(ambiguous)}_candidates_within_{margin_of_ambiguity_fraction:.0%}_of_top",
    }


def ensemble_disclosure_check(
    phase_d_output: dict[str, Any],
    ambiguous_size: int,
) -> dict[str, Any]:
    """Verify Phase D output discloses the ensemble when ambiguous_size >= 2.

    IMPLEMENTED TODAY. Reads the Phase D output dict.
    """
    if ambiguous_size < 2:
        return {"passed": True, "reason": "no_ambiguity_no_disclosure_required"}
    ensemble = phase_d_output.get("ensemble_members")
    if ensemble is None:
        return {
            "passed": False,
            "reason": (f"{ambiguous_size}_ambiguous_candidates_but_phase_d_did_not_emit_"
                       "ensemble_members_field"),
        }
    if not isinstance(ensemble, list) or len(ensemble) < ambiguous_size:
        return {
            "passed": False,
            "reason": (f"ensemble_members_present_but_size_{len(ensemble) if isinstance(ensemble, list) else 0}"
                       f"_does_not_cover_ambiguous_set_{ambiguous_size}"),
        }
    return {"passed": True, "reason": "ensemble_disclosed"}


def run_gate(
    claim: dict[str, Any],
    rubric_params: dict[str, Any],
) -> dict[str, Any]:
    """Run G7 ensemble-ambiguity on a claim.

    claim schema:
        {
            "candidates": [{"score": <float>, ...}, ...],    # from Phase C
            "phase_d_output": {"ensemble_members": [...], ...}  # from Phase D writer
        }
    """
    candidates = claim.get("candidates", [])
    phase_d = claim.get("phase_d_output", {})
    margin = float(rubric_params.get("margin_of_ambiguity_fraction", 0.05))

    r_amb = ambiguity_check(candidates, margin_of_ambiguity_fraction=margin)
    if r_amb.get("ambiguous_set_size") is None:
        # Empty / malformed — shell reports unverifiable
        return {
            "name": GATE_ID,
            "passed": None,
            "actual": None,
            "threshold": None,
            "reason": (f"shell_not_fully_implemented: Phase C did not emit a multi-candidate "
                       f"list. Ambiguity check needs candidate ensemble as input. "
                       f"Upstream Phase C extension pending."),
            "penalty": 0,
            "hard_fail": False,
            "source": PRODUCER,
            "extra": {
                "ambiguity_check": r_amb,
                "shell_fully_implemented": False,
                "blocked_on": "Phase C ensemble extension",
            },
        }

    r_disc = ensemble_disclosure_check(phase_d, r_amb["ambiguous_set_size"])
    passed = r_disc["passed"]
    return {
        "name": GATE_ID,
        "passed": passed,
        "actual": r_amb["ambiguous_set_size"],
        "threshold": None,  # no fixed threshold; contextual
        "reason": f"{r_amb['reason']}; disclosure={r_disc['reason']}",
        "penalty": 0 if passed else 1,
        "hard_fail": False,
        "source": PRODUCER,
        "extra": {
            "ambiguity_check": r_amb,
            "disclosure_check": r_disc,
            "shell_fully_implemented": True,  # this branch IS fully implemented
        },
    }


def filter_per_candidate_for_mutator_prompt(gate_result: dict[str, Any]) -> dict[str, Any]:
    filtered = {k: v for k, v in gate_result.items() if k != "extra"}
    extra = gate_result.get("extra", {})
    filtered["extra"] = {
        "shell_fully_implemented": extra.get("shell_fully_implemented"),
        "ambiguous_set_size": extra.get("ambiguity_check", {}).get("ambiguous_set_size"),
        "disclosure_passed": extra.get("disclosure_check", {}).get("passed"),
    }
    return filtered
