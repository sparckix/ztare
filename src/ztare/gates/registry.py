"""GP-157 v5.0 Phase 3a — gate registry.

Single source of truth for which gates participate in v5.0 Cage's
dispatch. Replaces the scattered conditional-import dispatch in
autoresearch_loop.py (~14 sites) with a single Cage built from this
registry.

Per spec §4 Phase 3a + Class L finding: every gate that exists in
src/ztare/gates/ either WIRES into this registry OR has a documented
RETIRE rationale in DECISION_LOG.md. No gate stays "built but dark."

This module is ADDITIVE: importing it does not modify autoresearch_loop;
the migration to use `get_default_cage()` happens in Phase 3b.

Per the Software-Integration-Engineer rule (R7): each gate's `run`
callback is a thin lazy-import wrapper. Heavy module loading is
deferred until the gate actually engages. This keeps Cage construction
cheap and avoids import-time side effects from inactive gates.
"""
from __future__ import annotations

from typing import Any, Callable, Optional

from ztare.gates.cage import Cage, Gate


# ── Per-substrate-class engagement predicates ────────────────────────


def _meta_class(substrate: Any) -> Optional[str]:
    meta = getattr(substrate, "meta", None)
    if not isinstance(meta, dict):
        return None
    return meta.get("class")


def _engages_on(*classes: str) -> Callable[[Any, Any], tuple[bool, str]]:
    """Build a can_handle predicate that engages when substrate.meta['class']
    is in the allowed set."""
    allowed = frozenset(classes)
    label = "/".join(sorted(classes))

    def can_handle(substrate: Any, _candidate: Any) -> tuple[bool, str]:
        cls = _meta_class(substrate)
        if cls is None:
            return False, f"substrate.meta['class'] missing; gate requires {label}"
        if cls in allowed:
            return True, f"engaged on substrate.meta['class']={cls!r}"
        return False, f"substrate.meta['class']={cls!r} not in {{{label}}}"

    return can_handle


def _engages_universally() -> Callable[[Any, Any], tuple[bool, str]]:
    def can_handle(_s: Any, _c: Any) -> tuple[bool, str]:
        return True, "universal gate"
    return can_handle


def _engages_universally_when_flag(flag_key: str) -> Callable[[Any, Any], tuple[bool, str]]:
    def can_handle(substrate: Any, _candidate: Any) -> tuple[bool, str]:
        rubric = getattr(substrate, "rubric_flags", None)
        if not isinstance(rubric, dict):
            rubric = getattr(substrate, "rubric_data", None)
        if not isinstance(rubric, dict):
            rubric = getattr(substrate, "rubric", None)
        if not isinstance(rubric, dict):
            return False, f"gate requires rubric flag {flag_key!r}; no rubric on substrate"
        if not rubric.get(flag_key, False):
            return False, f"rubric flag {flag_key!r} is not true"
        return True, f"engaged with rubric {flag_key}=True"
    return can_handle


def _g_circ_structural_can_handle(substrate: Any, candidate: Any) -> tuple[bool, str]:
    """Engagement predicate for the upgraded structural G-CIRC gate.

    Engages when `rubric.enable_g_circ_structural=True`. Default-off
    preserves the legacy DAG-cycle G-CIRC (`circularity_gate.py`) as
    the sole circularity defense for substrates that have not yet
    opted in.

    Lazy-imports the predicate from `src.ztare.gates.g_circ` so that
    Cage construction does not pay the sympy import cost when the gate
    is dormant.
    """
    from ztare.gates.g_circ import can_handle as _ch
    return _ch(substrate, candidate)


def _engages_on_when_flag(
    *classes: str, flag_key: str
) -> Callable[[Any, Any], tuple[bool, str]]:
    """Engage when substrate.meta['class'] is in `classes` AND the rubric
    sets `flag_key` to a truthy value. Used for Cage-routed apparatus
    gates that should fire only on substrates explicitly opting in
    (e.g. modified-gravity PPN gates that don't apply to OEIS or
    queueing substrates).
    """
    allowed = frozenset(classes)
    label = "/".join(sorted(classes))

    def can_handle(substrate: Any, _candidate: Any) -> tuple[bool, str]:
        cls = _meta_class(substrate)
        if cls is None:
            return False, f"substrate.meta['class'] missing; gate requires {label}"
        if cls not in allowed:
            return False, f"substrate.meta['class']={cls!r} not in {{{label}}}"
        rubric = getattr(substrate, "rubric_flags", None)
        if not isinstance(rubric, dict):
            rubric = getattr(substrate, "rubric_data", None)
        if not isinstance(rubric, dict):
            rubric = getattr(substrate, "rubric", None)
        if not isinstance(rubric, dict):
            return False, f"gate requires rubric flag {flag_key!r}; no rubric on substrate"
        if not rubric.get(flag_key, False):
            return False, f"rubric flag {flag_key!r} is not true"
        return True, f"engaged on substrate.meta['class']={cls!r} with rubric {flag_key}=True"

    return can_handle


