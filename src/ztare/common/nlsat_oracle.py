#!/usr/bin/env python3
"""Nonlinear real-arithmetic DECISION oracle via z3 nlsat (transport edge #1, 2026-06-13).

Real-closed-field quantifier elimination (Tarski) is DECIDABLE — z3's `nlsat` engine decides nonlinear real
arithmetic exactly, where Lean's `nlinarith`/`polyrith` are incomplete heuristics. This is the SCREENING /
routing leg of the nonlinear-real regime (the certificate leg is `sos_certificate` — univariate exact, and
multivariate via the SDP path). The oracle answers, for a goal `∀ x…, φ(x)` over ℝ (or ℤ):

  • VALID    (¬φ is UNSAT)  ⇒ the goal is TRUE — keep proving it (route a polynomial-nonnegativity shape to
                              `sos_certificate` for a kernel-checkable `nlinarith` certificate);
  • INVALID  (¬φ is SAT)    ⇒ a COUNTEREXAMPLE model — the statement is false as written, route to falsify
                              (the dual of `witness_transport.looks_false`, but a COMPLETE decision over ℝ);
  • UNKNOWN  (z3 unknown / untranslatable) ⇒ None — fail-closed, never a verdict.

SOUNDNESS: this is an ADVISORY oracle (a decision, NOT a Lean proof). VALID does not close the goal — the Lean
kernel still needs a proof (the SOS certificate, or the agent's tactic). It only tells the agent which way to
spend effort; the kernel-proved goal / kernel-proved ¬G remain the only verdicts. A mistranslation can only
make the oracle return the WRONG advice or None, never mint a closure (there is no closure here to mint).

TRANSLATION (conservative, fail-closed): a recursive-descent over the logical connectives (→ ∨ ∧ ¬, lowest→
highest) with sympy parsing the atomic relations, then a sympy→z3 map over polynomial/rational arithmetic.
Any construct outside that fragment (transcendental, set/Finset, a binder we can't type) ⇒ None.

  python -m ztare.common.nlsat_oracle --selftest
"""
from __future__ import annotations

import re
from typing import Optional

# Unicode → ASCII tokens for the connectives/relations the agent passes in Lean surface syntax.
_REL = {"≤": "<=", "≥": ">=", "≠": "!=", "→": "->", "∧": "&", "∨": "|", "¬": "~", "↔": "<->"}
_FIELD_TYPES = {"ℝ", "Real", "ℚ", "Rat"}
_INT_TYPES = {"ℤ", "Int", "ℕ", "Nat"}
_NAT_TYPES = {"ℕ", "Nat"}


def _normalize(body: str) -> str:
    s = body
    for u, a in _REL.items():
        s = s.replace(u, a)
    return s


def _strip_forall(goal: str) -> "tuple[str, dict]":
    """Strip a leading `∀ <binders>, <body>` and return (body, {var: 'int'|'real'|'nat'}). A bare body
    (no binder) yields ({}, body) — free symbols are then treated as universally-quantified reals."""
    t = (goal or "").strip()
    m = re.match(r"^\s*(?:∀|\\forall|forall)\s+(.*?),\s*(.+)$", t, re.DOTALL)
    if not m:
        return t, {}
    binders, body = m.group(1), m.group(2)
    types: dict = {}
    # binder groups like `(x y : ℝ) (n : ℕ)` or a bare `x y` (untyped ⇒ real)
    for grp, typ in re.findall(r"\(([^():]+):\s*([^()]+)\)", binders):
        kind = ("nat" if typ.strip() in _NAT_TYPES else "int" if typ.strip() in _INT_TYPES
                else "real" if typ.strip() in _FIELD_TYPES else "")
        if not kind:
            return body, {"__unsupported__": typ.strip()}   # a type we don't model ⇒ caller bails
        for nm in grp.replace(",", " ").split():
            if re.fullmatch(r"[A-Za-z_][\w']*", nm):
                types[nm] = kind
    return body, types


