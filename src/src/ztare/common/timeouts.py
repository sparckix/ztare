"""Central time-budget factory — ONE place that resolves every blocking-operation timeout, with env-var
overrides instead of constants scattered across the solver / formal / governance modules.

WHY THIS EXISTS (the operator's ask after the P1-RUNG-A silent-death RCA): the recurring "the run just hangs"
bugs were all the SAME class — a deeply-nested blocking call (a `lake env lean`, a REPL `check`, a `#print
axioms` audit) whose timeout was either MISSING (blocks forever) or ≈ the whole wallclock (one stuck probe eats
the budget). Fixing them one-by-one with hardcoded numbers invites the next one. Instead every timeout now flows
through `timeout_s(<name>)`:

  • the CODE default is the single source of truth (mirrors `solver/config.py`: defaults live in code);
  • an env var is an OPTIONAL override (absent ⇒ the default ⇒ byte-parity) so a node can be tuned without edits;
  • a missing timeout becomes greppable — it's "a blocking call that did NOT call `timeout_s`";
  • `clamp_to_remaining()` enforces the standing lesson (a per-step timeout ≈ total wallclock starves every later
    step) by clamping a named budget to the wallclock that actually remains;
  • `budgets_report()` dumps the resolved table for the run banner (so a hang is troubleshootable: you can SEE
    which budget was in force, instead of archaeology with faulthandler).

Soundness note (mirrors config.py): these are PURE-TUNING knobs. A worse timeout costs closures (a real proof
times out → honest "open"), never a FALSE closure — the kernel still gates. So they are operator-overridable.
Stdlib-only (no ztare imports) so the lowest layers (`ztare.formal`) can depend on it with no import cycle.

  python -m ztare.common.timeouts --selftest      # controls: default / override / floor / clamp
  python -m ztare.common.timeouts                  # print the resolved budget table
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class _Budget:
    default: int     # the canonical code default (seconds, or budget-units for the abstract ones)
    env: str         # the OPTIONAL override env var (absent ⇒ default ⇒ byte-parity)
    floor: int = 1   # a hard lower bound so a fat-fingered override can't set a starving 0/-5


# The canonical registry. Folds in the timeout env vars that ALREADY existed (ZTARE_COLD_BASELINE_S stays a
# separate measurement pin; these are the OPERATIONAL budgets). Add a row here, not an ad-hoc os.environ.get.
_BUDGETS: "dict[str, _Budget]" = {
    # Lean compile budgets
    "cold_compile":      _Budget(300, "ZTARE_LEANMILL_COLD_COMPILE_S", floor=30),   # cold `lake env lean` of a probe
    "warm_repl_ceiling": _Budget(90,  "ZTARE_LEANMILL_REPL_WARM_CEILING_S", floor=15),  # per-probe WARM REPL cap
    "equiv_compile":     _Budget(180, "ZTARE_LEANMILL_EQUIV_TIMEOUT_S", floor=60),   # cross-vote ↔ equivalence compile
    "axiom_audit":       _Budget(180, "ZTARE_LEANMILL_AXIOM_AUDIT_S", floor=30),     # cold `#print axioms` audit
    "leaf_verify":       _Budget(250, "ZTARE_LEANMILL_LEAF_VERIFY_S", floor=30),     # solve_leaf final verify_lean_proof compile of the agent's probe (was a hardcoded 250)
    "vacuity_probe":     _Budget(150, "ZTARE_LEANMILL_VACUITY_PROBE_S", floor=30),   # firewall nondegenerate-instance (vacuity) compile probe (was a hardcoded 150)
    "substrate_liveness": _Budget(120, "ZTARE_LEANMILL_SUBSTRATE_LIVENESS_S", floor=15),  # warm-REPL substrate-liveness check (positive/negative-false/sorry-gate; was a hardcoded 120)
    "independent_verify": _Budget(70,  "ZTARE_LEANMILL_INDEPENDENT_VERIFY_S", floor=15),  # v33 indirect/exact independent re-verify compile (was a hardcoded 70)
    "margin_probe":      _Budget(90,  "ZTARE_LEANMILL_MARGIN_PROBE_S", floor=15),    # opt-in proof_margin_of_safety perturbation compile (was a hardcoded 90)
    "selfcheck_compile": _Budget(180, "ZTARE_LEANMILL_SELFCHECK_COMPILE_S", floor=30),  # solver self-check positive/negative control lake compile (was a hardcoded 180)
    # Tactic / move budgets.
    #   (No `per_tactic` budget here ON PURPOSE: the native-hammer per-tactic FLOOR is already owned by the
    #    typed solver config `solver/config.py::SolverConfig.native_hammer_per_tactic_floor_s` (#49). One home
    #    per concept — don't register a second. Operational per-op budgets that config does NOT own live here.)
    "dag_move_budget":   _Budget(32,  "ZTARE_DAG_MOVE_BUDGET", floor=1),             # per-move budget units (abstract)
    "propose":           _Budget(180, "ZTARE_PROPOSE_TIMEOUT", floor=10),            # a propose/generate dispatch
    "planner":           _Budget(1800, "ZTARE_LEANMILL_PLANNER_TIMEOUT_S", floor=180),  # the iso DECOMPOSE planner dispatch. Default 1800 is INTENTIONALLY ≥ any single-target wallclock so `clamp_to_remaining("planner", caller_timeout_s)` = the CALLER's FULL allotted budget — NOT an arbitrary sub-cap. Generating an AUDITED frontier decomposition IS the work; a fixed 180/360 sub-budget is "still arbitrary, still a wall" and GUILLOTINED a codex run that had an audit-PASSING Hermite DAG ready (it was stalled on its own cold `lake env lean`, 2026-06-11). Hang-protection is the WARM check surfaced to the planner (no cold-compile stall) + the caller wallclock; a node can still set an EXPLICIT cap via the env. TRUE free-will = idle/heartbeat kill (kill only on SILENCE) — needs a streaming dispatch (follow-up), since subprocess.run can only enforce a hard wall.
    "notes_refine":      _Budget(240, "ZTARE_LEANMILL_NOTES_REFINE_S", floor=30),    # opt-in best-effort blueprint-refine dispatch (a `propose`-class generate; kept a distinct key — its prior value was a hardcoded 240, not the 180 propose default — so the migration is byte-parity)
    "notes_lemma":       _Budget(1200, "ZTARE_LEANMILL_NOTES_LEMMA_S", floor=240),   # notes-channel per-LEMMA whole-attack wallclock (formalize→plan→solve→ratify). GENEROUS (was a hardcoded 400): a frontier sub-lemma is real research; the planner now draws from THIS via clamp_to_remaining. Self-learn the right value from recorded attempts.wallclock_s (next).
    "notes_target":      _Budget(1800, "ZTARE_LEANMILL_NOTES_TARGET_S", floor=300),  # notes-channel per-TARGET whole-attack wallclock (was a hardcoded 600). The planner gets up to THIS (no arbitrary sub-cap). 30 min for a research-grade frontier target.
    # External-tool budgets
    "agent_dispatch":    _Budget(600, "ZTARE_LEANMILL_DISPATCH_S", floor=30),        # a subscription-agent dispatch
    "formalize_oneshot": _Budget(240, "ZTARE_LEANMILL_FORMALIZE_ONESHOT_S", floor=60),  # per oneshot NL→Lean
    #   (was a HARDCODED `timeout_s=240` default in autoformalize.default_formalize — the exact "arbitrary magic
    #    constant" this factory exists to kill. A oneshot single theorem is lighter than multistep, hence < the
    #    360 multistep budget. Env-tunable per node; the deepseek API fallback makes a contention-timeout moot.)
    "formalize_multistep": _Budget(360, "ZTARE_LEANMILL_FORMALIZE_MULTISTEP_S", floor=120),  # per define_then_state
    #   (CALIBRATED 2026-06-10, not guessed: measured claude multistep dispatches peaked at ~243s on the hard
    #    PF-existence lemma, so 360s = the observed max + headroom. Re-measure + bump if a node is slower.)
    "sledgehammer":      _Budget(120, "ZTARE_LEANMILL_SLEDGEHAMMER_S", floor=10),    # Isabelle sledgehammer call
    "smt_solve":         _Budget(30,  "ZTARE_LEANMILL_SMT_S", floor=1),              # a z3 / cvc5 solve
    "provider_live":     _Budget(90,  "ZTARE_LEANMILL_PROVIDER_LIVE_S", floor=10),   # the provider-liveness ping
}


def _read(env: str) -> "int | None":
    raw = os.environ.get(env)
    if raw is None or not str(raw).strip():
        return None
    try:
        return int(float(raw))           # tolerate "90" and "90.0"
    except (TypeError, ValueError):
        return None                       # a garbage override falls back to the default (fail-safe, never crash)


def register(name: str, default: int, env: str, floor: int = 1) -> None:
    """Register (or override) a named budget — for a module that owns a budget not in the canonical table.
    Idempotent; last registration wins. Keeps the factory extensible without editing this file."""
    _BUDGETS[name] = _Budget(int(default), env, int(floor))


def timeout_s(name: str, default: "int | None" = None) -> int:
    """Resolve a named time budget in seconds (or budget-units for the abstract ones). Env override wins, then
    the registered default, then the passed `default`. Always ≥ the registered floor. For an UNREGISTERED name a
    `default` is required and a generic `ZTARE_TIMEOUT_<NAME>_S` env override applies (so even ad-hoc budgets get
    the env-override convention for free)."""
    b = _BUDGETS.get(name)
    if b is not None:
        v = _read(b.env)
        return max(b.floor, v if v is not None else b.default)
    if default is None:
        raise KeyError(f"unregistered time budget {name!r} and no default given — register it in timeouts._BUDGETS")
    v = _read(f"ZTARE_TIMEOUT_{name.upper()}_S")
    return max(1, v if v is not None else int(default))


def clamp_to_remaining(name: str, remaining_s: float, *, default: "int | None" = None) -> int:
    """The named budget, CLAMPED to the wallclock that actually remains — the standing lesson (a per-step
    timeout ≈ total wallclock starves every LATER step). Never below the budget's floor (so a near-exhausted
    wallclock still gets a minimal, honest attempt rather than 0). Use at every per-move / per-probe call that
    runs inside a larger deadline."""
    floor = _BUDGETS[name].floor if name in _BUDGETS else 1
    return max(floor, min(timeout_s(name, default), int(max(0, remaining_s))))


def budgets_report() -> "dict[str, int]":
    """The resolved budget table (env overrides applied) — for the run banner / observability so a hang is
    troubleshootable (you can SEE which budget was in force)."""
    return {name: timeout_s(name) for name in sorted(_BUDGETS)}


def _selftest() -> int:
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    # default when no env (byte-parity)
    os.environ.pop("ZTARE_LEANMILL_AXIOM_AUDIT_S", None)
    ok("default when env unset", timeout_s("axiom_audit") == 180)
    # env override wins
    os.environ["ZTARE_LEANMILL_AXIOM_AUDIT_S"] = "45"
    ok("env override wins", timeout_s("axiom_audit") == 45)
    # floor clamps a too-small override
    os.environ["ZTARE_LEANMILL_AXIOM_AUDIT_S"] = "3"
    ok("floor clamps a starving override", timeout_s("axiom_audit") == 30)
    # garbage override → default (fail-safe)
    os.environ["ZTARE_LEANMILL_AXIOM_AUDIT_S"] = "not-a-number"
    ok("garbage override falls back to default", timeout_s("axiom_audit") == 180)
    os.environ.pop("ZTARE_LEANMILL_AXIOM_AUDIT_S", None)
    # float-string tolerated
    os.environ["ZTARE_LEANMILL_REPL_WARM_CEILING_S"] = "90.0"
    ok("float-string override tolerated", timeout_s("warm_repl_ceiling") == 90)
    os.environ.pop("ZTARE_LEANMILL_REPL_WARM_CEILING_S", None)
    # clamp_to_remaining honours the wallclock
    ok("clamp to remaining wallclock", clamp_to_remaining("cold_compile", 50) == 50)
    ok("clamp never below floor", clamp_to_remaining("cold_compile", 1) == 30)
    ok("clamp capped by the budget when wallclock is ample", clamp_to_remaining("cold_compile", 9999) == 300)
    # unregistered name needs a default + gets the generic env convention
    ok("unregistered name uses passed default", timeout_s("adhoc_thing", 42) == 42)
    os.environ["ZTARE_TIMEOUT_ADHOC_THING_S"] = "7"
    ok("unregistered name honours generic env override", timeout_s("adhoc_thing", 42) == 7)
    os.environ.pop("ZTARE_TIMEOUT_ADHOC_THING_S", None)
    try:
        timeout_s("totally_unknown")
        ok("unregistered name with no default raises", False)
    except KeyError:
        ok("unregistered name with no default raises", True)
    # register extends the table
    register("custom_budget", 55, "ZTARE_CUSTOM_BUDGET_S", floor=10)
    ok("register adds a budget", timeout_s("custom_budget") == 55)
    ok("budgets_report includes the registered budgets", "axiom_audit" in budgets_report())

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    print("Resolved time budgets (seconds; env overrides applied):")
    for k, v in budgets_report().items():
        print(f"  {k:20s} {v}")