# ── Lazy run-callback factory ────────────────────────────────────────


def _make_run_callback(module_path: str, function_name: str) -> Callable[[Any, Any], Any]:
    """Lazy-import the gate's main function only when the gate engages.

    Avoids import-time side effects from inactive gates, and prevents
    Cage construction from triggering 17 module loads at startup.

    The returned callback signature is (substrate, candidate) → Any.
    Each gate's actual function may take different args — this stub
    captures the "engagement happens here" event; full arg-marshalling
    happens in Phase 3b when autoresearch_loop wires real data.
    """
    def run(substrate: Any, candidate: Any) -> Any:
        # Defer full integration to Phase 3b — for now, return a
        # placeholder signaling "would-have-run" so smoke tests can
        # verify engagement reachability without executing gate logic
        # against incomplete fixtures.
        return {
            "_gate_engagement_recorded": True,
            "_module": module_path,
            "_function": function_name,
            "_substrate_class": _meta_class(substrate),
        }
    return run


# ── Gate definitions ──────────────────────────────────────────────────


# Substrate classes (matches v5.0 spec §3 substrate taxonomy):
#   1d              — paired (x, y) curve fit
#   nd_features     — feature_dict-based predictor
#   time_series     — trajectory / chaotic time series
#   audit           — meta-audit (gp156, gp158)
#   literature      — text-based research review
#   proof_target    — Lean / formal-proof substrate (GP-122 / GP-139)
#   closed_form_constant — PSLQ-style integer-relation discovery (GP-145)


