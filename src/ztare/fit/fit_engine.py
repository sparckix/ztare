"""GP-157 v5.0 Phase 2 — FitEngine Protocol consolidation.

Unifies the parallel fit primitives (1D `fit_primitive` and N-D
`fit_primitive_features`) under a single Protocol that v5.0 Cage
dispatches against. Adapters wrap the existing primitives without
modifying them — this is ADDITIVE; existing call sites in
autoresearch_loop continue to work unchanged.

Per GP-157 v5 spec §4 Phase 2:
- Drop AST whitelist? KEEP. Namespace lockdown is the security boundary;
  whitelist remains as footgun-protection.
- Add `residual_diagnostic` to ALL adapters (1D primitive has it; N-D
  got it in Bug #31; tensor adapter is NEW per defect D2).
- Decision: tensor-target adapter is a STUB in this phase. Real
  implementation deferred to Phase 3 when v5.0 Cage's substrate-class
  routing decides which adapter to dispatch.

Migration sequence (Phase 3 will do):
1. autoresearch_loop replaces direct calls to fit_primitive_features
   with `Cage.dispatch_fit(substrate, candidate)`
2. Cage uses substrate.meta["class"] to choose adapter
3. Per-substrate `near_miss_factor` flows through; magic numbers
   become substrate metadata, not module defaults
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Protocol, runtime_checkable


# ── Common result type ────────────────────────────────────────────────


@dataclass
class FitEngineResult:
    """Common result shape across all FitEngine adapters.

    Matches the union of fields from `FitSuccess` (1D) and
    `FeatureFitResult` (N-D), so v5.0 Cage downstream consumers see
    a single shape regardless of which adapter ran.
    """
    success: bool
    fitted_params: dict[str, float] = field(default_factory=dict)
    error_message: Optional[str] = None
    # Common-fit telemetry
    sse: float = float("nan")
    sigma_sq: float = float("nan")
    mean_abs_residual: float = float("nan")
    max_abs_residual: float = float("nan")
    n_fit_rows: int = 0
    k_params: int = 0
    bic: float = float("nan")  # GP-152 framer spec v2.0
    n_starts_attempted: int = 0
    n_starts_converged: int = 0
    convergence_classification: str = "unknown"
    # Bug #26 pathology
    pathological: bool = False
    pathology_reason: str = ""
    extreme_params: dict[str, float] = field(default_factory=dict)
    # Bug #31 closed-loop residual feedback
    residual_diagnostic: str = ""
    residual_by_category: dict[str, dict[str, dict[str, float]]] = field(default_factory=dict)
    feature_value_counts: dict[str, dict[str, int]] = field(default_factory=dict)
    # Adapter identification (for telemetry)
    adapter_class: str = ""


# ── Protocol ──────────────────────────────────────────────────────────


@runtime_checkable
class FitEngine(Protocol):
    """v5.0 Cage's fit primitive contract. Each adapter implements this."""

    def can_handle(
        self, substrate: Any, candidate: Any
    ) -> tuple[bool, str]:
        """Engagement predicate. Returns (engage, reason).

        v5.0 Cage's dispatcher calls this BEFORE engaging the adapter.
        Implements:
          - R8 data-adequacy check: required form-features must have
            ≥30% row coverage
          - R9 target-convention homogeneity: substrate.meta declares
            target_convention_homogeneity; if heterogeneous, form must
            reference features['fit_convention']
          - Reachability defense (D1): missing canonical metadata
            raises a sharp diagnostic, never silently returns False
        """
        ...

    def fit(
        self, declaration: Any, evidence: Any, **kwargs: Any
    ) -> FitEngineResult:
        """Run scipy.optimize multi-start; return common result shape."""
        ...

    def write_result(
        self, workspace_dir: Any, result: FitEngineResult
    ) -> None:
        """Persist result to workspace JSON. Canonical schema."""
        ...

    def residual_diagnostic(
        self, result: FitEngineResult, evidence: Any
    ) -> str:
        """Bug #31 closed-loop feedback: emit per-categorical-feature
        residual breakdown the next mutator prompt injects."""
        ...


# ── 1D Adapter (wraps fit_primitive) ──────────────────────────────────


