#!/usr/bin/env python3
"""Fail-loud POSITIVE-CONTROL verifier for the leanmill solver backends (cvc5 / numpy / z3 / Isabelle).

Dead-instrument discipline: a move that depends on an external solver must NOT silently no-op on a
mis-provisioned box. This asserts each backend actually COMPUTES the right answer (not just imports),
so a broken install fails the deploy LOUDLY instead of turning the move into an invisible inert stub.

  - cvc5  (MOVE_ABDUCE)       : `get-abduct` returns the expected `(define-fun A …)` for a known query.
  - numpy (MOVE_FUNCTOR_LIFT) : K2 adjacency spectrum is exactly {-1, +1}.
  - z3    (cross-vote / SMT + nlsat edge #1) : a known-SAT formula is SAT.
  - sdp   (multivariate SOS, edge #2) : cvxpy SOLVES a tiny SDP (OPTIONAL — multivariate `sos` fail-closes).
  - Isabelle (MOVE_SLEDGEHAMMER): OPTIONAL — only checked when ZTARE_ISABELLE_SERVER is set (a /health ping).

FUTURE NODES (the mechanized pattern for a new transport substrate): (1) add the dep to requirements.txt
(prepare_lean_backends.sh step 6b pip-installs it into the venv on every node); (2) add a `check_*` here +
a `_check_*` in src/ztare/leanmill/preflight_carriers.py (so a dead carrier fails LOUD, never a silent stub).

Exit 0 iff every REQUIRED backend passes. cvc5/Isabelle are treated as OPTIONAL by default (the moves are
default-OFF + fail-closed) unless `--require cvc5,isabelle` is passed — so a box that doesn't run those
moves isn't forced to carry their deps, but a box that DOES can assert them.

Usage:
  python scripts/public/control/verify_solver_backends.py            # numpy+z3 required; cvc5/isabelle advisory
  python scripts/public/control/verify_solver_backends.py --require cvc5
  python scripts/public/control/verify_solver_backends.py --self-test # alias for the default run
"""
from __future__ import annotations

import argparse
import os
import sys

REPO = None
try:
    from pathlib import Path
    REPO = Path(__file__).resolve().parents[3]
    sys.path.insert(0, str(REPO / "src"))
except Exception:  # noqa: BLE001
    pass


def check_numpy() -> "tuple[bool, str]":
    try:
        from ztare.leanmill.solver.spectral_lift import compute_spectral_bound
    except Exception as e:  # noqa: BLE001
        return False, f"import spectral_lift failed: {e!r}"
    k2 = compute_spectral_bound('{"matrix": [[0,1],[1,0]]}')
    if k2 is None:
        return False, "numpy ABSENT (compute_spectral_bound returned None)"
    eig = sorted(k2.get("eigenvalues") or [])
    if eig != [-1.0, 1.0]:
        return False, f"numpy spectral WRONG: K2 eigenvalues={eig} (expected [-1.0, 1.0])"
    return True, f"numpy OK (K2 spectrum {eig})"


def check_z3() -> "tuple[bool, str]":
    try:
        import z3
    except Exception as e:  # noqa: BLE001
        return False, f"z3 ABSENT: {e!r}"
    x = z3.Int("x")
    s = z3.Solver()
    s.add(x > 5, x < 8)
    if s.check() != z3.sat:
        return False, "z3 returned non-SAT for a known-SAT formula"
    return True, f"z3 OK ({z3.get_version_string()})"


def check_cvc5() -> "tuple[bool, str]":
    try:
        from ztare.leanmill.solver.abduction import _cvc5_available, _cvc5_abduct
    except Exception as e:  # noqa: BLE001
        return False, f"import abduction failed: {e!r}"
    if not _cvc5_available():
        return False, "cvc5 ABSENT (no binary on PATH/ZTARE_CVC5_BIN and no `cvc5` pip wheel)"
    q = "(set-logic QF_LIA)\n(declare-const x Int)\n(assert (> x 5))\n(get-abduct A (> x 10))\n"
    raw = _cvc5_abduct(q, 10)
    if not raw or "define-fun A" not in raw:
        return False, f"cvc5 get-abduct produced no abduct (raw={raw!r})"
    return True, f"cvc5 OK (abduct={raw})"


def check_sdp() -> "tuple[bool, str]":
    """SDP carrier (transport edge #2 — multivariate SOS). cvxpy must actually SOLVE a tiny SDP, not just
    import (the dead-instrument discipline). OPTIONAL by default — multivariate `sos` fail-closes to None
    without it, the univariate path is unaffected — `--require sdp` to assert it on a solver node."""
    try:
        import cvxpy as cp
        import numpy as np
    except Exception as e:  # noqa: BLE001
        return False, f"cvxpy/numpy ABSENT (multivariate SOS inert): {e!r}"
    try:
        X = cp.Variable((2, 2), symmetric=True)
        prob = cp.Problem(cp.Minimize(cp.trace(X)), [X >> 0, X[0, 0] == 1, X[1, 1] == 1])
        prob.solve(solver=cp.SCS, verbose=False)
        ok = prob.status in ("optimal", "optimal_inaccurate") and X.value is not None
        return (ok, f"cvxpy OK (SDP status={prob.status}, ver {getattr(cp,'__version__','?')})" if ok
                else f"cvxpy SDP did not solve (status={prob.status})")
    except Exception as e:  # noqa: BLE001
        return False, f"cvxpy SDP solve FAILED: {e!r}"


def check_isabelle() -> "tuple[bool, str]":
    base = os.environ.get("ZTARE_ISABELLE_SERVER", "").strip()
    if not base:
        return False, "ZTARE_ISABELLE_SERVER unset (sledgehammer fail-closed no-op)"
    try:
        import requests
        r = requests.get(base.rstrip("/") + "/health", timeout=10)
        if r.status_code == 200:
            return True, f"Isabelle server OK ({base})"
        return False, f"Isabelle server {base} /health -> HTTP {r.status_code}"
    except Exception as e:  # noqa: BLE001
        return False, f"Isabelle server {base} unreachable: {e!r}"


CHECKS = {"numpy": check_numpy, "z3": check_z3, "cvc5": check_cvc5, "sdp": check_sdp,
          "isabelle": check_isabelle}
DEFAULT_REQUIRED = {"numpy", "z3"}            # always-on backends (cross-vote + functor_lift exogenous compute)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--require", default="", help="comma list of OPTIONAL backends to also REQUIRE (cvc5,isabelle)")
    ap.add_argument("--self-test", action="store_true", help="default run (numpy+z3 required)")
    args = ap.parse_args()
    required = set(DEFAULT_REQUIRED)
    if args.require:
        required |= {x.strip() for x in args.require.split(",") if x.strip()}

    failures = []
    for name, fn in CHECKS.items():
        ok, msg = fn()
        req = name in required
        tag = "PASS" if ok else ("FAIL" if req else "skip")
        print(f"  [{tag}] {name}: {msg}")
        if req and not ok:
            failures.append(name)
    if failures:
        print(f"SOLVER BACKENDS: FAILED required = {failures}")
        return 1
    print("SOLVER BACKENDS: all required backends green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
