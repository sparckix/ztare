"""FAIL-LOUD carrier preflight — the admissibility gate for every lift / A-B run (roadmap #1, 2026-06-09).

WHY (operator rule, twice-codified): "a negative is INADMISSIBLE without calibration through the SAME code
path." The failure mode this prevents is concrete and already happened: an A/B runner launched on the WRONG
interpreter (system `python`, which lacks sympy/cvc5/z3/numpy) records a FABRICATED fail-closed null for
every exogenous move — a dead instrument masquerading as a capability verdict (the yield-audit agents hit
exactly this: they probed system python and "found" 4 dead moves that are live under `./venv/bin/python`).

So before ANY lift run, assert each move's CARRIER both imports AND closes a trivial positive control:
  • sympy  (witness_transport)  — `diop_DN(61,1)` returns the Pell D=61 fundamental x=1766319049
  • cvc5   (abduce)             — a Solver instantiates and check-sat returns
  • z3     (cross_vote / SMT boundary) — solves a trivial constraint
  • numpy  (functor_lift)       — a spectral (eigenvalue) compute runs
  • sdp/cvxpy (sos_multivariate) — OPTIONAL: cvxpy solves a tiny SDP (transport edge #2). Absent ⇒ reported,
                                   not fatal (multivariate `sos` fail-closes to None; univariate unaffected)
  • native_hammer (Lean cascade) — closes `: True := by trivial`  [opt-in: needs the Lean box, --lean]

`run_preflight()` returns the per-carrier verdicts; the CLI exits NONZERO naming any DEAD *required* carrier.
Wire it as the mandatory first step of a benchmark/A-B runner so a dead carrier ABORTS the run instead of
poisoning it. FUTURE NODES: a new transport carrier = a `_check_*` here (mark `optional=True` if the move
fail-closes without it) + its dep in requirements.txt (auto-installed by prepare_lean_backends.sh step 6b).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass


@dataclass
class CarrierVerdict:
    name: str
    move: str
    live: bool
    detail: str
    optional: bool = False   # an OPT-IN carrier (e.g. the SDP node) — reported but never fails the assert


def _check_sympy() -> CarrierVerdict:
    try:
        from sympy.solvers.diophantine.diophantine import diop_DN
        sols = diop_DN(61, 1)  # Pell D=61, N=1 — the famous huge fundamental solution
        ok = any(abs(int(x)) == 1766319049 for x, _y in sols)
        return CarrierVerdict("sympy", "witness_transport", ok,
                              f"diop_DN(61,1)={sols}" if ok else f"WRONG fundamental: {sols}")
    except Exception as e:  # noqa: BLE001
        return CarrierVerdict("sympy", "witness_transport", False, f"{type(e).__name__}: {e}")


def _check_cvc5() -> CarrierVerdict:
    try:
        import cvc5
        s = cvc5.Solver()
        s.setOption("produce-models", "true")
        x = s.mkConst(s.getIntegerSort(), "x")
        s.assertFormula(s.mkTerm(cvc5.Kind.GT, x, s.mkInteger(5)))
        r = s.checkSat()
        ok = r.isSat()
        return CarrierVerdict("cvc5", "abduce", ok, f"check-sat={r} (ver {getattr(cvc5,'__version__','?')})")
    except Exception as e:  # noqa: BLE001
        return CarrierVerdict("cvc5", "abduce", False, f"{type(e).__name__}: {e}")


def _check_z3() -> CarrierVerdict:
    try:
        import z3
        s = z3.Solver(); x = z3.Int("x"); s.add(x > 5, x < 8)
        ok = s.check() == z3.sat
        return CarrierVerdict("z3", "cross_vote/smt_boundary", ok, f"check={s.check()}")
    except Exception as e:  # noqa: BLE001
        return CarrierVerdict("z3", "cross_vote/smt_boundary", False, f"{type(e).__name__}: {e}")


def _check_numpy() -> CarrierVerdict:
    try:
        import numpy as np
        ev = np.linalg.eigvals(np.array([[2.0, 0.0], [0.0, 3.0]]))
        ok = sorted(round(float(e), 6) for e in ev) == [2.0, 3.0]
        return CarrierVerdict("numpy", "functor_lift", ok, f"eigvals={sorted(ev.tolist())}")
    except Exception as e:  # noqa: BLE001
        return CarrierVerdict("numpy", "functor_lift", False, f"{type(e).__name__}: {e}")


def _check_sdp() -> CarrierVerdict:
    """SDP carrier (transport edge #2 — multivariate SOS via cvxpy). OPTIONAL: multivariate `sos` fail-closes
    to None without it (the univariate path is unaffected), so a node that doesn't provision cvxpy is NOT
    failed — it is reported. cvxpy must SOLVE a tiny SDP, not merely import (the dead-instrument discipline)."""
    try:
        import cvxpy as cp
        import numpy as np  # noqa: F401
        X = cp.Variable((2, 2), symmetric=True)
        prob = cp.Problem(cp.Minimize(cp.trace(X)), [X >> 0, X[0, 0] == 1, X[1, 1] == 1])
        prob.solve(solver=cp.SCS, verbose=False)
        ok = prob.status in ("optimal", "optimal_inaccurate")
        return CarrierVerdict("sdp/cvxpy", "sos_multivariate", ok, f"SDP status={prob.status}", optional=True)
    except Exception as e:  # noqa: BLE001
        return CarrierVerdict("sdp/cvxpy", "sos_multivariate", False,
                              f"{type(e).__name__}: {e} (multivariate sos inert; univariate unaffected)",
                              optional=True)


def _check_native_hammer() -> CarrierVerdict:
    """Lean carrier — needs the Lean box (a cold Mathlib compile). Opt-in (serial-Lean discipline)."""
    try:
        from pathlib import Path
        from ztare.gates.v33_preflight_risk_detector import _compile_probe
        repo = Path(__file__).resolve().parents[3]
        lr = (repo / "projects/putnambench_substrate/lean4").resolve()
        ok = _compile_probe("import Mathlib\n\ntheorem _pf_ctrl : True := by trivial\n", lr, "PfCtrl", 200)
        return CarrierVerdict("native_hammer", "native_hammer", ok is True, "': True := by trivial' compiles")
    except Exception as e:  # noqa: BLE001
        return CarrierVerdict("native_hammer", "native_hammer", False, f"{type(e).__name__}: {e}")


def _check_leaf(runtime: str) -> CarrierVerdict:
    """LLM LEAF provider liveness — the solver's prover (the most expensive, most load-bearing carrier). An API
    leaf (kimi/deepseek) that is rate-limited (429), out of credits, or mis-keyed is a DEAD INSTRUMENT: the
    dispatch fails over SILENTLY to the CLI subscription, so the run looks alive while the CONFIGURED leaf never
    ran — a whole campaign can be spent on a degraded prover with no signal. Probe it with a 1-token call BEFORE
    the run. CLI runtimes (claude/codex subscription) are assumed live (no cheap probe), reported optional."""
    try:
        from ztare.leanmill.solver.api_agentic_leaf import is_api_runtime, _client_and_model
    except Exception as e:  # noqa: BLE001
        return CarrierVerdict("leaf", "solver_leaf", False, f"import failed: {e}", optional=True)
    rt = (runtime or "").strip().lower()
    if not is_api_runtime(rt):
        return CarrierVerdict(f"leaf:{rt or 'cli'}", "solver_leaf", True,
                              "CLI/subscription leaf (no API probe)", optional=True)
    try:
        client, model = _client_and_model(rt)
        if client is None:
            return CarrierVerdict(f"leaf:{rt}", "solver_leaf", False, "no client (missing key?)", optional=True)
        resp = client.chat.completions.create(model=model,
                                              messages=[{"role": "user", "content": "ok"}], max_tokens=1)
        live = getattr(resp, "choices", None) is not None
        return CarrierVerdict(f"leaf:{rt}", "solver_leaf", bool(live), f"{model} responded", optional=True)
    except Exception as e:  # noqa: BLE001 — 429 / quota / bad key ⇒ DEAD
        return CarrierVerdict(f"leaf:{rt}", "solver_leaf", False,
                              f"{type(e).__name__}: {str(e)[:80]}", optional=True)


def resolve_live_leaf_runtime(preferred: str, fallbacks: "tuple[str, ...]" = ("deepseek",)) -> "tuple[str, str]":
    """Probe the PREFERRED API leaf; if it is DEAD (429/quota/key), walk `fallbacks` to the first LIVE one and
    return that instead. FAIL-LOUD: prints which leaf was chosen and why — a silent degrade to the CLI is exactly
    what loses a campaign to a throttled provider. Returns (runtime, reason); an empty runtime means "all API
    leaves dead — caller should use the CLI subscription leaf". A non-API `preferred` is returned as-is."""
    try:
        from ztare.leanmill.solver.api_agentic_leaf import is_api_runtime
    except Exception:  # noqa: BLE001
        return preferred, f"could not import api leaf — using '{preferred}' as-is"
    pref = (preferred or "").strip().lower()
    if not is_api_runtime(pref):
        return pref, f"non-API leaf '{pref or 'cli'}' (assumed live)"
    chain = [pref] + [f.strip().lower() for f in fallbacks if f and f.strip().lower() != pref]
    tried: list[str] = []
    for rt in chain:
        v = _check_leaf(rt)
        tried.append(f"{rt}={'LIVE' if v.live else 'DEAD'}")
        if v.live:
            note = (f"[leaf-liveness] using preferred leaf '{rt}' ({'; '.join(tried)})" if rt == pref
                    else f"[leaf-liveness] PREFERRED '{pref}' DEAD → AUTO-SWITCHED to '{rt}' ({'; '.join(tried)})")
            print(note, flush=True)
            return rt, note
    note = f"[leaf-liveness] ALL API leaves DEAD ({'; '.join(tried)}) → CLI subscription leaf"
    print(note, flush=True)
    return "", note


def run_preflight(include_lean: bool = False) -> "list[CarrierVerdict]":
    """All exogenous (Python) carriers always; the Lean carrier only when `include_lean` (it costs a cold
    Mathlib compile and must not run concurrently with another Lean job)."""
    vs = [_check_sympy(), _check_cvc5(), _check_z3(), _check_numpy(), _check_sdp()]
    if include_lean:
        vs.append(_check_native_hammer())
    return vs


def assert_carriers_live(include_lean: bool = False) -> None:
    """Raise (fail-LOUD) if any REQUIRED carrier is dead — call at the head of a lift/A-B runner. An OPTIONAL
    carrier (e.g. the SDP/cvxpy node) that is dead is NOT fatal — the dependent move fail-closes to None."""
    dead = [v for v in run_preflight(include_lean) if not v.live and not v.optional]
    if dead:
        raise RuntimeError("DEAD CARRIER(S) — lift run would record FABRICATED nulls: "
                           + "; ".join(f"{v.name}({v.move}): {v.detail}" for v in dead)
                           + " | wrong interpreter? use ./venv/bin/python with requirements.txt installed.")


def main() -> int:
    include_lean = "--lean" in sys.argv
    vs = run_preflight(include_lean=include_lean)
    print(f"{'carrier':<15} {'move':<26} {'status':<6} detail")
    for v in vs:
        status = "LIVE" if v.live else ("OPT-DEAD" if v.optional else "DEAD")
        print(f"{v.name:<15} {v.move:<26} {status:<8} {v.detail}")
    dead = [v for v in vs if not v.live and not v.optional]
    opt_dead = [v for v in vs if not v.live and v.optional]
    print("\nPREFLIGHT", "GREEN — all required carriers live (lift runs are admissible)" if not dead
          else f"RED — {len(dead)} DEAD required carrier(s): {[v.name for v in dead]} (nulls would be fabricated)")
    if opt_dead:
        print(f"(optional carriers absent — dependent move fail-closes to None: {[v.name for v in opt_dead]})")
    if not include_lean:
        print("(note: native_hammer Lean carrier skipped — pass --lean to include it, needs the Lean box)")
    return 0 if not dead else 1


if __name__ == "__main__":
    sys.exit(main())