def _build_gates() -> list[Gate]:
    return [
        # ── Universal gates (run on every substrate) ─────────────────
        # bridge_scope_contract: RETIRED per panel synthesis 2026-04-25.
        # Three perspectives (Chaos, Physics, Mathematician) flagged the
        # forbidden-marker blacklist as brittle code-smell with no v5.0
        # signal. Module remains importable; revive when bridge-discovery
        # campaigns return. See DECISION_LOG.md for retire rationale.
        Gate(
            name="semantic_gate_stabilization",
            phase="POST_JUDGE",
            can_handle=_engages_universally(),
            run=_make_run_callback("src.ztare.gates.semantic_gate_stabilization", "diagnose_unresolved"),
            dependencies=[],
        ),
        Gate(
            name="circularity",  # G-CIRC (already LIVE — registered for completeness)
            phase="POST_FIT",
            can_handle=_engages_universally(),
            run=_make_run_callback("src.ztare.gates.circularity_gate", "evaluate_circularity"),
            dependencies=[],
        ),
        # G-CIRC structural — 3-part Lagrangian-smuggling detector
        # (AST symbol scan / Sacred-DNA literal scan / on-shell
        # substitution audit). Default-off via rubric flag
        # enable_g_circ_structural; gp163d's rubric will opt in. See
        # src/ztare/gates/g_circ.py for the threat model.
        Gate(
            name="g_circ_structural",
            phase="POST_FIT",
            can_handle=_g_circ_structural_can_handle,
            run=_make_run_callback("src.ztare.gates.g_circ", "run_gate"),
            dependencies=["circularity"],
        ),
        Gate(
            name="falsifiability",  # G-FALSIFY (already LIVE)
            phase="POST_FIT",
            can_handle=_engages_universally(),
            run=_make_run_callback("src.ztare.gates.falsifiability_gate", "evaluate_falsifiability"),
            dependencies=[],
        ),
        # ── Interactive-environment gates (GP-250) ──────────────────
        # Transition-program candidates on interactive substrates: exact
        # replay over the episode log, then rollout depth on a held-out
        # episode (the farther-tail discipline with time as the tail
        # axis). Pure logic lives in src/ztare/worldmodel/gates.py; these
        # entries adapt the dispatcher contract.
        Gate(
            name="worldmodel_replay",
            phase="POST_FIT",
            can_handle=_engages_on("interactive_environment"),
            run=_make_run_callback("src.ztare.gates.worldmodel_gates", "run_replay_gate"),
            dependencies=[],
        ),
        Gate(
            name="worldmodel_rollout",
            phase="POST_FIT",
            can_handle=_engages_on("interactive_environment"),
            run=_make_run_callback("src.ztare.gates.worldmodel_gates", "run_rollout_gate"),
            dependencies=["worldmodel_replay"],
        ),
        Gate(
            name="derived_constraints",
            phase="POST_JUDGE",
            can_handle=_engages_universally(),
            run=_make_run_callback("src.ztare.gates.derived_constraints", "render_confirmed_constraints_prompt_section"),
            dependencies=[],
        ),

        # ── 1d-curve substrate gates ────────────────────────────────
        # coordinate_invariance: panel UNANIMOUS WIRE on 1d + time_series
        # (Chaos: KY-dimension/Lyapunov-sum invariance under C¹ diffeo).
        Gate(
            name="coordinate_invariance",
            phase="POST_FIT",
            can_handle=_engages_on("1d", "time_series", "time_series_chaotic"),
            run=_make_run_callback("src.ztare.gates.coordinate_invariance_gate", "run_gate"),
            dependencies=[],
        ),
        # residual_norm: classified as UTILITY (not registered as Gate)
        # per panel synthesis 2026-04-25. Module remains importable;
        # downstream gates (e.g. coordinate_invariance, asymptotic) call it
        # as a helper, not as a separately-dispatched gate.

        # ── 1d + nd_features gates ──────────────────────────────────
        Gate(
            name="asymptotic_claim_discipline",
            phase="POST_FIT",
            can_handle=_engages_on("1d", "nd_features"),
            run=_make_run_callback("src.ztare.gates.asymptotic_claim_discipline", "assess_asymptotic_claim_discipline"),
            dependencies=[],
        ),
        Gate(
            name="deterministic_charter_gates",
            phase="POST_FIT",
            can_handle=_engages_on("1d", "nd_features"),
            run=_make_run_callback("src.ztare.gates.deterministic_charter_gates", "evaluate_deterministic_charter_gates"),
            dependencies=[],
        ),
        Gate(
            name="linear_observable_coercivity",
            phase="POST_FIT",
            can_handle=_engages_universally_when_flag(
                "enable_linear_observable_coercivity_gate"
            ),
            run=_make_run_callback("src.ztare.gates.linear_observable_coercivity_gate", "run_gate"),
            dependencies=[],
        ),

        # ── nd_features modified-gravity gates (Solar-System PPN) ──
        # G-CASSINI-PPN + G-MERCURY-PRECESSION engage only when the
        # rubric flag `enable_solar_system_ppn_gates` is true. The
        # gates evaluate the candidate's y(g_bar) at Solar-System
        # probe accelerations and require it to reduce to Newtonian
        # gravity within the Cassini bound (|γ−1|<2.3e-5; Bertotti+
        # 2003) and the Mercury perihelion bound (≤0.5% of 43.0
        # arcsec/century). Substrates without the flag (galaxy-scale
        # fits without gravitational claim, OEIS, audit) skip.
        Gate(
            name="cassini_ppn",
            phase="POST_FIT",
            can_handle=_engages_on_when_flag(
                "nd_features", "1d", flag_key="enable_solar_system_ppn_gates"
            ),
            run=_make_run_callback("src.ztare.gates.gravity_ppn_gates", "check_cassini_ppn"),
            dependencies=[],
        ),
        Gate(
            name="mercury_precession",
            phase="POST_FIT",
            can_handle=_engages_on_when_flag(
                "nd_features", "1d", flag_key="enable_solar_system_ppn_gates"
            ),
            run=_make_run_callback("src.ztare.gates.gravity_ppn_gates", "check_mercury_perihelion"),
            dependencies=["cassini_ppn"],
        ),

        # ── nd_features-only gates ──────────────────────────────────
        # domain_match: per panel synthesis, scope is Lean-substrate
        # (proof_target + nd_features-with-Lean), not universal feature_dict.
        # Mathematician + CS Engineer flagged regex-based Lean parsing
        # as fragile but contained.
        Gate(
            name="domain_match",
            phase="POST_FIT",
            can_handle=_engages_on("nd_features", "proof_target"),
            run=_make_run_callback("src.ztare.gates.domain_match_gate", "run_gate"),
            dependencies=[],
        ),
        Gate(
            name="ensemble_ambiguity",
            phase="POST_FIT",
            can_handle=_engages_on("nd_features"),
            run=_make_run_callback("src.ztare.gates.ensemble_ambiguity_gate", "run_gate"),
            dependencies=[],
        ),

        # ── time_series gates ────────────────────────────────────────
        # continuum_limit: per panel, only RMS-chaos-trap precheck (subgate 1)
        # is live; BKM/Leray subgates dormant pending PDE substrate roadmap.
        Gate(
            name="continuum_limit",
            phase="POST_FIT",
            can_handle=_engages_on("time_series", "time_series_chaotic", "1d"),
            run=_make_run_callback("src.ztare.gates.continuum_limit_gate", "run_gate"),
            dependencies=[],
        ),
        Gate(
            name="wasserstein_persistence",
            phase="POST_FIT",
            can_handle=_engages_on("time_series", "time_series_chaotic"),
            run=_make_run_callback("src.ztare.gates.wasserstein_persistence_gate", "run_gate"),
            dependencies=[],
        ),
        # coordinate_invariance also engages on time_series per panel matrix
        # (Chaos Theorist: KY-dimension/Lyapunov sum invariance is gold standard).
        # Note: gate already declared above for "1d"; duplicate registration
        # would error. Substrate-class affinity for time_series is captured
        # by adding it to the existing "1d" predicate's allowed set below.

        # ── proof_target gates (GP-122 / GP-139) ────────────────────
        Gate(
            name="ansatz_survivor",
            phase="POST_JUDGE",
            can_handle=_engages_on("proof_target"),
            run=_make_run_callback("src.ztare.gates.ansatz_survivor_gate", "run_gate"),
            dependencies=[],
        ),
        Gate(
            name="proof_surveyability",
            phase="POST_JUDGE",
            can_handle=_engages_on("proof_target"),
            run=_make_run_callback("src.ztare.gates.proof_surveyability_gate", "run_gate"),
            dependencies=["ansatz_survivor"],  # surveyability depends on ansatz survivors
        ),
        Gate(
            name="translation_diff",
            phase="POST_JUDGE",
            can_handle=_engages_on("proof_target"),
            run=_make_run_callback("src.ztare.gates.translation_diff_gate", "run_gate"),
            dependencies=[],
        ),

        # ── closed_form_constant gates (GP-145 PSLQ) ────────────────
        Gate(
            name="pslq_falsity_audit",
            phase="POST_FIT",
            can_handle=_engages_on("closed_form_constant"),
            run=_make_run_callback("src.ztare.gates.pslq_falsity_audit_gate", "evaluate_relation_at_precision"),
            dependencies=[],
        ),

        # ── audit substrate gates (gp156 / gp158) ───────────────────
        Gate(
            name="prompt_leak_audit",
            phase="PRE_JUDGE",
            can_handle=_engages_on("audit"),
            run=_make_run_callback("src.ztare.gates.prompt_leak_audit", "audit_prompt_for_leak"),
            dependencies=[],
        ),

        # ── v5.0 infrastructure gates ───────────────────────────────
        # cage.py + substrate_evaluation.py are infrastructure, not
        # registered as gates. They're called BY the dispatcher.
    ]


def get_default_cage() -> Cage:
    """Return the v5.0 Cage with all 17 dormant + 5 live gates registered.

    Per the gp158 audit Class L finding, every existing gate either WIRES
    here or has a RETIRE rationale in DECISION_LOG.md. As of v5.0 Phase 3a
    ship, no RETIRE decisions have been made — all 17 dormant gates are
    WIRE.

    Multi-disciplinary panel review (chaos / quantum / physics / math /
    CS) running in parallel may RECOMMEND retire on individual gates;
    the operator's final decision is recorded in DECISION_LOG.md before
    any RETIRE removes a gate from this list.

    autoresearch_loop.py imports this and calls
    `cage.dispatch(substrate, candidate)` once per iter (Phase 3b).
    """
    return Cage(_build_gates())


# Convenience: the canonical engagement predicates exported for testing
# and for downstream gates that share the same substrate-class affinity.
__all__ = [
    "get_default_cage",
    "_engages_on",
    "_engages_universally",
    "_engages_universally_when_flag",
]
