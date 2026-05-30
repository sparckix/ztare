"""GP-180 Lagrangian Derivation dispatch — extracted from autoresearch_loop.

Single entry point: `dispatch_gp180_lagrangian()`. Owns the full
inline behavior the autoresearch loop used to carry: sympy derivation,
non-degeneracy gating, Lagrangian-path telemetry, gaming-streak
detection, and substituting the derived form back into the python
suite. Returns a result struct the caller threads into the existing
fit/cage pipeline.

Why this is a module
--------------------
Before the extraction, ~150 lines of GP-180 logic lived inline in
the autoresearch_loop's fit_primitive_features dispatch block. That
file is already long and had been flagged for modular refactor.
Adding more inline accretion would have re-introduced the spaghetti
pattern. This module concentrates everything GP-180-related in one
file with a clean function boundary; the autoresearch loop now calls
it as a single line.

Result schema:
    GP180DispatchResult(
        engaged: bool,                # True iff rubric flag was on
        derivation_attempted: bool,   # True iff sympy was invoked
        derivation_success: bool,     # True iff sympy returned a closed form
        substituted_form: Optional[str],   # the derived callable_src; None if no substitution
        substituted_python_code: Optional[str], # python_code with PARAMETRIC_FORM rewritten
        noether_kept: dict[str, str], # symmetry → invariant strings that survived non-degeneracy gate
        telemetry: dict,              # path-adoption counters for iteration_telemetry
        gaming_streak_emitted: bool,  # True iff noether_gaming_streak signal fired this iter
    )

The caller is responsible for using `substituted_form` /
`substituted_python_code` (overriding the mutator's PARAMETRIC_FORM)
and `noether_kept` (passed to fit_features as `noether_invariants`).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class GP180DispatchResult:
    engaged: bool = False
    derivation_attempted: bool = False
    derivation_success: bool = False
    substituted_form: Optional[str] = None
    substituted_python_code: Optional[str] = None
    noether_kept: dict[str, str] = field(default_factory=dict)
    telemetry: dict = field(default_factory=lambda: {
        "lagrangian_declared": False,
        "derivation_success": False,
        "noether_kept": 0,
        "noether_dropped_degenerate": 0,
        "noether_weak": 0,
        "lagrangian_nontriviality_verdict": None,  # GP-183 B1
    })
    gaming_streak_emitted: bool = False
    nontriviality_verdict: Optional[str] = None  # GP-183 B1


def dispatch_gp180_lagrangian(
    *,
    python_code: str,
    parameter_names: list[str],
    workspace_dir: Path,
    iter_index_one_based: int,
    rubric_data: dict,
) -> GP180DispatchResult:
    """Run the full GP-180 dispatch pipeline.

    Args:
      python_code: the mutator's submitted test_model.py text. May
        contain a LAGRANGIAN declaration alongside PARAMETRIC_FORM.
      parameter_names: PARAMETER_NAMES from the submission; used by
        sympy to know which symbols are fittable constants.
      workspace_dir: target directory for persisted artifacts
        (lagrangian_derivation_latest.json, noether_nondegeneracy_audit.json,
        gp180_telemetry_latest.json, noether_gaming_streak.json).
      iter_index_one_based: iter number for streak-tracking.
      rubric_data: rubric dict; checked for enable_lagrangian_derivation.

    Returns:
      GP180DispatchResult. The caller substitutes the derived form
      (if any), passes noether_kept to fit_features, and records the
      telemetry.
    """
    result = GP180DispatchResult()
    if not bool(rubric_data.get("enable_lagrangian_derivation", False)):
        return result
    result.engaged = True

    try:
        from src.ztare.fit.lagrangian_derivation import (
            derive_from_submission, to_jsonable, substitute_derived_parametric_form,
        )
    except ImportError as exc:
        print(f"🧮   GP-180 import failure (sympy?): {exc}")
        return result

    result.derivation_attempted = True
    try:
        gp180 = derive_from_submission(python_code, parameter_names=parameter_names)
    except Exception as exc:                                            # noqa: BLE001
        print(f"🧮   GP-180 dispatch error (non-fatal): {type(exc).__name__}: {exc}")
        return result

    if gp180 is None:
        print(f"🧮   GP-180 Lagrangian: no LAGRANGIAN declaration; "
              f"using mutator PARAMETRIC_FORM (legacy mode)")
    elif not gp180.success:
        result.telemetry["lagrangian_declared"] = True
        print(f"🧮   GP-180 Lagrangian: derivation FAILED — {gp180.error_message}")
        print(f"🧮             falling back to mutator PARAMETRIC_FORM")
    else:
        result.telemetry["lagrangian_declared"] = True
        result.telemetry["derivation_success"] = True
        result.derivation_success = True
        print(f"🧮   GP-180 Lagrangian: ✅ derived closed-form")
        print(f"🧮             EOM: {gp180.eom[0][:120] if gp180.eom else ''}")
        print(f"🧮             steady_state: {gp180.steady_state}")
        print(f"🧮             closed_form: {gp180.closed_form[:160]}")
        # GP-183 B1: classify the Lagrangian's derivation content
        # (trivial single-feature substitution, params-only, or genuine
        # multi-symbol composition). Trivial Lagrangians are the iter-2
        # false-positive class — they pass the legacy success check but
        # contain no derivation content beyond syntactic substitution.
        try:
            from src.ztare.gates.lagrangian_nontrivial_gate import (
                evaluate_lagrangian_nontriviality, GATE_ID as _LNT_ID,
            )
            _bg_syms = list(gp180.steady_state.keys()) if hasattr(gp180, "steady_state") else []
            # The dispatch caller has the original `background` list;
            # we synthesize it from the closed-form features. Background
            # symbols are also accessible via the substrate feature heuristic.
            _lnt = evaluate_lagrangian_nontriviality(
                gp180.steady_state,
                background_symbols=None,  # heuristic-only mode
                param_symbols=parameter_names,
            )
            result.nontriviality_verdict = _lnt["verdict"]
            result.telemetry["lagrangian_nontriviality_verdict"] = _lnt["verdict"]
            if _lnt["verdict"] == "trivial":
                print(f"🧮   🛑 G-LAGRANGIAN-NONTRIVIAL: TRIVIAL — {_lnt['reason'][:140]}")
                # GP-183 C1 (2026-04-28): rubric flag
                # `require_nontrivial_lagrangian` hardens B1 from
                # informational to a skip-fit. When set true, a trivial
                # Lagrangian declaration causes GP-180 to discard the
                # derived form and revert to the mutator's legacy
                # PARAMETRIC_FORM (which the cage's R20-R24 will then
                # adjudicate normally). This prevents the iter-2
                # false-positive class from polluting the fit pipeline.
                if bool(rubric_data.get("require_nontrivial_lagrangian", False)):
                    print(f"🧮      → require_nontrivial_lagrangian=true: discarding "
                          f"derived form, reverting to mutator PARAMETRIC_FORM")
                    result.substituted_form = None
                    result.substituted_python_code = None
                    result.noether_kept = {}
            elif _lnt["verdict"] == "params_only":
                print(f"🧮   ⚠ G-LAGRANGIAN-NONTRIVIAL: params-only (informational; no cap)")
            else:
                print(f"🧮   ✓ G-LAGRANGIAN-NONTRIVIAL: {_lnt['verdict']}")
            try:
                (workspace_dir / f"lagrangian_nontriviality_iter_{iter_index_one_based:03d}.json").write_text(
                    json.dumps(_lnt, indent=2, default=str)
                )
            except OSError:
                pass
        except Exception as exc:                                        # noqa: BLE001
            print(f"🧮   G-LAGRANGIAN-NONTRIVIAL gate error (non-fatal): {exc}")
        if gp180.noether:
            for sym, inv in gp180.noether.items():
                print(f"🧮             noether[{sym}]: {inv[:120]}")
            # Non-degeneracy gate: drop AST-trivial-constant invariants
            # (X-X, X/X, X*0, X**0). Keep "weak" (params-only) — they
            # contribute zero to the loss anyway.
            try:
                from src.ztare.gates.noether_nondegeneracy_gate import filter_invariants
                kept, audit_entries = filter_invariants(gp180.noether)
            except Exception as exc:                                    # noqa: BLE001
                print(f"🧮             noether non-degeneracy gate error: {exc}")
                kept, audit_entries = {}, []
            for entry in audit_entries:
                if entry["verdict"] == "degenerate":
                    print(f"🧮             ⊘ DROPPED noether[{entry['symmetry']}] "
                          f"degenerate: {entry['reason']}")
                    result.telemetry["noether_dropped_degenerate"] += 1
                elif entry["verdict"] == "weak":
                    print(f"🧮             ~ noether[{entry['symmetry']}] weak: "
                          f"{entry['reason']}")
                    result.telemetry["noether_weak"] += 1
                else:  # "ok"
                    result.telemetry["noether_kept"] += 1
            # Dual write: per-iter audit + `_latest` backward-compat copy.
            # GP-183 phase A2.
            nd_payload = json.dumps(audit_entries, indent=2)
            try:
                (workspace_dir / f"noether_nondegeneracy_iter_{iter_index_one_based:03d}.json").write_text(nd_payload)
                (workspace_dir / "noether_nondegeneracy_audit.json").write_text(nd_payload)
            except OSError:
                pass
            result.noether_kept = dict(kept)
        # Substitute derived form for mutator PARAMETRIC_FORM in BOTH
        # the local _form variable AND the python_code text.
        if gp180.closed_form_callable_src:
            print(f"🧮             SUBSTITUTING derived form for "
                  f"mutator PARAMETRIC_FORM (both local + python_code)")
            result.substituted_form = gp180.closed_form_callable_src
            try:
                result.substituted_python_code = substitute_derived_parametric_form(
                    python_code, gp180.closed_form_callable_src
                )
            except Exception as exc:                                    # noqa: BLE001
                print(f"🧮             ⚠ python_code rewrite failed: "
                      f"{type(exc).__name__}: {exc}")

    # Persist the full derivation result for downstream consumers and
    # post-run analysis. Two copies: per-iter file (audit history) +
    # `_latest` file (backward-compat for callers that want the most
    # recent result without iter-aware logic). GP-183 phase A1.
    if gp180 is not None:
        payload = json.dumps(to_jsonable(gp180), indent=2, default=str)
        try:
            (workspace_dir / f"lagrangian_derivation_iter_{iter_index_one_based:03d}.json").write_text(payload)
            (workspace_dir / "lagrangian_derivation_latest.json").write_text(payload)
        except OSError:
            pass

    # Path-adoption telemetry: same dual-write pattern. GP-183 phase A3.
    tel_payload = json.dumps(result.telemetry, indent=2)
    try:
        (workspace_dir / f"gp180_telemetry_iter_{iter_index_one_based:03d}.json").write_text(tel_payload)
        (workspace_dir / "gp180_telemetry_latest.json").write_text(tel_payload)
    except OSError:
        pass

    # Noether-gaming-streak detection. If 3+ consecutive iters declared
    # a Lagrangian but produced ZERO non-degenerate Noether invariants,
    # the mutator is gaming the variance penalty via trivial
    # Lagrangians (variance of 0 is 0; loss term is silenced).
    noether_gamed = (
        result.telemetry["lagrangian_declared"]
        and result.telemetry["noether_kept"] == 0
    )
    streak_path = workspace_dir / "noether_gaming_streak.json"
    if streak_path.exists():
        try:
            streak = json.loads(streak_path.read_text())
        except (OSError, json.JSONDecodeError):
            streak = {"consecutive_gamed": 0, "history": []}
    else:
        streak = {"consecutive_gamed": 0, "history": []}
    streak["consecutive_gamed"] = (
        streak.get("consecutive_gamed", 0) + 1 if noether_gamed else 0
    )
    streak.setdefault("history", []).append({
        "iter": iter_index_one_based,
        "gamed": noether_gamed,
        "kept": result.telemetry["noether_kept"],
        "weak": result.telemetry["noether_weak"],
        "dropped": result.telemetry["noether_dropped_degenerate"],
    })
    streak["history"] = streak["history"][-10:]
    try:
        streak_path.write_text(json.dumps(streak, indent=2))
    except OSError:
        pass
    if streak["consecutive_gamed"] >= 3:
        print(f"🚨 noether-gaming streak: {streak['consecutive_gamed']} "
              f"consecutive iter(s) declared LAGRANGIAN with all "
              f"Noether invariants dropped/weak. Mutator likely "
              f"gaming the variance penalty via trivial Lagrangians.")
        try:
            from src.ztare.signals.damage import emit as emit_damage
            emit_damage(
                source="autoresearch.noether_streak",
                kind="noether_gaming_streak",
                detail=(
                    f"iter {iter_index_one_based}: {streak['consecutive_gamed']} "
                    f"consecutive iters with all-degenerate or weak "
                    f"Noether invariants. Suspected variance-penalty "
                    f"gaming via trivial Lagrangians."
                ),
                severity="warn",
            )
            result.gaming_streak_emitted = True
        except Exception:                                              # noqa: BLE001
            pass

    return result
