#!/usr/bin/env python3
"""Exact weighted sum-of-squares certificates for UNIVARIATE polynomial nonnegativity (#114) — the
exogenous-compute transport: sympy computes an EXACT rational decomposition p = Σ cᵢ·qᵢ² (cᵢ ∈ ℚ₊),
and the Lean kernel re-verifies it via `nlinarith [sq_nonneg q₁, …]` — providing the squares as hints
is precisely what lets nlinarith close degree ≥ 4 goals it cannot find alone. (Degree ≤ 2 is EXCLUDED
by the caller contract: nlinarith auto-generates degree-2 square terms — the abduce subsumption
lesson; claiming lift there would be a measurement error.)

SCOPE (fail-closed, the abduce-router discipline): UNIVARIATE rational polynomials only. General
multivariate SOS needs an SDP solver + rationalization (not provisioned); returns None there rather
than burning compute on an undecidable-without-SDP search. A None is "no certificate", never "false".

MATH (constructive, exact over ℚ): a univariate p ∈ ℚ[x] is PSD on ℝ iff lc(p) > 0, deg even, and
every irreducible factor of odd multiplicity is a positive-definite quadratic. Then
    p = c · s² · Π qⱼ,   s = Π fᵢ^⌊eᵢ/2⌋,  qⱼ = aⱼ(x + bⱼ/2aⱼ)² + kⱼ   (aⱼ, kⱼ ∈ ℚ₊)
and expanding the product keeps a WEIGHTED-SOS form with rational coefficients throughout — no
irrational square roots needed (the weights ride nlinarith's linear arithmetic).

FALSITY SIGNAL: a sign-change witness (odd-multiplicity real root / negative lc / odd degree) means
p is NOT nonnegative — returned as {"psd": False, "witness_hint": …} so callers can route to falsify.

  python -m ztare.common.sos_certificate --selftest
"""
from __future__ import annotations

from typing import Optional


