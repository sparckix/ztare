#!/usr/bin/env python3
"""Gröbner-basis ideal-membership certificates → Lean `linear_combination` (transport edge #3, 2026-06-13).

The exogenous-compute transport, witness-transport shape: a MULTIVARIATE polynomial EQUALITY that follows
from polynomial-equation HYPOTHESES is ideal membership — decidable by Gröbner bases, an LLM blind spot that
Lean's `linarith`/`nlinarith` cannot do and `polyrith` only does via a flaky Sage round-trip. SymPy computes
the exact COFACTORS, we emit a `linear_combination` the Lean kernel RE-VERIFIES (it discharges the residual
by `ring`). A wrong cofactor merely fails to compile (a MISS) — zero false-closure risk, the kernel arbitrates.

    membership-FINDING (SymPy polynomial division — exact over ℚ)  ⟂  PROVING (the Lean kernel / `ring`)

MATH. Given hypotheses hᵢ : Aᵢ = Bᵢ (i.e. generators gᵢ = Aᵢ − Bᵢ) and a goal L = R, the goal holds in the
quotient ring iff f := L − R ∈ ⟨g₁,…,gₖ⟩. The polynomial division algorithm gives f = Σ Qᵢ·gᵢ + r with the
Qᵢ EXACT over ℚ; when the remainder r = 0, f = Σ Qᵢ·gᵢ is a true identity (independent of whether {gᵢ} is a
Gröbner basis — the division identity always holds), so `linear_combination Σ Qᵢ·hᵢ` closes the goal.

SCOPE (fail-closed, the abduce-router discipline): v1 reduces against the RAW generators (`sympy.reduced`);
it emits IFF the remainder is exactly 0. A goal that is in the ideal but whose raw division does not terminate
at 0 (needs the Gröbner basis + cofactor lift) returns None rather than a wrong/partial certificate — the
kernel never sees a bad cert, and a None is "no certificate", never "false". Rational-coefficient polynomials
only; a parse failure / non-polynomial input ⇒ None.

  python -m ztare.common.groebner_cert --selftest
"""
from __future__ import annotations

from typing import Optional


def _lean_expr(expr) -> str:
    """Render a sympy polynomial as a Lean-parsable expression (`**`→`^`; rationals stay `a/b`)."""
    import sympy as sp
    return sp.sstr(sp.expand(expr)).replace("**", "^")


def _parse_eq(s: str, symbols, locals_) -> "Optional[tuple]":
    """Parse `lhs = rhs` (a single `=`, not `==`/`<=`) into (lhs_expr, rhs_expr). None if not an equation."""
    import sympy as sp
    body = (s or "").strip()
    # split on the FIRST bare `=` that is not part of <= >= == != (Lean/agent never sends those in an eq hyp,
    # but be defensive). A polynomial equation has exactly one `=`.
    import re
    parts = re.split(r"(?<![<>=!])=(?!=)", body)
    if len(parts) != 2:
        return None
    try:
        lhs = sp.sympify(parts[0], locals=locals_)
        rhs = sp.sympify(parts[1], locals=locals_)
    except Exception:  # noqa: BLE001
        return None
    return lhs, rhs


def groebner_certificate(hypotheses: "list[str]", goal: str,
                         variables: "Optional[list[str]]" = None) -> "Optional[dict]":
    """Find a `linear_combination` cofactor certificate for `goal` (an equation `L = R`) from the equation
    `hypotheses` (each `Aᵢ = Bᵢ`). Returns
        {"cofactors": [coeff_str, …], "hyp_count": k, "linear_combination": "<lean expr>", "names": ["h0",…]}
    with the EXACT identity L − R = Σ coeffᵢ·(Aᵢ − Bᵢ) (verified by sympy.expand before returning — never an
    unchecked cert), or None (no certificate / out of scope — fail-closed, never a verdict).

    The emitted Lean tactic is `linear_combination <c0>*h0 + <c1>*h1 + …`; the caller/agent must have the
    hypotheses in context under the names returned in `names` (default h0,h1,…) — or rename to match."""
    try:
        import sympy as sp
    except Exception:  # noqa: BLE001 — sympy is a hard carrier dep; absence ⇒ no cert (fail-closed)
        return None
    if not goal or not str(goal).strip():
        return None
    hyps = [h for h in (hypotheses or []) if str(h).strip()]
    if not hyps:
        return None   # no hypotheses ⇒ a pure ring identity; that is `ring`'s job, not this move (no lift)
    # Resolve the variable set: explicit, else the union of free symbols across goal+hyps.
    locals_: dict = {}
    if variables:
        for v in variables:
            locals_[v] = sp.Symbol(v)
    try:
        g_eq = _parse_eq(goal, None, locals_)
        h_eqs = [_parse_eq(h, None, locals_) for h in hyps]
    except Exception:  # noqa: BLE001
        return None
    if g_eq is None or any(e is None for e in h_eqs):
        return None
    f = sp.expand(g_eq[0] - g_eq[1])
    gens_poly = [sp.expand(a - b) for a, b in h_eqs]
    if all(gp == 0 for gp in gens_poly):
        return None
    # gather generator symbols (the polynomial ring variables)
    syms = sorted(set().union(*[e.free_symbols for e in [f, *gens_poly]]), key=lambda s: s.name)
    if not syms:
        return None   # everything is constant — not a polynomial-ideal problem
    try:
        # Division against the RAW generators (NOT a Gröbner basis): f = Σ Q_i g_i + r, exact over ℚ.
        Q, r = sp.reduced(f, gens_poly, *syms, order="grevlex")
        if sp.expand(r) != 0:
            return None   # not in the ideal by raw division ⇒ fail-closed (no partial cert)
        # EXACTNESS GATE: the identity must hold symbolically or we emit nothing.
        if sp.expand(f - sum(q * g for q, g in zip(Q, gens_poly))) != 0:
            return None
    except Exception:  # noqa: BLE001 — fail-closed: no certificate, never a wrong one
        return None
    names = [f"h{i}" for i in range(len(gens_poly))]
    terms = []
    cofactors = []
    for q, nm in zip(Q, names):
        qe = sp.expand(q)
        cofactors.append(_lean_expr(qe))
        if qe == 0:
            continue
        terms.append(f"({_lean_expr(qe)}) * {nm}")
    if not terms:
        return None   # all cofactors zero ⇒ goal followed from no hypothesis (ring's job, no lift)
    return {
        "cofactors": cofactors,
        "hyp_count": len(gens_poly),
        "names": names,
        "linear_combination": "linear_combination " + " + ".join(terms),
    }