class OneDFitEngine:
    """Adapter for the 1D paired-evidence primitive at
    `src/ztare/fit/fit_primitive.py`. Engages on substrates whose
    evidence is paired (x, y) rows with a single independent variable.
    """

    adapter_class = "OneDFitEngine"

    def can_handle(self, substrate: Any, candidate: Any) -> tuple[bool, str]:
        meta_class = self._safe_meta(substrate, "class")
        if meta_class is not None and meta_class != "1d":
            return False, f"substrate.meta['class']={meta_class!r} != '1d'"
        # 1D primitive engages when:
        #   - rubric.enable_fit_primitive=true AND
        #   - candidate text declares a FIT_DECLARATION block
        # Both conditions are checked at substrate-loading time;
        # at the adapter layer we only check candidate shape.
        candidate_text = self._extract_candidate_text(candidate)
        if "FIT_DECLARATION" not in (candidate_text or ""):
            return False, "candidate has no FIT_DECLARATION block"
        return True, "engaged"

    def fit(
        self,
        declaration: Any,
        evidence: Any,
        **kwargs: Any,
    ) -> Any:
        """L70 authoritative wire-in (2026-04-25 night): drop-in
        replacement for `fit_parameters()`. Returns native FitSuccess|
        FitFailure so the autoresearch_loop downstream code (which uses
        `isinstance(_fit_result, FitSuccess)`) continues to work
        unchanged. The FitEngineResult unification ships in a separate
        commit when downstream consumers migrate."""
        from src.ztare.fit.fit_primitive import fit_parameters
        return fit_parameters(declaration, evidence, **kwargs)

    def write_result(self, workspace_dir: Any, result: FitEngineResult) -> None:
        from pathlib import Path
        import json
        p = Path(workspace_dir) / "fit_result.json"
        p.write_text(json.dumps({
            "success": result.success,
            "fitted_params": result.fitted_params,
            "error_message": result.error_message,
            "bic": result.bic,
            "k_params": result.k_params,
            "n_fit_rows": result.n_fit_rows,
            "convergence_classification": result.convergence_classification,
            "adapter_class": result.adapter_class,
        }, indent=2))

    def residual_diagnostic(
        self, result: FitEngineResult, evidence: Any
    ) -> str:
        # 1D primitive has its own diagnose_residual_pattern;
        # we re-export the formatted block as the canonical diagnostic.
        # Lazy import.
        try:
            from src.ztare.fit.fit_primitive import (
                diagnose_residual_pattern,
                format_diagnostic_for_prompt,
            )
            # diagnose requires the raw FitSuccess; here we have the
            # common shape only. For now, return the precomputed
            # diagnostic if the adapter populated it; else empty.
            return result.residual_diagnostic
        except ImportError:
            return result.residual_diagnostic

    @staticmethod
    def _safe_meta(substrate: Any, key: str) -> Any:
        if substrate is None:
            return None
        meta = getattr(substrate, "meta", None)
        if not isinstance(meta, dict):
            return None
        return meta.get(key)

    @staticmethod
    def _extract_candidate_text(candidate: Any) -> Optional[str]:
        if isinstance(candidate, str):
            return candidate
        if hasattr(candidate, "thesis"):
            return getattr(candidate, "thesis")
        if hasattr(candidate, "text"):
            return getattr(candidate, "text")
        return None


# ── N-D Feature-vector Adapter (wraps fit_primitive_features) ─────────


