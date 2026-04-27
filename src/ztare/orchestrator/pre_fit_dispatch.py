"""Pre-fit Cage dispatch — extracted from autoresearch_loop.

Part of the GP-157 §3a backport (Task #151). New PRE_FIT-phase gates
register through the Cage and dispatch through this single entry-point
rather than accreting inline if-blocks in autoresearch_loop.

Today this dispatches the four backported diagnostics in their PRE_FIT
slots:
  - R13 substrate_critic (preflight, runs ONCE before iter 1)
  - R14 noise_profile (preflight, runs ONCE before iter 1)
  - R16 framer (per-iter, runs before fit primitive engagement)

R13 and R14 also have POST_FIT phases (per-iter refresh / residual
classifier) that dispatch through `post_fit_dispatch.py`.

Contract:
    autoresearch_loop calls `dispatch_preflight_cage(...)` ONCE before
    the iter loop starts (R13 + R14 preflight) and `dispatch_pre_fit_cage(...)`
    once per iter before fit primitive engagement (R16). Each function
    walks the Cage's PRE_FIT gate list, applies can_handle, and calls
    run() for engaged gates. Errors are caught per-gate so a single
    misbehaving adapter cannot abort the iter.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional


@dataclass
class PreFitVerdict:
    """Result of running PRE_FIT-phase Cage gates for one slot."""
    engagements: list[dict] = field(default_factory=list)
    log_lines: list[str] = field(default_factory=list)
    error: Optional[str] = None


def _make_substrate_view(rubric_data: dict) -> Any:
    """Build the same substrate-view proxy build_cage_runtime constructs.

    Used when dispatch is invoked outside the Cage runtime (e.g. when the
    Cage is off but the operator still wants the gates to run via this
    entry point — the gates' can_handle predicates read meta + rubric_flags
    so the proxy is sufficient for adapter calls).
    """
    cage_meta = rubric_data.get("cage_meta") or {}
    return SimpleNamespace(meta=cage_meta, rubric_flags=dict(rubric_data))


def _engage_gates_by_phase_and_name_filter(
    cage_runtime: Any,
    rubric_data: dict,
    candidate: Any,
    *,
    phase: str,
    name_substrings: tuple[str, ...],
) -> tuple[list[dict], list[str]]:
    """Walk the Cage's gates, engage those in `phase` whose name contains
    any of `name_substrings`. Returns (engagements, log_lines).

    Falls back to a substrate proxy when cage_runtime is None / inactive.
    """
    engagements: list[dict] = []
    log_lines: list[str] = []
    if cage_runtime is None or not getattr(cage_runtime, "is_active", False):
        # No live Cage; build a transient proxy and walk via direct adapter
        # imports. Preserves behavior when cage_*_mode rubric flags are off.
        substrate = _make_substrate_view(rubric_data)
        for adapter_name, adapter_fn in _direct_adapters_for(phase, name_substrings):
            ok, reason = _safe_can_handle(adapter_fn["can_handle"], substrate, candidate)
            if not ok:
                continue
            try:
                result = adapter_fn["run"](substrate, candidate)
            except Exception as exc:
                engagements.append({
                    "gate": adapter_name,
                    "engaged": True,
                    "error": f"{type(exc).__name__}: {exc}",
                })
                log_lines.append(f"🦴 {adapter_name} (direct) error: {exc}")
                continue
            engagements.append({
                "gate": adapter_name,
                "engaged": True,
                "result": result,
            })
            _append_log_line(log_lines, adapter_name, result)
        return engagements, log_lines

    instance = cage_runtime.instance
    substrate = cage_runtime.substrate_view
    for name, gate in list(getattr(instance, "gates", {}).items()):
        if getattr(gate, "phase", "") != phase:
            continue
        if not any(sub in name for sub in name_substrings):
            continue
        ok, reason = _safe_can_handle(gate.can_handle, substrate, candidate)
        if not ok:
            engagements.append({
                "gate": name, "engaged": False, "reason": reason,
            })
            continue
        try:
            result = gate.run(substrate, candidate)
        except Exception as exc:
            engagements.append({
                "gate": name,
                "engaged": True,
                "error": f"{type(exc).__name__}: {exc}",
            })
            log_lines.append(f"🦴 {name} error: {exc}")
            continue
        engagements.append({
            "gate": name, "engaged": True, "result": result,
        })
        _append_log_line(log_lines, name, result)
    return engagements, log_lines


def _safe_can_handle(can_handle, substrate, candidate) -> tuple[bool, str]:
    try:
        return can_handle(substrate, candidate)
    except Exception as exc:
        return False, f"can_handle raised: {type(exc).__name__}: {exc}"


def _append_log_line(log_lines: list[str], name: str, result: Any) -> None:
    if not isinstance(result, dict):
        return
    if result.get("skipped"):
        log_lines.append(f"🦴 {name} skipped: {result.get('reason', '')}")
        return
    summary = result.get("summary")
    if summary:
        log_lines.append(f"🦴 {name}: {summary}")
        return
    # Gate-specific compact log shapes
    if "framer_engaged" in result:
        if result["framer_engaged"]:
            log_lines.append(
                f"🪞 {name}: engaged h_in={result.get('h_in')} "
                f"h_out={result.get('h_out')} "
                f"MDL_gain={result.get('MDL_gain_bits', 0):.1f} bits"
            )
        else:
            log_lines.append(
                f"🪞 {name}: disabled ({result.get('disabled_reason')})"
            )
        return
    if "n_candidates" in result:
        log_lines.append(
            f"🔁 {name}: {result['n_candidates']} candidate forms via "
            f"{result.get('model_id')} (tokens in={result.get('tokens_in')} "
            f"out={result.get('tokens_out')})"
        )
        previews = result.get("candidates_preview") or []
        for cf in previews:
            log_lines.append(f"   → {cf}")
        return
    if "n_post_voids" in result:
        if result["n_post_voids"]:
            log_lines.append(
                f"🩺 {name}: {result['n_post_voids']} new post-fit void(s)"
            )
            for v in result.get("post_voids_preview", []):
                log_lines.append(f"🩺   {v}")
        return


def _direct_adapters_for(
    phase: str, name_substrings: tuple[str, ...]
) -> list[tuple[str, dict]]:
    """Return a list of (gate_name, {"can_handle": fn, "run": fn}) for the
    four backported gates. Used as a fallback when the Cage runtime is
    inactive but the operator still wants gate behavior preserved.
    """
    out: list[tuple[str, dict]] = []
    try:
        from src.ztare.diagnostics.substrate_critic import (
            r13_can_handle, r13_run_preflight, r13_run_post_fit,
        )
        if phase == "PRE_FIT" and any(s in "R13_substrate_critic_preflight" for s in name_substrings):
            out.append((
                "R13_substrate_critic_preflight",
                {"can_handle": r13_can_handle, "run": r13_run_preflight},
            ))
        if phase == "POST_FIT" and any(s in "R13_substrate_critic_post_fit" for s in name_substrings):
            out.append((
                "R13_substrate_critic_post_fit",
                {"can_handle": r13_can_handle, "run": r13_run_post_fit},
            ))
    except ImportError:
        pass
    try:
        from src.ztare.diagnostics.noise_profile import (
            r14_can_handle, r14_run_preflight, r14_run_post_fit,
        )
        if phase == "PRE_FIT" and any(s in "R14_noise_profile_preflight" for s in name_substrings):
            out.append((
                "R14_noise_profile_preflight",
                {"can_handle": r14_can_handle, "run": r14_run_preflight},
            ))
        if phase == "POST_FIT" and any(s in "R14_noise_profile_post_fit" for s in name_substrings):
            out.append((
                "R14_noise_profile_post_fit",
                {"can_handle": r14_can_handle, "run": r14_run_post_fit},
            ))
    except ImportError:
        pass
    try:
        from src.ztare.fit.analogy import r15_can_handle, r15_run
        if phase == "POST_FIT" and any(s in "R15_analogy" for s in name_substrings):
            out.append((
                "R15_analogy",
                {"can_handle": r15_can_handle, "run": r15_run},
            ))
    except ImportError:
        pass
    try:
        from src.ztare.framer.active_framer import r16_can_handle, r16_run
        if phase == "PRE_FIT" and any(s in "R16_framer_pre_fit" for s in name_substrings):
            out.append((
                "R16_framer_pre_fit",
                {"can_handle": r16_can_handle, "run": r16_run},
            ))
    except ImportError:
        pass
    return out


def dispatch_preflight_cage(
    *,
    cage_runtime: Any,
    rubric_data: dict,
    project_dir: Path,
    workspace_dir: Path,
    project_name: str = "",
) -> PreFitVerdict:
    """ONCE-per-run preflight dispatch.

    Engages the preflight gates (R13, R14) before iter 1 starts. Reads
    substrate data via project_dir/features.py inside each adapter.
    Persists artifacts to workspace_dir.

    The candidate object exposes the minimal context the preflight
    adapters need: project_dir, workspace_dir, project name, and a
    live_rubric_data reference so noise_profile's auto-route can flip
    flags the operator did not set.
    """
    verdict = PreFitVerdict()
    candidate = SimpleNamespace(
        project_dir=project_dir,
        workspace_dir=workspace_dir,
        project=project_name,
        # noise_profile auto-route writes back to this dict if the key is
        # absent (operator-set flags always win).
        live_rubric_data=rubric_data,
    )
    engagements, log_lines = _engage_gates_by_phase_and_name_filter(
        cage_runtime,
        rubric_data,
        candidate,
        phase="PRE_FIT",
        name_substrings=(
            "R13_substrate_critic_preflight",
            "R14_noise_profile_preflight",
        ),
    )
    verdict.engagements = engagements
    verdict.log_lines = log_lines
    return verdict


def dispatch_pre_fit_cage(
    *,
    cage_runtime: Any,
    rubric_data: dict,
    workspace_dir: Path,
    iter_index: int,
    fit_decl: Any = None,
    fit_required_dimensionality: Optional[int] = None,
    evidence_text: str = "",
) -> PreFitVerdict:
    """PER-ITER pre-fit dispatch — runs before fit primitive engagement.

    Currently engages R16 framer (1D PRE_FIT path). The candidate object
    carries the per-iter context the framer adapter needs: workspace_dir,
    iter_index, fit_decl, evidence_text.

    Returns a verdict the caller logs. Engagement metadata is not used
    to mutate downstream state — the framer ships in OBSERVE mode, so
    only the persisted framing_report.json affects the next iter.
    """
    verdict = PreFitVerdict()
    candidate = SimpleNamespace(
        workspace_dir=workspace_dir,
        iter_index=iter_index,
        fit_decl=fit_decl,
        fit_required_dimensionality=fit_required_dimensionality,
        evidence_text=evidence_text,
    )
    engagements, log_lines = _engage_gates_by_phase_and_name_filter(
        cage_runtime,
        rubric_data,
        candidate,
        phase="PRE_FIT",
        name_substrings=("R16_framer_pre_fit",),
    )
    verdict.engagements = engagements
    verdict.log_lines = log_lines
    return verdict
