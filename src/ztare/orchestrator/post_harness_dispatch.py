"""Post-harness Cage gate dispatch — extracted from autoresearch_loop.

Part of the Phase 4g Torvalds-style split (task #65). The autoresearch
loop's job is to coordinate the iter; gate dispatch logic lives here so
each new Cage-routed gate adds at most a registration line, not an
inline if-block.

Today this dispatches R10 (cross-class extrapolation diagnostic,
non-blocking) and R11 (per-class farther-tail MRE ceiling, hard-fail
when rubric.enforce_per_class_farther_tail). Future post-harness gates
register here without touching autoresearch_loop.

Contract:
    autoresearch_loop calls dispatch_post_harness_cage(ctx) once per iter
    after the holdout gate harness has written gate_harness_result.json.
    The function reads the harness JSON, runs every registered
    post-harness gate, and returns a PostHarnessVerdict the caller embeds
    into new_eval[...] and applies any score-zero / weakest-point
    overrides.

The verdict shape is intentionally narrow: gates that need access to
features.py / harness output / rubric flags use those inputs. Gates that
need richer context get added through the same channel as substrate_critic
when it migrates per task #151.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class PostHarnessVerdict:
    """Result of running all post-harness Cage gates for one iter."""
    score_zero_required: bool = False
    score_zero_reason: str = ""
    weakest_point_addendum: str = ""
    payload: dict = field(default_factory=dict)
    log_lines: list[str] = field(default_factory=list)
    error: Optional[str] = None
    # 2026-04-26 (Gemini-Pro panel rec): defense-in-depth score cap.
    # When R20/R21/R24 detect constant-laundering, the apparatus caps
    # the score deterministically rather than asking the judge to do
    # AST analysis (LLMs are blind to AST topology and get talked out
    # of it by mutator prose). The deterministic cap sits BELOW the
    # judge's score so even a 100-perfect-fit gets ceiled.
    score_cap: Optional[int] = None
    score_cap_reason: str = ""


def dispatch_post_harness_cage(
    *,
    project_dir: Path,
    rubric_data: dict,
    iter_index: int,
) -> PostHarnessVerdict:
    """Run every registered post-harness Cage gate.

    Currently:
        - R10 cross-class extrapolation diagnostic (non-blocking)
        - R11 per-class farther-tail MRE ceiling (hard-fail when opted in)

    Future gates (substrate_critic post-fit refresh, GP-170 symbolic logic
    cage when implemented, GP-168 forced-reframe trigger) register here.
    The autoresearch_loop call site stays a single-line dispatch.
    """
    verdict = PostHarnessVerdict()

    # R10 + R11 — both implemented in cross_class_extrapolation_gate.
    try:
        from src.ztare.gates.cross_class_extrapolation_gate import (
            dispatch_r10_r11_from_harness_json as _r1011_dispatch,
        )
    except ImportError as exc:
        verdict.error = f"R10/R11 module unavailable: {exc}"
        return verdict

    try:
        payload = _r1011_dispatch(
            project_dir=project_dir,
            rubric_data=rubric_data,
            iter_index=iter_index,
        )
    except Exception as exc:
        verdict.error = f"R10/R11 dispatch crashed: {type(exc).__name__}: {exc}"
        return verdict

    verdict.payload["cage_r10_r11"] = payload

    if payload.get("error"):
        verdict.log_lines.append(f"🦴 R10/R11 dispatch note: {payload['error']}")

    if payload.get("r10_engaged"):
        flags = payload.get("r10_flags") or []
        diag = payload.get("r10_diagnostic") or {}
        per_class = diag.get("per_class_mre", {})
        verdict.log_lines.append(
            f"🦴 Cage R10 engaged: per_class_mre={per_class} flags={len(flags)}"
        )
        for flag in flags:
            verdict.log_lines.append(
                f"🦴   R10 flag [{flag.get('kind')}] class={flag.get('class')}"
            )

    if payload.get("r11_engaged"):
        if not payload.get("r11_passed", True):
            failed = payload.get("r11_failed_classes", [])
            per_class = payload.get("r11_per_class_mre", {})
            verdict.log_lines.append(
                f"🚫 Cage R11 hard-fail: per-class MRE ceiling exceeded on "
                f"classes={failed} (per_class_mre={per_class})"
            )
            verdict.score_zero_required = True
            verdict.score_zero_reason = (
                f"Cage R11 per-class MRE ceiling failure on class(es) {failed}"
            )
            verdict.weakest_point_addendum = (
                f"SYSTEM OVERRIDE: Score zeroed due to Cage R11 per-class "
                f"MRE ceiling failure on class(es) {failed}. Combined-class "
                f"farther-tail no longer hides per-class blowups. Refine "
                f"the form so each held-out class independently passes its "
                f"MRE threshold."
            )
        else:
            verdict.log_lines.append(
                f"🦴 Cage R11 engaged + passed: {payload.get('r11_per_class_mre')}"
            )

    # R20-R23 structural anti-pattern gates (#137/#139/#146/#147).
    # Non-blocking by default — flags surface to briefing for next iter.
    # Mutator gets explicit feedback when forms structurally match
    # known Goodhart patterns (RH-13/17/18) without iter-blocking
    # hard-fail (which is reserved for R11 + R12 boundary violation).
    try:
        from src.ztare.gates.structural_anti_pattern_gates import (
            dispatch_structural_anti_pattern_gates as _sapg_dispatch,
        )
        sapg = _sapg_dispatch(
            project_dir=project_dir,
            rubric_data=rubric_data,
            iter_index=iter_index,
        )
        verdict.payload["cage_r20_r23"] = sapg
        for ln in sapg.get("log_lines", []) or []:
            verdict.log_lines.append(ln)
        # Soft penalty: any flag adds a weakest-point addendum. R10/R11
        # remain the hard-fail gates; R20-R23 are diagnostic enrichments
        # that surface structural-pattern findings for the next iter.
        if sapg.get("any_flag"):
            v22 = sapg.get("r22_apparatus_meta_runner") or {}
            v22_matches = v22.get("matches") or []
            v20 = sapg.get("r20_withheld_value_leakage") or {}
            v21 = sapg.get("r21_effective_parameter_count") or {}
            v24 = sapg.get("r24_feature_bump_pattern") or {}

            flagged_codes: list[str] = []
            if v20.get("flagged"):
                flagged_codes.append("R20-WITHHELD-VALUE-LEAKAGE")
            if v21.get("flagged"):
                flagged_codes.append(
                    f"R21-EFFECTIVE-K (declared {v21.get('declared_k')} vs effective {v21.get('effective_k')})"
                )
            if v24.get("flagged"):
                flagged_codes.append("R24-FEATURE-BUMP-PATTERN")
            for m in v22_matches:
                flagged_codes.append(f"R22-{m.get('code','?')}")

            if flagged_codes:
                # Defense-in-depth score cap (Gemini-Pro panel, 2026-04-26).
                # Apparatus-deterministic cap; judge never sees the AST.
                # Default cap = 50; rubric can override via
                # rubric.cage_constant_laundering_score_cap.
                cap = int(rubric_data.get("cage_constant_laundering_score_cap", 50))
                verdict.score_cap = cap
                verdict.score_cap_reason = (
                    f"Cage structural detectors flagged constant-laundering / "
                    f"kernel-camouflage / effective-K mismatch: {flagged_codes}. "
                    f"Apparatus-deterministic cap at {cap} per "
                    f"rubric.cage_constant_laundering_score_cap; the form's "
                    f"hardcoded literals are structural degrees of freedom that "
                    f"must be declared as fitted parameters or derived from the "
                    f"thesis. See workspace/structural_anti_pattern_iter_*.json "
                    f"for the literal-by-literal verdict."
                )
                soft_msg = (
                    f"Cage flagged: {', '.join(flagged_codes)}. Score capped at "
                    f"{cap} (apparatus-deterministic). The judge's qualitative "
                    f"score sits within [0, {cap}] regardless of fit quality "
                    f"because the form embeds {len((v21 or {}).get('load_bearing_constants') or [])} "
                    f"chosen literals as hidden parameters."
                )
                existing = verdict.weakest_point_addendum or ""
                verdict.weakest_point_addendum = (
                    f"{existing}\n\n⚠️  {soft_msg}" if existing else f"⚠️  {soft_msg}"
                )
    except ImportError:
        pass
    except Exception as exc:
        verdict.log_lines.append(
            f"🦴 R20-R23 dispatch error (non-fatal): {type(exc).__name__}: {exc}"
        )

    return verdict


def apply_verdict_to_eval(verdict: PostHarnessVerdict, new_eval: dict) -> None:
    """Apply a PostHarnessVerdict to the iter's `new_eval` dict in place.

    Mutates: new_eval["score"], new_eval["weakest_point"], new_eval["cage_r10_r11"],
    new_eval["cage_r20_r23"], new_eval["score_cap_applied"].

    Score handling, in priority order:
      1. score_zero_required (R11 hard-fail) → score = 0
      2. score_cap (R20/R21/R24 constant-laundering) → score = min(judge_score, cap)
      3. otherwise: judge score preserved

    Caller is responsible for printing verdict.log_lines.
    """
    new_eval.update(verdict.payload)
    if verdict.score_zero_required:
        new_eval["score"] = 0
        original = new_eval.get("weakest_point", "") or ""
        if verdict.weakest_point_addendum:
            new_eval["weakest_point"] = (
                f"{original}\n\n🚫 {verdict.weakest_point_addendum}"
                if original
                else f"🚫 {verdict.weakest_point_addendum}"
            )
        return

    # Defense-in-depth score cap (R20/R21/R24 flag → cap deterministically).
    # Apply only when judge score exceeds the cap; below-cap scores are
    # left alone (judge's pessimism is preserved).
    if verdict.score_cap is not None:
        try:
            judge_score = int(new_eval.get("score", 0) or 0)
        except (TypeError, ValueError):
            judge_score = 0
        cap = int(verdict.score_cap)
        if judge_score > cap:
            new_eval["score"] = cap
            new_eval["score_cap_applied"] = {
                "original_judge_score": judge_score,
                "capped_to": cap,
                "reason": verdict.score_cap_reason,
            }
        else:
            new_eval["score_cap_applied"] = {
                "original_judge_score": judge_score,
                "capped_to": judge_score,
                "reason": "cap_inactive_judge_score_already_below_cap",
            }
        original = new_eval.get("weakest_point", "") or ""
        if verdict.weakest_point_addendum:
            new_eval["weakest_point"] = (
                f"{original}\n\n⚠️  {verdict.weakest_point_addendum}"
                if original
                else f"⚠️  {verdict.weakest_point_addendum}"
            )