def _const_z3(expr, idom: bool):
    """A sympy numeric constant → a z3 value of the goal's domain sort. In the INTEGER domain a non-integer
    rational constant is OUT OF SCOPE (integer division is not polynomial-integer arithmetic) ⇒ raise → None,
    NEVER silently coerce (coercing would let `n/2` be reasoned as a real and reintroduce the int≠real bug)."""
    import sympy as sp
    import z3
    r = sp.Rational(expr)
    if idom:
        if r.q != 1:
            raise ValueError(f"non-integer constant {r} in an integer-domain goal")
        return z3.IntVal(int(r))
    return z3.RealVal(str(r))


def _sympy_to_z3(expr, zvars: dict, idom: bool):
    """Map a sympy ARITHMETIC expression to a z3 term over the given z3 variables, in the goal's domain
    (`idom`=integer ⇒ z3.Int sort + IntVal constants, else real). Raises on any node we do not model
    (transcendental, non-natural power, non-integer constant in ℤ) ⇒ the caller turns that into a None verdict."""
    import sympy as sp
    if isinstance(expr, sp.Symbol):
        return zvars[expr.name]
    if isinstance(expr, (sp.Integer, sp.Rational, sp.Float)):
        return _const_z3(expr, idom)
    if isinstance(expr, sp.Add):
        out = _sympy_to_z3(expr.args[0], zvars, idom)
        for a in expr.args[1:]:
            out = out + _sympy_to_z3(a, zvars, idom)
        return out
    if isinstance(expr, sp.Mul):
        out = _sympy_to_z3(expr.args[0], zvars, idom)
        for a in expr.args[1:]:
            out = out * _sympy_to_z3(a, zvars, idom)
        return out
    if isinstance(expr, sp.Pow):
        base, exp = expr.args
        if not (isinstance(exp, sp.Integer) and int(exp) >= 0):
            raise ValueError(f"non-natural power {exp}")   # division (x^-1) / fractional power ⇒ out of scope
        out = _const_z3(sp.Integer(1), idom)
        b = _sympy_to_z3(base, zvars, idom)
        for _ in range(int(exp)):
            out = out * b
        return out
    raise ValueError(f"unmodelled node {type(expr).__name__}: {expr}")


def _atom_to_z3(atom: str, zvars: dict, idom: bool):
    """A single relation `lhs REL rhs` → a z3 bool. None-raises on a non-relation / unmodelled atom."""
    import sympy as sp
    rels = [("<=", lambda a, b: a <= b), (">=", lambda a, b: a >= b), ("!=", lambda a, b: a != b),
            ("<", lambda a, b: a < b), (">", lambda a, b: a > b), ("=", lambda a, b: a == b)]
    s = atom.strip().strip("()").strip()
    for tok, op in rels:
        # split on the FIRST top-level occurrence (atoms are parenthesis-stripped, simple relations)
        idx = _find_rel(s, tok)
        if idx >= 0:
            lhs = sp.sympify(s[:idx], locals={k: sp.Symbol(k) for k in zvars})
            rhs = sp.sympify(s[idx + len(tok):], locals={k: sp.Symbol(k) for k in zvars})
            return op(_sympy_to_z3(lhs, zvars, idom), _sympy_to_z3(rhs, zvars, idom))
    raise ValueError(f"not a relation: {atom}")


