"""GP-157 v5.0 Phase 4c — orchestrator state-flow primitives.

Per-run state setup that the autoresearch_loop main module currently
constructs inline. Hickey decomplecting: pull the state-construction
helpers behind testable functions so the autoresearch_loop body
shrinks toward a clean orchestration shell.

This module's job is narrow:
  - Cage instance + substrate-view construction from rubric_data
  - mode resolution (observe vs authoritative)

Future migration targets (Phase 4c full, separate commits):
  - score history + stagnation tracking
  - rubric-evolution state
  - usage-bucket snapshots
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Optional, Tuple


@dataclass(frozen=True)
class CageRuntime:
    """Resolved Cage state for a run.

    `instance` is None when Cage is unavailable or rubric did not opt in.
    `substrate_view` mirrors the historic anonymous-class proxy.
    `mode` is one of "off" / "observe" / "authoritative".
    """
    instance: Any  # gates.cage.Cage | None
    substrate_view: Any | None
    mode: str
    cage_meta: Mapping[str, Any]

    @property
    def is_active(self) -> bool:
        return self.instance is not None and self.substrate_view is not None

    @property
    def is_authoritative(self) -> bool:
        return self.mode == "authoritative"

    @property
    def is_observe(self) -> bool:
        return self.mode in ("observe", "authoritative")


def resolve_cage_mode(rubric_data: Mapping[str, Any]) -> str:
    """Return one of "off" / "observe" / "authoritative".

    cage_authoritative_mode wins; cage_observe_mode is implied when
    authoritative is set. Both default False → "off".
    """
    if bool(rubric_data.get("cage_authoritative_mode", False)):
        return "authoritative"
    if bool(rubric_data.get("cage_observe_mode", False)):
        return "observe"
    return "off"


def build_cage_runtime(
    rubric_data: Mapping[str, Any],
    *,
    cage_factory,
    cage_available: bool,
) -> CageRuntime:
    """Construct a CageRuntime from rubric_data.

    `cage_factory`: callable returning a Cage instance (typically
    `get_default_cage` from src.ztare.gates.registry). Injected so this
    module does not import the gate registry at module load.

    `cage_available`: caller's flag indicating Cage import succeeded.
    Mirrors `_V5_CAGE_AVAILABLE` in autoresearch_loop.

    On factory failure, returns a CageRuntime with instance=None and
    mode preserved (caller logs the failure). Never raises — Cage init
    must not abort a run.
    """
    mode = resolve_cage_mode(rubric_data)
    cage_meta = rubric_data.get("cage_meta") or {}

    if mode == "off" or not cage_available:
        return CageRuntime(instance=None, substrate_view=None, mode=mode, cage_meta=cage_meta)

    try:
        instance = cage_factory()
    except Exception:
        return CageRuntime(instance=None, substrate_view=None, mode=mode, cage_meta=cage_meta)

    # GP-157 §3a (2026-04-27): register R10/R11 cross-class gates with the
    # Cage instance. New gates from R10 onward MUST follow the
    # Cage-routed pattern (can_handle predicate + run adapter, no
    # autoresearch_loop direct-wire). This call is the registration
    # point — register_cross_class_gates appends Gate objects to
    # cage.gates and invalidates the topo cache.
    try:
        from src.ztare.gates.cross_class_extrapolation_gate import (
            register_cross_class_gates,
        )
        register_cross_class_gates(instance)
    except Exception:
        pass  # gate registration is best-effort; never abort Cage init

    # GP-170 (2026-04-26): symbolic logic cage. Cage-routed PRE_FIT gate
    # that runs algebraic boundary-condition checks against PARAMETRIC_FORM
    # via SymPy reduction before scipy fits constants. Honors the panel
    # review + Gemini Pro paradox fixes (regex pre-parser fail-closed,
    # AST-rewrite for where/sigmoid, assumption-aware symbol declaration,
    # provenance-required constraints, trivial-wrapping detector,
    # 15s wall-clock budget, data-belief reconciliation, R1 templates).
    try:
        from src.ztare.gates.symbolic_logic_cage import (
            register_symbolic_logic_cage_gate,
        )
        register_symbolic_logic_cage_gate(instance)
    except Exception:
        pass  # gate registration is best-effort; never abort Cage init

    # GP-157 §3a backport (Task #151, 2026-04-26): migrate the four direct-
    # wired diagnostics (substrate_critic, noise_profile, ANALOGY, framer)
    # to the Cage-routed pattern so autoresearch_loop's per-gate if-block
    # stack stops accreting. Each register_r{N}_gate call appends its
    # Gate(s) to instance.gates with the right phase + can_handle + run
    # adapter. Behavior preserved verbatim by adapter contracts.
    try:
        from src.ztare.diagnostics.substrate_critic import register_r13_gate
        register_r13_gate(instance)
    except Exception:
        pass
    try:
        from src.ztare.diagnostics.noise_profile import register_r14_gate
        register_r14_gate(instance)
    except Exception:
        pass
    try:
        from src.ztare.fit.analogy import register_r15_gate
        register_r15_gate(instance)
    except Exception:
        pass
    try:
        from src.ztare.framer.active_framer import register_r16_gate
        register_r16_gate(instance)
    except Exception:
        pass

    # 2026-04-27 — register R20-R23 structural anti-pattern gates
    # (#137 G-WITHHELD-VALUE-LEAKAGE, #139 G-EFFECTIVE-PARAMETER-COUNT,
    # #146 apparatus-meta-runner, #147 sparse-cell exclusion).
    try:
        from src.ztare.gates.structural_anti_pattern_gates import (
            register_structural_anti_pattern_gates,
        )
        register_structural_anti_pattern_gates(instance)
    except Exception:
        pass

    # 2026-05-06 — register R8 + R9 substrate validator gates. Both
    # were authored in v5.0 Phase 3a (gp154-grounded) but never wired
    # — surfaced as dead code by today's cross-audit dashboard. Both
    # opt-in via rubric flags (enable_r8_feature_coverage,
    # enable_r9_target_convention_homogeneity) so registration is
    # zero-risk on existing projects; rubric must explicitly opt in
    # to engage them.
    try:
        from src.ztare.gates.r8_r9_substrate_validators import (
            register_r8_r9_gates,
        )
        register_r8_r9_gates(instance)
    except Exception:
        pass

    # Substrate-view proxy. `meta` is the cage_meta dict the Cage
    # dispatcher reads. `rubric_flags` is the rubric so gates' can_handle
    # predicates can read framer_primary_feature_key, substrate_class_key,
    # enforce_per_class_farther_tail, etc., without coupling each gate
    # to the autoresearch_loop's rubric_data variable.
    class _SubstrateView:
        meta = cage_meta
        rubric_flags = dict(rubric_data)  # snapshot

    return CageRuntime(
        instance=instance,
        substrate_view=_SubstrateView(),
        mode=mode,
        cage_meta=cage_meta,
    )


def cage_init_banner(runtime: CageRuntime) -> Optional[str]:
    """Return the one-line console banner for an active Cage runtime,
    or None when Cage is off / failed.

    Mirrors the historic `🦴 GP-157 v5.0 Cage observe-mode ACTIVE: …`
    line so log readers see the same shape."""
    if not runtime.is_active:
        return None
    label = "AUTHORITATIVE" if runtime.is_authoritative else "observe-mode"
    n_gates = len(getattr(runtime.instance, "gates", {}))
    cls = runtime.cage_meta.get("class", "unset")
    tch = runtime.cage_meta.get("target_convention_homogeneity", "unset")
    return (
        f"🦴 GP-157 v5.0 Cage {label} ACTIVE: {n_gates} gates "
        f"registered; substrate.meta.class={cls}; "
        f"target_convention_homogeneity={tch}. "
        f"Engagement matrix logged to workspace/cage_engagement.jsonl per iter."
    )
