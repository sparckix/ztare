"""GP-157 v5.0 Phase 3 — Cage Orchestrator dispatcher.

Single source of truth for `(substrate × gate)` engagement decisions.
Replaces the implicit/scattered dispatch logic that today lives across
`autoresearch_loop.py`'s ~6,200 lines (rubric flag checks, nested
`if rubric_data.get(...)` branches, per-substrate file-write logic).

Per GP-157 v5 spec §4 Phase 3, this module is ADDITIVE: autoresearch_loop
is NOT modified in this commit. Cage exists alongside the existing
dispatch and can be opted-in per substrate or per gate. Migration plan
in spec §6.

Defects this module closes (from gp158 audit champion + nuggets):

  D1 — Reachability gap in dispatcher: `can_handle_with_diagnostic`
       raises on missing canonical metadata, never silently returns False.
  D6 — Compositional deadlock: explicit dependency DAG (Gate.dependencies)
       drives topological-sorted dispatch; not alphabetical concurrent.
  N2 — Dispatcher ordering non-determinism: topological sort over
       declared dependencies; deterministic order.
  N3 — substrate.meta __getitem__ override: strict isinstance(..., dict)
       check at dispatch time; refuses ChainMap/UserDict subclasses.
  N4 — `min_rows_per_category` substrate metadata: data-adequacy gate
       reads substrate.meta and refuses engagement if violated.
  R8 — Feature-coverage adequacy: every feature key the form references
       must have ≥30% row coverage on visible.
  R9 — Target-convention homogeneity: substrate.meta declares
       target_convention_homogeneity; if heterogeneous, form must
       reference features['fit_convention'].

Anti-overfitting rule (spec §5): every magic number in this module is
substrate-metadata-overridable, never module-default-only. The K_law=5
sycophancy-loop precedent is the calibration; do not repeat.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Optional


# ── Required substrate metadata schema ────────────────────────────────


REQUIRED_SUBSTRATE_META_KEYS: tuple[str, ...] = (
    "type",                              # was "kind" — D1 fix
    "class",                             # 1d / nd_features / time_series / audit / literature
    "target_convention_homogeneity",     # R9
    "min_rows_per_category",             # N4
    "near_miss_factor",                  # D3 (per-substrate, not module-default)
    "frame_invariant_y",                 # whether y is dimensionally consistent
)

VALID_SUBSTRATE_CLASSES: frozenset[str] = frozenset({
    "1d", "nd_features", "time_series", "audit", "literature",
    # Panel-added classes (2026-04-25 night gp158 audit synthesis):
    "proof_target",            # Lean / formal-proof substrates (GP-122, GP-139)
    "closed_form_constant",    # PSLQ integer-relation discovery (GP-145)
    "time_series_chaotic",     # subset of time_series with chaotic dynamics (Wasserstein-persistence)
})

VALID_HOMOGENEITY: frozenset[str] = frozenset({
    "homogeneous", "heterogeneous",
})


def validate_substrate_meta(meta: Any) -> tuple[bool, list[str]]:
    """Per spec §3, every substrate must declare the canonical meta
    fields. Returns (is_valid, missing_or_invalid_diagnostics).

    Used by `scripts/generate_substrate.py` schema validator (§8.3) and
    by Cage.dispatch when refusing engagement on unmigrated substrates.
    """
    diagnostics: list[str] = []
    if not isinstance(meta, dict):
        return False, [f"substrate.meta must be a dict, got {type(meta).__name__}"]
    # N3 nugget: refuse dict subclasses to avoid __getitem__ override surprises.
    if type(meta) is not dict:
        diagnostics.append(
            f"substrate.meta must be a plain dict (got {type(meta).__name__}); "
            f"dict subclasses (ChainMap, UserDict, etc.) can override __getitem__ "
            f"and break dispatcher routing — N3 nugget defense."
        )
    for key in REQUIRED_SUBSTRATE_META_KEYS:
        if key not in meta:
            diagnostics.append(f"missing required key '{key}'")
    # Type / value checks for the keys that ARE present
    cls = meta.get("class")
    if cls is not None and cls not in VALID_SUBSTRATE_CLASSES:
        diagnostics.append(
            f"substrate.meta['class']={cls!r} not in {sorted(VALID_SUBSTRATE_CLASSES)}"
        )
    hom = meta.get("target_convention_homogeneity")
    if hom is not None and hom not in VALID_HOMOGENEITY:
        diagnostics.append(
            f"substrate.meta['target_convention_homogeneity']={hom!r} not in "
            f"{sorted(VALID_HOMOGENEITY)}"
        )
    minrows = meta.get("min_rows_per_category")
    if minrows is not None and not isinstance(minrows, int):
        diagnostics.append(
            f"substrate.meta['min_rows_per_category']={minrows!r} must be int"
        )
    nmf = meta.get("near_miss_factor")
    if nmf is not None and not isinstance(nmf, (int, float)):
        diagnostics.append(
            f"substrate.meta['near_miss_factor']={nmf!r} must be numeric"
        )
    fiy = meta.get("frame_invariant_y")
    if fiy is not None and not isinstance(fiy, bool):
        diagnostics.append(
            f"substrate.meta['frame_invariant_y']={fiy!r} must be bool"
        )
    return (not diagnostics), diagnostics


# ── Gate definition ──────────────────────────────────────────────────


@dataclass
class Gate:
    """A v5.0 gate. Subsumes today's per-rubric-flag dispatch logic.

    `phase` controls when in the iter the gate runs. v5.0 phases:
      - SUBSTRATE_VALIDATE: pre-iter; validates substrate.meta
      - PRE_FIT: before fit primitive; data-adequacy + form-feature check
      - FIT: the fit primitive itself (FitEngine adapter)
      - POST_FIT: after fit; pathology check, residual diagnostic injection
      - PRE_JUDGE: before judge; gate harness MRE, near-miss, etc.
      - POST_JUDGE: after judge; structural blocker gates (G-CIRC, G-FALSIFY)

    `dependencies` declares which gates MUST run before this one. Cage
    topologically sorts the gate list using this DAG (N2 fix).
    """
    name: str
    phase: str
    can_handle: Callable[[Any, Any], tuple[bool, str]]
    run: Callable[[Any, Any], Any]
    dependencies: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        valid_phases = {
            "SUBSTRATE_VALIDATE", "PRE_FIT", "FIT", "POST_FIT",
            "PRE_JUDGE", "POST_JUDGE",
        }
        if self.phase not in valid_phases:
            raise ValueError(
                f"Gate.phase={self.phase!r} not in {sorted(valid_phases)}"
            )


# ── R8: feature-coverage adequacy ─────────────────────────────────────


def check_feature_coverage_adequacy(
    referenced_keys: set[str],
    visible_rows: list[tuple[Any, ...]],
    *,
    min_coverage_fraction: float = 0.30,
) -> tuple[bool, str]:
    """Per R8: every feature key the form references must have ≥30%
    row coverage on visible (non-None values). Returns (ok, diagnostic).

    Closes the gp154 substrate-construction failure where log10_N_params
    was None on every row, making Gemini's terminal sigmoid form
    impossible to fit. Cage's PRE_FIT gate runs this BEFORE engaging
    the FitEngine.
    """
    if not visible_rows:
        return False, "no visible rows to check coverage against"
    n = len(visible_rows)
    coverage: dict[str, int] = {k: 0 for k in referenced_keys}
    for row in visible_rows:
        # Row shape is typically (id, y, features_dict) or (features_dict, y)
        feats = None
        if len(row) >= 3 and isinstance(row[2], dict):
            feats = row[2]
        elif len(row) >= 2 and isinstance(row[0], dict):
            feats = row[0]
        if not isinstance(feats, dict):
            continue
        for k in referenced_keys:
            v = feats.get(k)
            if v is not None:
                coverage[k] += 1
    failing = []
    for k, cnt in coverage.items():
        frac = cnt / n
        if frac < min_coverage_fraction:
            failing.append(f"'{k}': {cnt}/{n}={frac:.1%}")
    if failing:
        return False, (
            f"R8 feature-coverage adequacy FAILED: "
            f"required features have <{min_coverage_fraction:.0%} coverage on visible: "
            f"{', '.join(failing)}. The form cannot be fit when the data the form "
            f"references is not present. Either populate the substrate, or remove "
            f"the missing-feature reference from PARAMETRIC_FORM."
        )
    return True, f"R8 ok: all referenced features ≥{min_coverage_fraction:.0%} coverage"


# ── R9: target-convention homogeneity ─────────────────────────────────


def check_target_convention_homogeneity(
    substrate: Any,
    visible_rows: list[tuple[Any, ...]],
    parametric_form: Optional[str],
) -> tuple[bool, str]:
    """Per R9 (Class K, gp154-grounded): substrate.meta declares
    target_convention_homogeneity. If heterogeneous, the form MUST
    reference `features['fit_convention']` for convention-correction.
    Otherwise no closed-form law can hold across non-commensurable y.
    """
    meta = getattr(substrate, "meta", None)
    if not isinstance(meta, dict):
        return False, "R9 check failed: substrate has no meta dict"
    hom = meta.get("target_convention_homogeneity")
    if hom is None:
        return False, (
            "R9 FAILED: substrate.meta missing 'target_convention_homogeneity'. "
            "Substrate constructor MUST declare whether y values share a single "
            "fit_convention ('homogeneous') or mix conventions ('heterogeneous'). "
            "See gp154/Class K finding: pooling Kaplan-α + Chinchilla-isoFLOP-a + "
            "Bahri-α produces non-commensurable y values no closed-form law can "
            "fit. Generate-substrate validator should refuse to ship without this."
        )
    if hom == "homogeneous":
        # All visible rows must share fit_convention (if the field exists)
        seen: set = set()
        for row in visible_rows:
            feats = row[2] if len(row) >= 3 and isinstance(row[2], dict) else (
                row[0] if len(row) >= 2 and isinstance(row[0], dict) else None
            )
            if isinstance(feats, dict):
                fc = feats.get("fit_convention")
                if fc is not None:
                    seen.add(fc)
        if len(seen) > 1:
            return False, (
                f"R9 FAILED: substrate declared homogeneous but visible rows span "
                f"{len(seen)} fit_conventions: {sorted(seen)}. Either re-declare "
                f"as heterogeneous, or filter the substrate to a single convention."
            )
        return True, f"R9 ok: homogeneous; all rows share fit_convention"
    elif hom == "heterogeneous":
        if not parametric_form:
            return False, (
                "R9 FAILED: substrate is heterogeneous but no PARAMETRIC_FORM "
                "provided to check for fit_convention reference."
            )
        if "features['fit_convention']" not in parametric_form and \
                'features["fit_convention"]' not in parametric_form:
            return False, (
                "R9 FAILED: substrate is heterogeneous but PARAMETRIC_FORM does NOT "
                "reference features['fit_convention']. Heterogeneous substrates pool "
                "non-commensurable y values across fit_conventions; the form must "
                "include a per-convention scalar correction term, or no closed-form "
                "law can fit. See gp154/Class K finding."
            )
        return True, "R9 ok: heterogeneous; form references fit_convention"
    else:
        return False, f"R9 FAILED: unknown target_convention_homogeneity={hom!r}"


# ── N4: min_rows_per_category check ──────────────────────────────────


def check_min_rows_per_category(
    substrate: Any,
    visible_rows: list[tuple[Any, ...]],
) -> tuple[bool, str]:
    """Per N4 nugget: substrate.meta.min_rows_per_category sets the
    minimum row count per categorical-feature value below which Cage
    refuses engagement. Defends against the gp154 Class F failure
    pattern (sparse n=1 categories pulling fits to extreme values).
    """
    meta = getattr(substrate, "meta", None) or {}
    min_rows = meta.get("min_rows_per_category", 3)
    if not isinstance(min_rows, int) or min_rows <= 0:
        min_rows = 3  # safe default
    counts: dict[str, dict[str, int]] = {}
    for row in visible_rows:
        feats = row[2] if len(row) >= 3 and isinstance(row[2], dict) else (
            row[0] if len(row) >= 2 and isinstance(row[0], dict) else None
        )
        if not isinstance(feats, dict):
            continue
        for k, v in feats.items():
            if isinstance(v, str):
                counts.setdefault(k, {})
                counts[k][v] = counts[k].get(v, 0) + 1
    sparse = []
    for k, vc in counts.items():
        for v, c in vc.items():
            if c < min_rows:
                sparse.append(f"{k}='{v}' (n={c} < {min_rows})")
    if sparse:
        # NOT a hard fail; emit warning. v5.0 makes this a Cage-level
        # advisory unless substrate.meta sets enforce_min_rows=True.
        enforce = bool(meta.get("enforce_min_rows", False))
        diag = (
            f"N4 sparse-category warning: {len(sparse)} categorical values below "
            f"min_rows={min_rows}: {sparse[:5]}{' …' if len(sparse) > 5 else ''}"
        )
        if enforce:
            return False, f"N4 ENFORCE FAILED: {diag}"
        return True, f"{diag} (advisory; set substrate.meta.enforce_min_rows=true to enforce)"
    return True, f"N4 ok: all categorical values have ≥{min_rows} rows"


# ── Cage Orchestrator ────────────────────────────────────────────────


@dataclass
class EngagementMatrix:
    """Result of Cage.dispatch: per-gate engagement decision + diagnostic."""
    engagements: dict[str, tuple[bool, str]] = field(default_factory=dict)
    topo_order: list[str] = field(default_factory=list)
    substrate_meta_valid: bool = True
    substrate_meta_diagnostics: list[str] = field(default_factory=list)


class Cage:
    """Substrate-agnostic gate dispatcher (v5.0).

    Holds an immutable list of Gates declared at construction. Every
    call to `dispatch(substrate, candidate)` returns an EngagementMatrix
    describing which gates engaged, in topological-sort order over
    declared dependencies (N2 fix).
    """

    def __init__(self, gates: list[Gate]):
        self.gates: dict[str, Gate] = {g.name: g for g in gates}
        if len(self.gates) != len(gates):
            names = [g.name for g in gates]
            duplicates = [n for n in names if names.count(n) > 1]
            raise ValueError(f"Duplicate gate names: {sorted(set(duplicates))}")
        self._topo_cache: Optional[list[str]] = None

    def topo_order(self) -> list[str]:
        """Topological sort of gates by dependency. Per N2 fix:
        deterministic order, not alphabetical-concurrent."""
        if self._topo_cache is not None:
            return self._topo_cache
        order: list[str] = []
        visited: set[str] = set()
        in_progress: set[str] = set()

        def visit(name: str) -> None:
            if name in visited:
                return
            if name in in_progress:
                raise ValueError(
                    f"Gate dependency cycle detected at {name!r}; cycle: {in_progress}"
                )
            in_progress.add(name)
            gate = self.gates.get(name)
            if gate is not None:
                for dep in sorted(gate.dependencies):
                    if dep not in self.gates:
                        # Missing dep is non-fatal; just skip (caller may
                        # have set up partial Cage for testing).
                        continue
                    visit(dep)
            in_progress.discard(name)
            visited.add(name)
            order.append(name)

        for name in sorted(self.gates):
            visit(name)
        self._topo_cache = order
        return order

    def can_handle_with_diagnostic(
        self, gate_name: str, substrate: Any, candidate: Any
    ) -> tuple[bool, str]:
        """Per defect D1 fix: NEVER silently return False.

        - If substrate.meta is missing required keys → raise ValueError
          with sharp diagnostic (vs Bug #11 silent skip).
        - If gate.can_handle returns False → return (False, reason)
          with a non-empty reason string.
        """
        if gate_name not in self.gates:
            raise ValueError(f"Unknown gate {gate_name!r}")
        gate = self.gates[gate_name]
        # Validate substrate.meta — D1 fix
        meta_ok, meta_diag = validate_substrate_meta(getattr(substrate, "meta", None))
        if not meta_ok:
            raise ValueError(
                f"Cage refuses to engage gate {gate_name!r}: substrate.meta failed "
                f"v5.0 schema validation. Diagnostics: {meta_diag}. "
                f"Per spec §3 R-rules + spec §8.3 substrate-validator, every "
                f"substrate MUST declare the canonical metadata."
            )
        ok, reason = gate.can_handle(substrate, candidate)
        if not isinstance(reason, str) or not reason:
            reason = f"(adapter returned empty reason for can_handle={ok})"
        return ok, reason

    def dispatch(self, substrate: Any, candidate: Any) -> EngagementMatrix:
        """Run can_handle on every gate in topo order; return matrix.

        Does NOT execute the gates. Caller iterates the engagements
        and invokes `gate.run(substrate, candidate)` for engaged ones,
        or uses `dispatch_and_run` to do both in one call.
        """
        em = EngagementMatrix()
        em.topo_order = self.topo_order()
        # First validate substrate.meta once.
        meta_ok, meta_diag = validate_substrate_meta(getattr(substrate, "meta", None))
        em.substrate_meta_valid = meta_ok
        em.substrate_meta_diagnostics = meta_diag
        if not meta_ok:
            # Refuse engagement on every gate when meta is invalid.
            for name in em.topo_order:
                em.engagements[name] = (False, f"substrate.meta invalid: {meta_diag}")
            return em
        for name in em.topo_order:
            gate = self.gates[name]
            try:
                ok, reason = gate.can_handle(substrate, candidate)
                if not isinstance(reason, str) or not reason:
                    reason = f"(can_handle returned empty reason for ok={ok})"
                em.engagements[name] = (ok, reason)
            except Exception as exc:  # noqa: BLE001
                em.engagements[name] = (False, f"can_handle raised {type(exc).__name__}: {exc}")
        return em

    def dispatch_and_run(
        self, substrate: Any, candidate: Any
    ) -> tuple[EngagementMatrix, dict[str, Any]]:
        """Phase 3c authoritative dispatch (GP-157 v5.0 — 2026-04-25 night).

        Computes the engagement matrix (same as `dispatch`), then for each
        gate that engaged, invokes `gate.run(substrate, candidate)` and
        collects the result keyed by gate name. Run failures are caught
        per-gate and recorded in the run_results dict as
        `{"__error__": "<type>: <msg>"}` so one bad gate does not abort
        the rest of the topo order.

        Returns (engagement_matrix, run_results). Engaged gates whose run
        succeeded contribute the function's return value; engaged gates
        whose run raised contribute an `__error__` entry; gates that
        did not engage are absent from run_results.

        Today most registered gates have stub run callbacks (per
        `src/ztare/gates/registry.py`) that return engagement-recorded
        sentinels. As individual gates migrate from stubs to real
        implementations, this method automatically routes them.
        """
        em = self.dispatch(substrate, candidate)
        run_results: dict[str, Any] = {}
        if not em.substrate_meta_valid:
            return em, run_results
        for name in em.topo_order:
            engaged, _reason = em.engagements.get(name, (False, ""))
            if not engaged:
                continue
            gate = self.gates[name]
            try:
                run_results[name] = gate.run(substrate, candidate)
            except Exception as exc:  # noqa: BLE001
                run_results[name] = {"__error__": f"{type(exc).__name__}: {exc}"}
        return em, run_results