def sos_certificate(poly_str: str, var: str = "x") -> "Optional[dict]":
    """Compute an exact weighted-SOS certificate for `poly_str` ≥ 0 (univariate over ℚ).
    Returns {"psd": True, "terms": [(coeff_str, poly_str), …], "nlinarith_hints": [...]} with the
    EXACT identity p = Σ coeff·term² (verified by sympy expand before returning — never emits an
    unchecked certificate), or {"psd": False, "witness_hint": str} when p is provably NOT PSD,
    or None (out of scope / failure — fail-closed, not a verdict)."""
    try:
        import sympy as sp
        x = sp.Symbol(var, real=True)
        p = sp.Poly(sp.sympify(poly_str, locals={var: x}), x, domain="QQ")
    except Exception:  # noqa: BLE001 — unparseable / non-polynomial / multivariate ⇒ out of scope
        return None
    if p.degree() <= 0:
        c = p.coeffs()[0] if p.coeffs() else 0
        return ({"psd": True, "terms": [(str(sp.Rational(c)), "1")], "nlinarith_hints": []}
                if c >= 0 else {"psd": False, "witness_hint": "negative constant"})
    if p.degree() % 2 == 1:
        return {"psd": False, "witness_hint": f"odd degree {p.degree()} — sign change at ±∞"}
    lc = p.coeffs()[0]
    if lc < 0:
        return {"psd": False, "witness_hint": "negative leading coefficient — p → -∞"}
    try:
        const, factors = sp.factor_list(p.as_expr())
        # split: even-multiplicity part s², odd-multiplicity residual factors (each must be PD quadratic)
        weighted: "list[tuple]" = [(sp.Rational(const), sp.Integer(1))]   # running weighted-SOS product
        for f, e in factors:
            fp = sp.Poly(f, x)
            if e % 2 == 0:
                # f^e = (f^(e/2))² — a pure square, weight 1
                weighted = _wsos_mul(weighted, [(sp.Integer(1), f ** (e // 2))], x)
                continue
            # odd multiplicity: f^(e-1) is a square; ONE residual f must itself be PSD
            if e > 1:
                weighted = _wsos_mul(weighted, [(sp.Integer(1), f ** ((e - 1) // 2))], x)
            if fp.degree() == 1:
                return {"psd": False,
                        "witness_hint": f"odd-multiplicity real root of {f} — sign change crossing it"}
            if fp.degree() != 2:
                return None   # irreducible quartic+ over ℚ with odd multiplicity — out of v1 scope
            a, b, c2 = [sp.Rational(v) for v in fp.all_coeffs()]
            disc = b * b - 4 * a * c2
            if a <= 0 or disc >= 0:
                return {"psd": False, "witness_hint": f"quadratic factor {f} takes negative values"}
            # a(x + b/2a)² + (4ac−b²)/4a — two weighted squares, all rational
            weighted = _wsos_mul(weighted, [(a, x + b / (2 * a)), (-disc / (4 * a), sp.Integer(1))], x)
        if any(w < 0 for w, _ in weighted):
            return None   # construction invariant violated — refuse rather than emit a wrong cert
        # EXACTNESS GATE: the identity must hold symbolically, or we emit nothing.
        recon = sp.expand(sum(w * q ** 2 for w, q in weighted))
        if sp.expand(recon - p.as_expr()) != 0:
            return None
        terms = [(str(w), str(sp.expand(q))) for w, q in weighted if w != 0]
        hints = [f"sq_nonneg ({_lean_poly(sp.expand(q), var)})" for w, q in weighted
                 if w != 0 and sp.expand(q) != 1]
        return {"psd": True, "terms": terms, "nlinarith_hints": hints}
    except Exception:  # noqa: BLE001 — fail-closed: no certificate, never a wrong one
        return None


def _wsos_mul(A: "list[tuple]", B: "list[tuple]", x) -> "list[tuple]":
    """Product of two weighted-SOS forms stays weighted-SOS: (Σaᵢuᵢ²)(Σbⱼvⱼ²) = Σᵢⱼ aᵢbⱼ(uᵢvⱼ)²."""
    import sympy as sp
    return [(wa * wb, sp.expand(qa * qb)) for wa, qa in A for wb, qb in B]


def _lean_poly(expr, var: str) -> str:
    """Render a sympy univariate polynomial as a Lean-parsable expression (digits, + - * ^, the var).
    Rationals become (a / b); sympy's default printing is already operator-compatible for these."""
    import sympy as sp
    s = sp.sstr(sp.nsimplify(expr))
    return s.replace("**", "^")


def render_verbatim_lean(cert: dict, var: str = "x") -> str:
    """The agent-facing VERBATIM block (same contract as the witness tool): a ready nlinarith call
    with the certificate's squares as hints — copy exactly; the kernel re-verifies regardless."""
    if not cert or not cert.get("psd") or not cert.get("nlinarith_hints"):
        return ""
    hints = ", ".join(cert["nlinarith_hints"])
    return f"===VERBATIM-LEAN-BEGIN===\nnlinarith [{hints}]\n===VERBATIM-LEAN-END==="


# ── MULTIVARIATE SOS via an SDP solver (transport edge #2, 2026-06-13) ─────────────────────────────────
# The univariate path above is exact + closed-form. The MULTIVARIATE Positivstellensatz/SOS problem needs a
# semidefinite program: find Q ⪰ 0 with p = zᵀQz (z = the monomial basis). We solve the SDP NUMERICALLY (cvxpy
# + SCS, an OPT-IN VPS dep — `requirements.txt`; absent ⇒ None, the same fail-closed posture as "SDP not
# provisioned"), then read off square HINTS from the eigendecomposition of Q and hand them to `nlinarith`.
#
# SOUNDNESS — these are HEURISTIC HINTS, not a claimed exact identity (the key difference from the univariate
# path): the numerical Q is rounded to rational square polynomials, so the emitted `nlinarith [sq_nonneg …]`
# may or may not close the goal — and that is FINE, because the LEAN KERNEL re-verifies it (nlinarith searches
# a positive combination of the provided squares; a bad hint set is a MISS, never a false closure). A numerical
# reconstruction check (Σ λᵢ qᵢ² ≈ p) gates emission so we never hand nlinarith pure garbage; a polynomial that
# is nonnegative but NOT SOS (e.g. Motzkin) makes the SDP infeasible ⇒ None (honest no-certificate).
def sos_certificate_multivariate(poly_str: str, variables: "Optional[list]" = None,
                                 *, max_squares: int = 4, recon_tol: float = 1e-6) -> "Optional[dict]":
    """Numerical multivariate SOS hints for `poly_str` ≥ 0. Returns
        {"psd": True, "nlinarith_hints": ["sq_nonneg (…)", …], "multivariate": True, "n_squares": k,
         "heuristic": True, "recon_err": float}
    when an SDP-feasible SOS decomposition is found and reconstructs p within `recon_tol`, else None
    (infeasible / not SOS / cvxpy absent / out of scope — fail-closed, never "false"). UNIVARIATE input is
    delegated to the exact `sos_certificate` (do not pay the SDP for what closed-form solves)."""
    try:
        import sympy as sp
    except Exception:  # noqa: BLE001
        return None
    try:
        expr = sp.expand(sp.sympify(poly_str))
    except Exception:  # noqa: BLE001 — unparseable / non-polynomial ⇒ out of scope
        return None
    syms = sorted(expr.free_symbols, key=lambda s: s.name)
    if variables:
        syms = [sp.Symbol(v) for v in variables]
    if len(syms) <= 1:
        # univariate (or constant) — the exact closed-form path owns this; reuse it (no SDP).
        return sos_certificate(poly_str, var=(syms[0].name if syms else "x")) if syms else None
    try:
        p = sp.Poly(expr, *syms, domain="QQ")
    except Exception:  # noqa: BLE001
        return None
    deg = p.total_degree()
    if deg == 0 or deg % 2 == 1:
        return None   # odd total degree can't be PSD on ℝⁿ (sign change at ∞); constant handled elsewhere
    d = deg // 2
    try:
        import cvxpy as cp
        import numpy as np
    except Exception:  # noqa: BLE001 — cvxpy/numpy is the OPT-IN VPS SDP carrier; absent ⇒ fail-closed None
        return None
    # monomial basis z = all monomials in `syms` of total degree ≤ d (exponent tuples).
    basis = _monomials_upto(len(syms), d)
    n = len(basis)
    if n == 0 or n > 60:   # economics guard: a huge basis blows up the SDP — bail to None
        return None
    # target coefficient map: exponent-tuple → rational coeff of p
    pcoeffs = {tuple(int(e) for e in mono): float(c) for mono, c in zip(p.monoms(), p.coeffs())}
    # products of basis monomials → which (i,j) entries of Q contribute to each product-exponent
    contrib: dict = {}
    for i in range(n):
        for j in range(n):
            key = tuple(basis[i][k] + basis[j][k] for k in range(len(syms)))
            contrib.setdefault(key, []).append((i, j))
    Q = cp.Variable((n, n), symmetric=True)
    constraints = [Q >> 0]
    all_keys = set(contrib) | set(pcoeffs)
    for key in all_keys:
        lhs = cp.sum([Q[i, j] for (i, j) in contrib.get(key, [])]) if contrib.get(key) else 0
        constraints.append(lhs == pcoeffs.get(key, 0.0))
    prob = cp.Problem(cp.Minimize(0), constraints)
    try:
        prob.solve(solver=cp.SCS, verbose=False)
    except Exception:  # noqa: BLE001
        try:
            prob.solve(verbose=False)   # any installed SDP-capable default
        except Exception:  # noqa: BLE001
            return None
    if prob.status not in ("optimal", "optimal_inaccurate"):
        return None   # infeasible ⇒ NOT SOS (e.g. Motzkin) — honest no-certificate
    Qv = Q.value
    if Qv is None:
        return None
    Qv = np.array(Qv, dtype=float)
    Qv = (Qv + Qv.T) / 2.0
    # eigendecomposition → squares: significant nonneg eigenpairs (λᵢ, vᵢ) give λᵢ (vᵢ·z)².
    eigvals, eigvecs = np.linalg.eigh(Qv)
    order = np.argsort(eigvals)[::-1]
    z_monos = [_mono_expr(syms, e) for e in basis]
    squares = []         # (lambda, sympy q)  for reconstruction
    hints = []
    for idx in order:
        lam = float(eigvals[idx])
        if lam <= 1e-7 or len(hints) >= max_squares:
            continue
        vec = eigvecs[:, idx]
        q = _round_combo(vec, z_monos)
        if q is None or sp.expand(q) == 0:
            continue
        squares.append((lam, vec))
        hints.append(f"sq_nonneg ({_lean_multi(q)})")
    if not hints:
        return None
    # numerical reconstruction gate: Σ λᵢ (vᵢ·z)² must approximate p (else the squares are garbage).
    recon_err = _recon_error(syms, basis, squares, p)
    if recon_err > recon_tol * max(1.0, _coeff_scale(p)):
        return None
    return {"psd": True, "nlinarith_hints": hints, "multivariate": True,
            "n_squares": len(hints), "heuristic": True, "recon_err": recon_err}


def _monomials_upto(nvars: int, d: int) -> "list[tuple]":
    """All exponent tuples over `nvars` variables with total degree ≤ d (lexicographic)."""
    def rec(remaining_vars: int, budget: int) -> "list[tuple]":
        if remaining_vars == 0:
            return [()]
        out = []
        for e in range(budget + 1):
            for rest in rec(remaining_vars - 1, budget - e):
                out.append((e, *rest))
        return out
    return rec(nvars, d)


def _mono_expr(syms, exps):
    import sympy as sp
    out = sp.Integer(1)
    for s, e in zip(syms, exps):
        out *= s ** int(e)
    return out


def _round_combo(vec, z_monos):
    """Round a numerical eigenvector to a clean integer combination of the basis monomials (so the emitted
    `sq_nonneg` is a tidy polynomial). Scale the largest entry to ~6, round, drop near-zeros. None if empty."""
    import numpy as np
    import sympy as sp
    m = float(np.max(np.abs(vec)))
    if m < 1e-9:
        return None
    scaled = vec / m * 6.0
    q = sp.Integer(0)
    nonzero = 0
    for coef, mono in zip(scaled, z_monos):
        r = int(round(coef))
        if r != 0:
            q += r * mono
            nonzero += 1
    return q if nonzero else None


def _recon_error(syms, basis, squares, p) -> float:
    """Max-abs coefficient error of Σ λᵢ (vᵢ·z)² vs p, evaluated symbolically (exact monomial match)."""
    import numpy as np
    import sympy as sp
    z = [_mono_expr(syms, e) for e in basis]
    acc = sp.Integer(0)
    for lam, vec in squares:
        lin = sum(float(vec[i]) * z[i] for i in range(len(z)))
        acc += lam * lin ** 2
    diff = sp.expand(acc - p.as_expr())
    try:
        dpoly = sp.Poly(diff, *syms)
        return max((abs(float(c)) for c in dpoly.coeffs()), default=0.0)
    except Exception:  # noqa: BLE001 — diff is ~0 (a constant) ⇒ tiny error
        return float(abs(diff)) if diff.is_number else 1.0


def _coeff_scale(p) -> float:
    return max((abs(float(c)) for c in p.coeffs()), default=1.0)


def _lean_multi(expr) -> str:
    """Render a multivariate sympy polynomial Lean-parsable (`**`→`^`)."""
    import sympy as sp
    return sp.sstr(sp.expand(expr)).replace("**", "^")


def _selftest() -> int:
    import sympy as sp
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    def _check_identity(poly_str, cert):
        x = sp.Symbol("x", real=True)
        p = sp.expand(sp.sympify(poly_str, locals={"x": x}))
        s = sp.expand(sum(sp.Rational(w) * sp.sympify(q, locals={"x": x}) ** 2 for w, q in cert["terms"]))
        return sp.expand(s - p) == 0

    c = sos_certificate("x**4 - 2*x**3 + 2*x**2 - 2*x + 1")
    ok("quartic PSD: certificate found + EXACT identity", c and c["psd"] and _check_identity("x**4 - 2*x**3 + 2*x**2 - 2*x + 1", c))
    ok("quartic: emits nlinarith square hints", c and len(c["nlinarith_hints"]) >= 1)
    c2 = sos_certificate("x**2 + 1")
    ok("x²+1: PSD + exact", c2 and c2["psd"] and _check_identity("x**2 + 1", c2))
    c3 = sos_certificate("(x-1)**2 * (x**2 + 3)")
    ok("mixed square×quadratic: PSD + exact", c3 and c3["psd"] and _check_identity("(x-1)**2 * (x**2 + 3)", c3))
    ok("odd degree ⇒ NOT PSD with witness hint", sos_certificate("x**3 + 1")["psd"] is False)
    ok("negative lc ⇒ NOT PSD", sos_certificate("-x**2 - 1")["psd"] is False)
    # (x−1)³(x−2): even degree, lc>0, but the odd-multiplicity root at 1 forces a sign change
    c_odd = sos_certificate("(x-1)**3 * (x-2)")
    ok("odd-multiplicity real root ⇒ NOT PSD (sign change)",
       c_odd is not None and c_odd["psd"] is False and "sign change" in c_odd["witness_hint"])
    c4 = sos_certificate("(x**2+1)*(x**2+2)")
    ok("product of PD quadratics: PSD + exact (Brahmagupta-free weighted form)",
       c4 and c4["psd"] and _check_identity("(x**2+1)*(x**2+2)", c4))
    ok("multivariate ⇒ None (fail-closed, SDP not provisioned)", sos_certificate("x**2 + y**2") is None)
    ok("non-polynomial ⇒ None", sos_certificate("sin(x)") is None)
    v = render_verbatim_lean(c)
    ok("VERBATIM block renders with ^ not ** and sq_nonneg hints",
       "VERBATIM-LEAN-BEGIN" in v and "sq_nonneg" in v and "**" not in v)
    # delegation: a univariate string handed to the multivariate entrypoint reuses the exact path
    cm_uni = sos_certificate_multivariate("x**4 - 2*x**2 + 1")
    ok("multivariate entrypoint DELEGATES univariate to the exact path",
       cm_uni is not None and cm_uni.get("psd") is True and not cm_uni.get("multivariate"))
    # MULTIVARIATE SDP path — only exercised where cvxpy is provisioned (VPS); skipped (not failed) locally.
    try:
        import cvxpy  # noqa: F401
        _have_sdp = True
    except Exception:  # noqa: BLE001
        _have_sdp = False
    if _have_sdp:
        cm = sos_certificate_multivariate("x**2 + y**2 - 2*x*y")     # = (x-y)² — SOS
        ok("MULTIVARIATE POSITIVE: (x−y)² gets SOS hints", cm is not None and cm["psd"] and cm["n_squares"] >= 1)
        cm2 = sos_certificate_multivariate("x**2 + 2*x*y + y**2 + 1")  # = (x+y)²+1 — SOS
        ok("MULTIVARIATE POSITIVE: (x+y)²+1 gets SOS hints", cm2 is not None and cm2["psd"])
        # Motzkin x⁴y² + x²y⁴ − 3x²y² + 1 is nonnegative but NOT SOS ⇒ SDP infeasible ⇒ None (honest).
        cm3 = sos_certificate_multivariate("x**4*y**2 + x**2*y**4 - 3*x**2*y**2 + 1")
        ok("MULTIVARIATE NEGATIVE: Motzkin (nonneg but not SOS) ⇒ None", cm3 is None)
    else:
        print("  [SKIP] multivariate SDP path — cvxpy not provisioned in this venv (exercised on the VPS)")
    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