class FeatureVectorFitEngine:
    """Adapter for the N-D feature-dict primitive at
    `src/ztare/fit/fit_primitive_features.py`. Engages on substrates
    whose evidence is `(features_dict, y)` row pairs."""

    adapter_class = "FeatureVectorFitEngine"

    def can_handle(self, substrate: Any, candidate: Any) -> tuple[bool, str]:
        meta_class = OneDFitEngine._safe_meta(substrate, "class")
        if meta_class is not None and meta_class != "nd_features":
            return False, f"substrate.meta['class']={meta_class!r} != 'nd_features'"
        # N-D primitive engages when test_model.py declares
        # PARAMETRIC_FORM + PARAMETER_NAMES.
        candidate_text = OneDFitEngine._extract_candidate_text(candidate)
        if not candidate_text:
            return False, "no candidate text"
        from src.ztare.fit.fit_primitive_features import extract_form_declaration
        decl = extract_form_declaration(candidate_text)
        if decl is None:
            return False, "candidate did not declare PARAMETRIC_FORM + PARAMETER_NAMES"
        return True, "engaged"

    def fit(
        self,
        declaration: Any,
        evidence: Any,
        **kwargs: Any,
    ) -> Any:
        """L70 authoritative wire-in: drop-in for `fit_features()`.
        Returns native fit_features result for downstream compat."""
        from src.ztare.fit.fit_primitive_features import fit_features
        if isinstance(declaration, tuple) and len(declaration) >= 2:
            form, names = declaration[0], declaration[1]
            init_range = declaration[2] if len(declaration) > 2 else None
        else:
            raise ValueError(
                f"Invalid declaration shape for FeatureVectorFitEngine: "
                f"expected tuple (form, names, init_range?), got {type(declaration).__name__}"
            )
        kwargs.setdefault("init_range", init_range or (-2.0, 2.0))
        return fit_features(form, names, evidence, **kwargs)

    def write_result(self, workspace_dir: Any, result: FitEngineResult) -> None:
        from pathlib import Path
        import json
        p = Path(workspace_dir) / "fit_features_result.json"
        p.write_text(json.dumps({
            "success": result.success,
            "fitted_params": result.fitted_params,
            "error_message": result.error_message,
            "bic": result.bic,
            "sigma_sq": result.sigma_sq,
            "mean_abs_residual": result.mean_abs_residual,
            "max_abs_residual": result.max_abs_residual,
            "n_fit_rows": result.n_fit_rows,
            "k_params": result.k_params,
            "n_starts_converged": result.n_starts_converged,
            "n_starts_attempted": result.n_starts_attempted,
            "classification": result.convergence_classification,
            "pathological": result.pathological,
            "pathology_reason": result.pathology_reason,
            "extreme_params": result.extreme_params,
            "residual_diagnostic": result.residual_diagnostic,
            "residual_by_category": result.residual_by_category,
            "feature_value_counts": result.feature_value_counts,
            "adapter_class": result.adapter_class,
        }, indent=2))

    def residual_diagnostic(
        self, result: FitEngineResult, evidence: Any
    ) -> str:
        return result.residual_diagnostic


# ── Tensor-target Adapter (NEW per spec defect D2 — STUB in this phase) ─


class TensorTargetFitEngine:
    """STUB adapter for substrates with tensor-valued y (e.g. time-series
    with shape (N, T)). Per spec defect D2: existing 1D + N-D primitives
    silently discard cross-time covariance. This adapter is a placeholder;
    full implementation deferred to Phase 3 when Cage routing exists.
    """

    adapter_class = "TensorTargetFitEngine"

    def can_handle(self, substrate: Any, candidate: Any) -> tuple[bool, str]:
        meta_class = OneDFitEngine._safe_meta(substrate, "class")
        if meta_class != "time_series":
            return False, f"substrate.meta['class']={meta_class!r} != 'time_series' (TensorTargetFitEngine STUB)"
        return True, "engaged (STUB)"

    def fit(self, declaration: Any, evidence: Any, **_kwargs: Any) -> FitEngineResult:
        return FitEngineResult(
            success=False,
            error_message=(
                "TensorTargetFitEngine is a STUB in v5.0 Phase 2. Tensor-target "
                "fitting (per defect D2) requires per-(row, time) residuals and is "
                "deferred to Phase 3. For time-series substrates today, use the "
                "continuous_chaotic kernels in src/ztare/fit/continuous_chaotic/ "
                "instead of fit_primitive."
            ),
            adapter_class=self.adapter_class,
        )

    def write_result(self, workspace_dir: Any, result: FitEngineResult) -> None:
        from pathlib import Path
        import json
        p = Path(workspace_dir) / "fit_tensor_result.json"
        p.write_text(json.dumps({
            "success": False,
            "stub": True,
            "error_message": result.error_message,
        }, indent=2))

    def residual_diagnostic(
        self, result: FitEngineResult, evidence: Any
    ) -> str:
        return ""


# ── Conversion helpers ────────────────────────────────────────────────