def render_verbatim_lean(cert: "Optional[dict]") -> str:
    """Agent-facing VERBATIM block (same contract as witness/sos): a ready `linear_combination` call; copy
    exactly, the kernel re-verifies. Empty when there is no certificate."""
    if not cert or not cert.get("linear_combination"):
        return ""
    return f"===VERBATIM-LEAN-BEGIN===\n{cert['linear_combination']}\n===VERBATIM-LEAN-END==="


def _selftest() -> int:
    import sympy as sp
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    def _identity_holds(hyps, goal, cert):
        """The emitted cofactors must reconstruct L−R exactly over ℚ."""
        loc = {}
        gl, gr = _parse_eq(goal, None, loc)
        f = sp.expand(gl - gr)
        acc = 0
        for c, h in zip(cert["cofactors"], hyps):
            a, b = _parse_eq(h, None, loc)
            acc += sp.sympify(c) * (a - b)
        return sp.expand(f - acc) == 0

    # POSITIVE: a multivariate identity that genuinely needs the hypotheses (not pure ring).
    # h0: x = y+1, h1: y = z*z  ⊢  x = z*z + 1   (f = x - z² - 1 = 1·(x-(y+1)) + 1·(y - z²))
    h = ["x = y + 1", "y = z*z"]
    g = "x = z*z + 1"
    c = groebner_certificate(h, g)
    ok("POSITIVE: linear chain — cert found", c is not None and "linear_combination" in c["linear_combination"])
    ok("POSITIVE: cofactor identity holds exactly", c is not None and _identity_holds(h, g, c))
    ok("POSITIVE: references the hyp names h0/h1", c is not None and c["names"] == ["h0", "h1"])

    # POSITIVE: a nonlinear cofactor (cofactor is itself a polynomial, not a constant).
    # h0: a = b  ⊢  a*a = b*b   (f = a²-b² = (a+b)·(a-b), cofactor a+b)
    h2 = ["a = b"]
    g2 = "a*a = b*b"
    c2 = groebner_certificate(h2, g2)
    ok("POSITIVE: nonlinear cofactor (a+b) found + exact", c2 is not None and _identity_holds(h2, g2, c2))
    ok("POSITIVE: cofactor is a polynomial, not a bare constant",
       c2 is not None and any(s in c2["cofactors"][0] for s in ("a", "b")))

    # NEGATIVE: goal NOT implied by the hypotheses ⇒ None (fail-closed, no false cert).
    ok("NEGATIVE: goal not in the ideal ⇒ None",
       groebner_certificate(["x = y"], "x = y + 1") is None)
    # NEGATIVE: no hypotheses ⇒ None (pure ring identity is `ring`'s job, no lift here).
    ok("NEGATIVE: no hypotheses ⇒ None (no lift over `ring`)",
       groebner_certificate([], "x + y = y + x") is None)
    # NEGATIVE: non-equation goal ⇒ None.
    ok("NEGATIVE: inequality goal ⇒ None", groebner_certificate(["x = y"], "x <= y") is None)
    # NEGATIVE: non-polynomial ⇒ None.
    ok("NEGATIVE: transcendental ⇒ None", groebner_certificate(["x = y"], "sin(x) = sin(y)") is None)

    v = render_verbatim_lean(c)
    ok("VERBATIM block renders with ^ not ** and linear_combination",
       "VERBATIM-LEAN-BEGIN" in v and "linear_combination" in v and "**" not in v)

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