def _find_rel(s: str, tok: str) -> int:
    """Index of the first top-level `tok` not adjacent to another relation char (so `<=` isn't matched as
    `<`), respecting parenthesis depth. -1 if none."""
    depth = 0
    i = 0
    while i < len(s):
        c = s[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif depth == 0 and s[i:i + len(tok)] == tok:
            nb = s[i - 1] if i > 0 else ""
            na = s[i + len(tok)] if i + len(tok) < len(s) else ""
            if tok in ("<", ">", "=") and (nb in "<>=!" or na in "=<>"):
                i += 1
                continue
            return i
        i += 1
    return -1


def _split_top(s: str, tok: str) -> "list[str]":
    """Split `s` on top-level `tok` (parenthesis-aware). Returns [s] if `tok` absent."""
    parts, depth, last, i = [], 0, 0, 0
    while i < len(s):
        c = s[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif depth == 0 and s[i:i + len(tok)] == tok:
            parts.append(s[last:i]); i += len(tok); last = i; continue
        i += 1
    parts.append(s[last:])
    return parts


def _formula_to_z3(s: str, zvars: dict, idom: bool):
    """Recursive descent: -> (lowest) , | , & , ~ , then atoms. z3 bool. Raises on the unmodelled."""
    import z3
    s = s.strip()
    while s.startswith("(") and _matched(s):
        s = s[1:-1].strip()
    imp = _split_top(s, "->")
    if len(imp) > 1:
        # right-assoc: a -> b -> c == a -> (b -> c); fold from the right
        rhs = _formula_to_z3(imp[-1], zvars, idom)
        for part in reversed(imp[:-1]):
            rhs = z3.Implies(_formula_to_z3(part, zvars, idom), rhs)
        return rhs
    ors = _split_top(s, "|")
    if len(ors) > 1:
        return z3.Or(*[_formula_to_z3(p, zvars, idom) for p in ors])
    ands = _split_top(s, "&")
    if len(ands) > 1:
        return z3.And(*[_formula_to_z3(p, zvars, idom) for p in ands])
    if s.startswith("~"):
        return z3.Not(_formula_to_z3(s[1:], zvars, idom))
    return _atom_to_z3(s, zvars, idom)


def _matched(s: str) -> bool:
    """True iff the OUTER parens of `s` wrap the whole string (so stripping them is safe)."""
    if not (s.startswith("(") and s.endswith(")")):
        return False
    depth = 0
    for i, c in enumerate(s):
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0 and i != len(s) - 1:
                return False
    return depth == 0


def nlsat_decide(goal: str, timeout_ms: int = 8000) -> "Optional[dict]":
    """Decide a nonlinear real/integer arithmetic goal `∀ x…, φ`. Returns
        {"valid": True}                                  — ¬φ UNSAT (the goal is TRUE);
        {"valid": False, "counterexample": {var: val}}   — ¬φ SAT (false as written — route to falsify);
      or None — UNKNOWN / untranslatable / no z3 (fail-closed, never a verdict)."""
    try:
        import sympy as sp  # noqa: F401  (used transitively by the translators)
        import z3
    except Exception:  # noqa: BLE001 — z3 is a carrier dep; absence ⇒ no verdict
        return None
    body, types = _strip_forall(goal)
    if types.get("__unsupported__"):
        return None
    body = _normalize(body)
    # collect variable names: declared binders ∪ free identifiers in the body (default real)
    names = set(types)
    for tok in re.findall(r"[A-Za-z_][\w']*", body):
        if tok not in ("abs",):
            names.add(tok)
    if not names:
        return None
    # DOMAIN: integer iff EVERY declared binder is ℤ/ℕ (and at least one is declared). Otherwise real —
    # the safe default. Modelling ℤ as ℝ was UNSOUND for the INVALID verdict (a real counterexample like
    # n=1/2 need NOT be an integer ⇒ `∀ n:ℤ, n²≥n` was wrongly called false); reasoning over ℤ (z3.Int)
    # keeps VALID/INVALID sound on integer goals (z3's nonlinear-int is incomplete ⇒ may return unknown→None).
    declared = {k: v for k, v in types.items() if v in ("int", "nat", "real")}
    idom = bool(declared) and all(v in ("int", "nat") for v in declared.values())
    zvars: dict = {}
    nonneg = []
    for nm in sorted(names):
        kind = types.get(nm, "real")
        if idom:
            zvars[nm] = z3.Int(nm)
            if kind == "nat":
                nonneg.append(zvars[nm] >= 0)
        else:
            zvars[nm] = z3.Real(nm)   # real/mixed/untyped goal — RCF nlsat domain
    try:
        phi = _formula_to_z3(body, zvars, idom)
    except Exception:  # noqa: BLE001 — outside the modelled fragment ⇒ honest None
        return None
    s = z3.Solver()
    s.set("timeout", int(timeout_ms))
    for c in nonneg:
        s.add(c)
    s.add(z3.Not(phi))
    r = s.check()
    if r == z3.unsat:
        return {"valid": True}
    if r == z3.sat:
        m = s.model()
        cex = {}
        for nm in sorted(names):
            try:
                val = m.eval(zvars[nm], model_completion=True)
                cex[nm] = str(val)
            except Exception:  # noqa: BLE001
                cex[nm] = "?"
        return {"valid": False, "counterexample": cex}
    return None   # z3 unknown ⇒ fail-closed


def _selftest() -> int:
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    # VALID: AM-GM-flavoured nonlinear truth over ℝ (x²+y² ≥ 2xy) — nlsat decides it true.
    r = nlsat_decide("∀ (x y : ℝ), x*x + y*y >= 2*x*y")
    ok("VALID: x²+y² ≥ 2xy decided TRUE", r is not None and r.get("valid") is True)
    # VALID: a univariate quartic nonnegativity (x⁴ - 2x² + 1 = (x²-1)² ≥ 0)
    r2 = nlsat_decide("∀ (x : ℝ), x^4 - 2*x^2 + 1 >= 0")
    ok("VALID: (x²−1)² ≥ 0 decided TRUE", r2 is not None and r2.get("valid") is True)
    # INVALID: a FALSE nonlinear claim ⇒ counterexample (x²+1 ≥ 3 fails near 0)
    r3 = nlsat_decide("∀ (x : ℝ), x*x + 1 >= 3")
    ok("INVALID: x²+1 ≥ 3 ⇒ counterexample returned",
       r3 is not None and r3.get("valid") is False and "counterexample" in r3)
    # VALID with hypothesis (implication): 0 ≤ x → x ≤ x*x + 1 ... actually x ≤ x²+1 holds ∀x; use a real impl
    r4 = nlsat_decide("∀ (x : ℝ), (x >= 2) -> (x*x >= 4)")
    ok("VALID: x≥2 → x²≥4 decided TRUE", r4 is not None and r4.get("valid") is True)
    # INVALID implication: x≥2 → x²≥9 is false at x=2
    r5 = nlsat_decide("∀ (x : ℝ), (x >= 2) -> (x*x >= 9)")
    ok("INVALID: x≥2 → x²≥9 ⇒ counterexample", r5 is not None and r5.get("valid") is False)
    # OUT OF SCOPE: transcendental ⇒ None
    ok("OUT OF SCOPE: sin(x) ⇒ None", nlsat_decide("∀ (x : ℝ), sin(x) <= 1") is None)
    # OUT OF SCOPE: unsupported binder type ⇒ None
    ok("OUT OF SCOPE: Finset binder ⇒ None", nlsat_decide("∀ (s : Finset ℕ), s.card >= 0") is None)
    # ℕ nonnegativity is added: ∀ n:ℕ, n*n ≥ 0 is trivially valid (and the n≥0 constraint is harmless)
    r6 = nlsat_decide("∀ (n : ℕ), n + 1 >= 1")
    ok("ℕ binder: n+1 ≥ 1 decided TRUE (nonneg constraint added)", r6 is not None and r6.get("valid") is True)
    # SOUNDNESS REGRESSION (2026-06-13 bug): an ℤ goal TRUE over ℤ but FALSE over ℝ must reason over ℤ.
    # `∀ n:ℤ, n²≥n` is true (n(n-1)≥0 for all integers); modelling ℤ as ℝ wrongly returned invalid (n=1/2).
    r7 = nlsat_decide("∀ (n : ℤ), n*n >= n")
    ok("ℤ DOMAIN: n²≥n decided VALID over ℤ (not the spurious real n=1/2 counterexample)",
       r7 is not None and r7.get("valid") is True)
    # the SAME body over ℝ is correctly INVALID (x=1/2) — the domain genuinely changes the verdict
    r8 = nlsat_decide("∀ (x : ℝ), x*x >= x")
    ok("ℝ DOMAIN: same body x²≥x correctly INVALID over ℝ", r8 is not None and r8.get("valid") is False)
    # an integer-domain goal with a non-integer constant is OUT OF SCOPE (no silent real coercion)
    ok("ℤ DOMAIN: non-integer constant (n/2) ⇒ None (no unsound real coercion)",
       nlsat_decide("∀ (n : ℤ), n/2 >= 0") is None)
    # a TRUE integer inequality that is also true over ℝ stays valid
    r9 = nlsat_decide("∀ (n : ℤ), (n >= 3) -> (n*n >= 2*n)")
    ok("ℤ DOMAIN: n≥3 → n²≥2n decided VALID", r9 is not None and r9.get("valid") is True)

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