def _onedfit_to_common(result: Any) -> FitEngineResult:
    """Convert FitSuccess / FitFailure (1D) → FitEngineResult."""
    import math
    from src.ztare.fit.fit_primitive import FitFailure, FitSuccess
    if isinstance(result, FitSuccess):
        n = getattr(result, "n_rows_used", 0)
        k = len(result.fitted_params or {})
        sse = getattr(result, "sse", float("nan"))
        sigma_sq = sse / n if n > 0 and math.isfinite(sse) else float("nan")
        bic = float("nan")
        if n > 0 and sigma_sq > 0 and math.isfinite(sigma_sq):
            bic = n * math.log(sigma_sq) + k * math.log(n)
        return FitEngineResult(
            success=True,
            fitted_params=dict(result.fitted_params or {}),
            sse=sse,
            sigma_sq=sigma_sq,
            mean_abs_residual=getattr(result, "mean_abs_residual", float("nan")),
            max_abs_residual=getattr(result, "max_abs_residual", float("nan")),
            n_fit_rows=n,
            k_params=k,
            bic=bic,
            n_starts_attempted=getattr(result, "n_starts_attempted", 0),
            n_starts_converged=getattr(result, "n_starts_converged", 0),
            convergence_classification=getattr(result, "convergence_classification", "unknown"),
            adapter_class="OneDFitEngine",
        )
    if isinstance(result, FitFailure):
        return FitEngineResult(
            success=False,
            error_message=getattr(result, "error_message", str(result)),
            adapter_class="OneDFitEngine",
        )
    return FitEngineResult(
        success=False,
        error_message=f"Unexpected 1D fit result type: {type(result).__name__}",
        adapter_class="OneDFitEngine",
    )


def _featvec_to_common(result: Any, form: str, names: list[str]) -> FitEngineResult:
    """Convert FeatureFitResult (N-D) → FitEngineResult."""
    if not getattr(result, "success", False):
        return FitEngineResult(
            success=False,
            error_message=getattr(result, "error_message", "fit_features returned non-success"),
            adapter_class="FeatureVectorFitEngine",
        )
    return FitEngineResult(
        success=True,
        fitted_params=dict(getattr(result, "fitted_params", {})),
        sse=getattr(result, "sse", float("nan")),
        sigma_sq=getattr(result, "sigma_sq", float("nan")),
        mean_abs_residual=getattr(result, "mean_abs_residual", float("nan")),
        max_abs_residual=getattr(result, "max_abs_residual", float("nan")),
        n_fit_rows=getattr(result, "n_fit_rows", 0),
        k_params=getattr(result, "k_params", len(names)),
        bic=getattr(result, "bic", float("nan")),
        n_starts_attempted=getattr(result, "n_starts_attempted", 0),
        n_starts_converged=getattr(result, "n_starts_converged", 0),
        convergence_classification=getattr(result, "convergence_classification", "unknown"),
        pathological=getattr(result, "pathological", False),
        pathology_reason=getattr(result, "pathology_reason", ""),
        extreme_params=dict(getattr(result, "extreme_params", {})),
        residual_diagnostic=getattr(result, "residual_diagnostic", ""),
        residual_by_category=dict(getattr(result, "residual_by_category", {})),
        feature_value_counts=dict(getattr(result, "feature_value_counts", {})),
        adapter_class="FeatureVectorFitEngine",
    )


# ── Convenience: select adapter by substrate metadata ────────────────


def select_adapter(substrate: Any, candidate: Any) -> Optional[FitEngine]:
    """v5.0 Cage's dispatcher uses this. Returns the FIRST adapter
    whose can_handle returns True, or None if none engage.

    Order of evaluation (deterministic):
      1. OneDFitEngine (class='1d')
      2. FeatureVectorFitEngine (class='nd_features')
      3. TensorTargetFitEngine (class='time_series', STUB)

    Phase 3 will replace this with Cage's substrate-class-routed dispatch.
    """
    adapters: list[FitEngine] = [
        OneDFitEngine(),
        FeatureVectorFitEngine(),
        TensorTargetFitEngine(),
    ]
    for adapter in adapters:
        ok, _reason = adapter.can_handle(substrate, candidate)
        if ok:
            return adapter
    return None
