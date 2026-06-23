"""Pre-iter-1 Cage dispatch — extracted from autoresearch_loop.

Part of the pre-iteration modular split. Orchestrator
holds the once-per-run pre-iter-1 hooks. Today: GP-169 cold-LLM Erdős
seed. Future: any other once-before-iter-1 work that today lives
inline in autoresearch_loop.

Contract:
    autoresearch_loop calls dispatch_pre_iter1_cage(ctx) ONCE before
    the iter loop starts. This function reads rubric flags, dispatches
    every registered pre-iter-1 hook, persists artifacts to workspace,
    and returns a verdict the caller logs. The caller is NOT
    responsible for any per-hook plumbing.

Per GP-169 seam §Phase 1 + panel Blindspot 4 (degraded-mode contract):
hard 30s wall-clock budget on the cold-LLM call; on failure or budget
exceeded, iter 1 proceeds with the standard briefing and the seed
adherence rule auto-disables.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class PreIter1Verdict:
    cold_seed_attempted: bool = False
    cold_seed_succeeded: bool = False
    cold_seed_n_valid_candidates: int = 0
    cold_seed_artifact_path: Optional[str] = None
    cold_seed_error: Optional[str] = None
    cold_shot_policy_path: Optional[str] = None
    log_lines: list[str] = field(default_factory=list)


def _compute_anonymized_fingerprint(
    project_dir: Path,
    rubric_data: dict,
) -> Optional[dict]:
    """Build the anonymized residual fingerprint from the substrate.

    Reads features.py + a baseline-fit residual structure if available.
    Returns a dict with the keys the cold_llm_erdos_seed module reads,
    AFTER applying the panel-Blindspot-1 quantization.
    """
    # 2026-04-27 hotfix: qualitative-substrate fallback. Substrates declaring
    # rubric.fit_score_mode='none' or rubric.enable_fit_primitive=false (e.g.
    # gp168 org-topology) have no numerical features.py. Without this, Erdős
    # silent-fails and iter 1 has no cold-domain seed candidates. Return a
    # minimal fingerprint that signals "qualitative; substrate_domain=<X>"
    # so cold_llm_erdos_seed can produce relevant cross-domain candidates.
    is_qualitative = (
        rubric_data.get("fit_score_mode") == "none"
        or not bool(rubric_data.get("enable_fit_primitive", True))
        or rubric_data.get("rubric_mode") == "kepler"
    )
    feat_path = project_dir / "features.py"
    if is_qualitative and not feat_path.exists():
        return {
            "shape": "qualitative",
            "monotonicity": 0.0,
            "regime_break_count": 0,
            "heavy_tail_flag": False,
            "sign_pattern": "n_a",
            "y_dynamic_range_decades": 0.0,
            "n_visible_classes": 1,
            "n_withheld_classes": 0,
            "substrate_domain": rubric_data.get("substrate_domain", "qualitative"),
            "_qualitative_substrate": True,
        }

    try:
        import importlib.util as _ilu
        import sys as _sys
        if not feat_path.exists():
            # qualitative fallback above didn't trip; numerical substrate
            # missing features.py is genuinely broken.
            return None
        spec = _ilu.spec_from_file_location("_pre_iter1_features", str(feat_path))
        if spec is None or spec.loader is None:
            return None
        if str(project_dir) not in _sys.path:
            _sys.path.insert(0, str(project_dir))
        feat_mod = _ilu.module_from_spec(spec)
        spec.loader.exec_module(feat_mod)
    except Exception:
        # Last resort: if substrate is qualitative, return synthetic fingerprint
        # so Erdős still fires with substrate_domain context.
        if is_qualitative:
            return {
                "shape": "qualitative",
                "monotonicity": 0.0,
                "regime_break_count": 0,
                "heavy_tail_flag": False,
                "sign_pattern": "n_a",
                "y_dynamic_range_decades": 0.0,
                "n_visible_classes": 1,
                "n_withheld_classes": 0,
                "substrate_domain": rubric_data.get("substrate_domain", "qualitative"),
                "_qualitative_substrate": True,
            }
        return None

    try:
        visible = list(feat_mod.visible_rows())
        farther = list(feat_mod.farther_tail_rows()) if hasattr(feat_mod, "farther_tail_rows") else []
    except Exception:
        return None

    # Coarse fingerprint signal — quantized inside cold_llm_erdos_seed.
    ys: list[float] = []
    classes: set = set()
    for tup in visible:
        if len(tup) >= 3:
            _id, y, fx = tup[0], tup[1], tup[2]
            try:
                ys.append(float(y))
            except (TypeError, ValueError):
                continue
            cls = fx.get(rubric_data.get("substrate_class_key", ""), None) if isinstance(fx, dict) else None
            if cls is not None:
                classes.add(str(cls))
    withheld_classes: set = set()
    for tup in farther:
        if len(tup) >= 3:
            fx = tup[2]
            cls = fx.get(rubric_data.get("substrate_class_key", ""), None) if isinstance(fx, dict) else None
            if cls is not None:
                withheld_classes.add(str(cls))

    if not ys:
        return None
    import math
    pos = [y for y in ys if y > 0]
    if pos:
        ymin, ymax = min(pos), max(pos)
        decades = math.log10(ymax / ymin) if (ymin > 0 and ymax > ymin) else 0.0
    else:
        decades = 0.0
    sign = "positive_only" if all(y > 0 for y in ys) else (
        "negative_only" if all(y < 0 for y in ys) else "mixed"
    )

    raw_fp = {
        "shape": "monotone_or_unknown",
        "monotonicity": 0.0,
        "regime_break_count": 0,
        "heavy_tail_flag": False,
        "sign_pattern": sign,
        "y_dynamic_range_decades": decades,
        "n_visible_classes": len(classes),
        "n_withheld_classes": len(withheld_classes),
    }
    # Apply Panel-Blindspot-1 quantization
    try:
        from ztare.fit.cold_llm_erdos_seed import quantize_fingerprint
        return quantize_fingerprint(raw_fp)
    except ImportError:
        return raw_fp


def dispatch_pre_iter1_cage(
    *,
    project_dir: Path,
    rubric_data: dict,
    workspace_dir: Optional[Path] = None,
    mutator_model_id: Optional[str] = None,
) -> PreIter1Verdict:
    """Run every registered pre-iter-1 hook. Today: GP-169 cold-LLM seed.

    `mutator_model_id` is the resolved runtime mutator model. When the
    rubric declares ``cold_llm_seed_model_id`` as the sentinel
    ``"@mutator"`` (or leaves it blank), the cold-LLM call uses the
    runtime mutator model — same family as the mutator but a fresh
    context, no shared prior. The operator-curated cross-family choice
    (e.g. claude-opus-4-6 from a gpt-5.5 mutator) is the strict-hygiene
    path; the @mutator default trades cross-family hygiene for cost.
    """
    verdict = PreIter1Verdict()
    workspace_dir = workspace_dir or (project_dir / "workspace")
    workspace_dir.mkdir(parents=True, exist_ok=True)

    _policy = None
    try:
        from ztare.orchestrator.cold_shot_policy import (
            route_cold_shot_families,
            write_policy_artifacts,
        )

        _policy = route_cold_shot_families(
            project=project_dir.name,
            rubric_data=rubric_data,
            lifecycle="pre_iter_1",
        )
        _policy_path = write_policy_artifacts(
            workspace_dir=workspace_dir,
            decision=_policy,
            event="pre_iter_1_policy_decision",
        )
        verdict.cold_shot_policy_path = str(_policy_path)
        verdict.log_lines.append(
            "🧭 cold-shot policy: selected="
            f"{_policy.selected_families or []} saved={_policy_path.name}"
        )
        _de_anchor_selected = _policy.family_selected("de_anchor_seed")
    except Exception as exc:  # noqa: BLE001
        # Policy observability must never block a run. Fall back to the
        # legacy flag so old rubrics keep working if the router fails.
        verdict.log_lines.append(f"🧭 cold-shot policy error (non-fatal): {exc}")
        _de_anchor_selected = bool(rubric_data.get("enable_cold_llm_erdos_seed", False))

    def _dispatch_evidence_cold_shot() -> None:
        # Evidence-grounded cold shot (qualitative_evidence_seed family).
        # Runs independently of the de-anchor seed; a disabled de-anchor route
        # must not suppress other pre-iter-1 hooks selected by policy.
        if _policy is not None:
            _evidence_selected = _policy.family_selected("qualitative_evidence_seed")
        else:
            _evidence_selected = bool(
                rubric_data.get("enable_qualitative_evidence_cold_shot", False)
            )
        if not _evidence_selected:
            return
        try:
            from ztare.orchestrator.qualitative_evidence_cold_shot import (
                run_qualitative_evidence_cold_shot,
            )
            ev_result = run_qualitative_evidence_cold_shot(
                project_dir=project_dir,
                rubric_data=rubric_data,
                workspace_dir=workspace_dir,
                mutator_model_id=mutator_model_id,
                timeout_seconds=float(
                    rubric_data.get("qualitative_evidence_cold_shot_timeout_seconds", 45.0)
                ),
            )
            if ev_result.success:
                verdict.log_lines.append(
                    f"🔎 evidence cold shot: {len(ev_result.candidates)} thesis-family "
                    f"candidates, saved to qualitative_evidence_cold_shot.json"
                )
            else:
                verdict.log_lines.append(
                    f"🔎 evidence cold shot: degraded — {ev_result.error}; "
                    f"iter-1 proceeds without evidence seed"
                )
        except Exception as _ev_exc:
            verdict.log_lines.append(
                f"🔎 evidence cold shot: error (non-fatal) — {_ev_exc}"
            )

    if not _de_anchor_selected:
        _dispatch_evidence_cold_shot()
        return verdict

    verdict.cold_seed_attempted = True

    fingerprint = _compute_anonymized_fingerprint(project_dir, rubric_data)
    if fingerprint is None:
        verdict.cold_seed_error = "could not build anonymized fingerprint from features.py"
        verdict.log_lines.append(f"🔎 GP-169 de-anchor seed: {verdict.cold_seed_error}")
        _dispatch_evidence_cold_shot()
        return verdict

    raw_model_id = str(rubric_data.get("cold_llm_seed_model_id") or "").strip()
    # Resolve the sentinel "@mutator" (or blank) to the runtime mutator
    # model. Operator can still pin a specific cross-family model by
    # writing a literal model id like "claude-opus-4-6".
    if raw_model_id in ("", "@mutator", "mutator"):
        if not mutator_model_id:
            verdict.cold_seed_error = (
                "cold_llm_seed_model_id is '@mutator' (or blank) but no "
                "mutator_model_id supplied at dispatch — autoresearch_loop "
                "must pass MUTATOR_MODEL_ID through"
            )
            verdict.log_lines.append(f"🔎 GP-169 de-anchor seed: {verdict.cold_seed_error}")
            _dispatch_evidence_cold_shot()
            return verdict
        model_id = str(mutator_model_id).strip()
        verdict.log_lines.append(
            f"🔎 GP-169 de-anchor seed: using runtime mutator model '{model_id}' "
            f"(rubric set cold_llm_seed_model_id='@mutator' or blank)"
        )
    else:
        model_id = raw_model_id
    forbidden_domain = rubric_data.get("cold_llm_seed_forbidden_domain")
    k_law_budget = int(rubric_data.get("cold_llm_seed_k_law_budget", 7))
    # Panel-Blindspot-4 fix: hard 30s wall-clock budget (down from default 120s)
    timeout_s = float(rubric_data.get("cold_llm_seed_timeout_seconds", 30.0))

    try:
        from ztare.fit.cold_llm_erdos_seed import (
            query_cold_llm_erdos_seed,
            write_cold_seed_log,
        )
    except ImportError as exc:
        verdict.cold_seed_error = f"cold_llm_erdos_seed module unavailable: {exc}"
        verdict.log_lines.append(f"🔎 GP-169 de-anchor seed: {verdict.cold_seed_error}")
        _dispatch_evidence_cold_shot()
        return verdict

    response = query_cold_llm_erdos_seed(
        fingerprint=fingerprint,
        model_id=model_id,
        forbidden_domain=forbidden_domain,
        k_law_budget=k_law_budget,
        timeout_seconds=timeout_s,
        project_dir=project_dir,
        rubric_data=rubric_data,
    )

    artifact_path = write_cold_seed_log(workspace_dir, response)
    verdict.cold_seed_artifact_path = str(artifact_path)

    n_valid = sum(1 for c in response.candidates if c.valid_python)
    verdict.cold_seed_n_valid_candidates = n_valid

    if response.error:
        verdict.cold_seed_error = response.error
        verdict.log_lines.append(
            f"🔎 GP-169 de-anchor seed: error — {response.error}; iter-1 proceeds "
            f"with standard briefing (degraded-mode contract)."
        )
        _dispatch_evidence_cold_shot()
        return verdict

    verdict.cold_seed_succeeded = n_valid >= 2
    qual_mode = getattr(response, "qualitative_mode", False)
    if qual_mode:
        verdict.log_lines.append(
            f"🔎 GP-169 de-anchor seed (qualitative): {len(response.candidates)} "
            f"argument-structure candidates, fields="
            f"{[c.field_of_origin for c in response.candidates]}, "
            f"saved to {artifact_path.name}"
        )
    else:
        verdict.log_lines.append(
            f"🔎 GP-169 de-anchor seed: {len(response.candidates)} candidates, "
            f"{n_valid} valid Python forms, fields={[c.field_of_origin for c in response.candidates]}, "
            f"saved to {artifact_path.name}"
        )

    _dispatch_evidence_cold_shot()

    return verdict
