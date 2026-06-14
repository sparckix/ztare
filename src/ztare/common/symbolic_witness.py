"""General-purpose SYMBOLIC WITNESS computation (SymPy) — substrate-agnostic, 2026-06-07.

The reusable half of cross-substrate witness transport: given an algebraic constraint + the variables to
solve for, FIND a satisfying witness via SymPy, run in a bounded + import-whitelisted subprocess. NO Lean, no
LLM, no leanmill specifics — leanmill (and any other caller, e.g. autoresearch) imports this and adds its own
substrate glue (the Lean ∃-gate, the tactic injection, the kernel re-verify live in
`ztare.leanmill.solver.witness_transport`).

Safety: the solver script — whether built here or authored by a model — is STATICALLY import-whitelisted
(`script_is_safe`) and run with `-I` (isolated) + a hard wall-clock timeout. The static guard blocks
os/subprocess/socket/open/eval/…, so a script can only `import sympy/json/math/…` — no FS or network reach,
independent of any env sandbox. SMT/Z3 would be a future extension here (absent today).
"""
from __future__ import annotations

import json

# The sandboxed-execution half now lives in the CANONICAL shared home `ztare.common.sandboxed_python` (used by
# autoresearch too — no parallel subprocess wrappers). `run_solver_script` is kept as a back-compat alias of
# `run_guarded_script` so existing leanmill imports (`witness_transport`) are unchanged. This module owns only
# the MATH (the witness / counterexample / recurrence / linear-system script BUILDERS).
from ztare.common.sandboxed_python import script_is_safe, run_guarded_script as run_solver_script  # noqa: F401


def build_existential_script(sympy_eq: str, var_names: "list[str]", integer: bool = False) -> str:
    """Build a self-contained SymPy script for `∃ <vars>, <sympy_eq>` (a single equality, `lhs == rhs` ALREADY
    in SymPy surface syntax — the CALLER does any substrate→SymPy translation). Solves in the domain (integer
    or real) and prints a JSON witness. Empty `var_names` ⇒ '' (nothing to solve)."""
    if not var_names or "==" not in sympy_eq:
        return ""
    lhs, rhs = sympy_eq.split("==", 1)
    syms = ", ".join(var_names)                 # LHS unpack (single ⇒ Symbol, multi ⇒ tuple)
    sym_arg = " ".join(var_names)               # symbols('x y') — SPACE-joined (a list would nest [x])
    assum = "integer=True" if integer else "real=True"
    loc = "{" + ", ".join(f"'{v}': {v}" for v in var_names) + "}"   # bind the ASSUMED symbols into sympify
    return (
        "import sympy, json\n"
        f"{syms} = sympy.symbols('{sym_arg}', {assum})\n"
        f"_loc = {loc}\n"
        "sol=None\n"
        "try:\n"   # sympify INSIDE the try → a malformed equation yields a clean ok:false, not a crash
        f"    expr = sympy.Eq(sympy.sympify({json.dumps(lhs.strip())}, locals=_loc), "
        f"sympy.sympify({json.dumps(rhs.strip())}, locals=_loc))\n"
        f"    ds = sympy.solve(expr, [{syms}], dict=True)\n"
        f"    sol = [d for d in ds if all(getattr(v, 'is_integer', False) for v in d.values())] if {integer} else ds\n"
        "except Exception:\n"
        "    sol=None\n"
        "if sol:\n"
        f"    d=sol[0]; cand=[d.get(s, None) for s in [{syms}]]\n"
        # reject PARAMETRIC/underdetermined solutions (a free symbol can't be injected as a concrete Lean
        # witness); only a fully-concrete (symbol-free) assignment is usable.
        "    if all(c is not None and not getattr(c, 'free_symbols', set()) for c in cand):\n"
        "        print(json.dumps({'ok': True, 'witnesses': [str(c) for c in cand]}))\n"
        "    else:\n"
        "        print(json.dumps({'ok': False, 'witnesses': []}))\n"
        "else:\n"
        "    print(json.dumps({'ok': False, 'witnesses': []}))\n"
    )


def solve_existential(sympy_eq: str, var_names: "list[str]", integer: bool = False,
                      timeout_s: int = 10) -> "list[str] | None":
    """Direct path: build → run → return the witness string(s), or None. No LLM. `sympy_eq` is `lhs == rhs`
    in SymPy syntax (caller-translated)."""
    script = build_existential_script(sympy_eq, var_names, integer=integer)
    if not script:
        return None
    res = run_solver_script(script, timeout_s=timeout_s)
    if res and res.get("ok") and res.get("witnesses"):
        return [str(w) for w in res["witnesses"]]
    return None


def build_linear_system_script(equations: "list[str]", var_names: "list[str]", integer: bool = False) -> str:
    """Build a SymPy script for a MULTI-binder existential over a CONJUNCTION of equations:
    `∃ <vars>, eq0 ∧ eq1 ∧ …` — each `eqi` is `lhs == rhs` ALREADY in SymPy surface syntax. Solves the system
    (sympy.linsolve for a linear system; falls back to nonlinear `solve`) and prints a JSON witness tuple. The
    Kronecker/Hankel use case (recover recurrence coefficients) IS exactly this: solving the linear Hankel
    system for the c's. Rejects PARAMETRIC (underdetermined) solutions — only a fully-concrete (symbol-free)
    assignment is injectable. '' if nothing to solve."""
    if not var_names or not equations or any("==" not in e for e in equations):
        return ""
    syms = ", ".join(var_names)
    sym_arg = " ".join(var_names)
    assum = "integer=True" if integer else "real=True"
    loc = "{" + ", ".join(f"'{v}': {v}" for v in var_names) + "}"
    pairs = [e.split("==", 1) for e in equations]
    pj = json.dumps([[l.strip(), r.strip()] for l, r in pairs])
    ints = "True" if integer else "False"   # embedded as a Python literal in the script (NOT str.format)
    return (
        "import sympy, json\n"
        f"{syms} = sympy.symbols('{sym_arg}', {assum})\n"
        f"_loc = {loc}\n"
        f"_vars = [{syms}]\n"
        f"_INT = {ints}\n"
        "sol=None\n"
        "def _intify(c):\n"
        # accept an exact integer OR a whole-number Float (decimal-coeff systems, e.g. 0.5*x==2 ⇒ x=4.0);
        # return the int-form sympy value, else None. NB: compare as FLOATS — `Float(4.0)==Integer(4)` is
        # False in sympy (exact-vs-inexact `==`), so a sympy-equality check would wrongly reject the witness.
        "    if getattr(c, 'is_integer', False):\n"
        "        return c\n"
        "    try:\n"
        "        if getattr(c, 'is_number', False):\n"
        "            f = float(c)\n"
        "            if f == round(f):\n"
        "                return sympy.Integer(int(round(f)))\n"
        "    except Exception:\n"
        "        return None\n"
        "    return None\n"
        "try:\n"   # sympify/solve INSIDE try → malformed input ⇒ clean ok:false, never a crash
        f"    eqs = [sympy.Eq(sympy.sympify(a, locals=_loc), sympy.sympify(b, locals=_loc)) for a, b in {pj}]\n"
        "    cands = []\n"
        "    try:\n"   # linsolve in its OWN try so a NonlinearError falls through to the general solver
        "        ls = sympy.linsolve(eqs, _vars)\n"
        "        cands = [tuple(t) for t in ls]\n"
        "    except Exception:\n"
        "        cands = []\n"
        "    if not cands or all(any(getattr(x,'free_symbols',set()) for x in c) for c in cands):\n"
        "        ds = sympy.solve(eqs, _vars, dict=True)\n"   # nonlinear / underdetermined fallback
        "        cands = [tuple(d.get(s) for s in _vars) for d in ds]\n"
        # pick the FIRST fully-concrete (and, under _INT, integer-valued) candidate
        "    for c in cands:\n"
        "        if not c or any(x is None or getattr(x,'free_symbols',set()) for x in c):\n"
        "            continue\n"
        "        if _INT:\n"
        "            ic = [_intify(x) for x in c]\n"
        "            if all(x is not None for x in ic):\n"
        "                sol = [str(x) for x in ic]; break\n"
        "        else:\n"
        "            sol = [str(x) for x in c]; break\n"
        "except Exception:\n"
        "    sol=None\n"
        "print(json.dumps({'ok': sol is not None, 'witnesses': sol or []}))\n"
    )


def solve_linear_system(equations: "list[str]", var_names: "list[str]", integer: bool = False,
                        timeout_s: int = 10) -> "list[str] | None":
    """Direct path for a system existential `∃ vars, ⋀ eqs`: build → run → witness tuple, or None. No LLM."""
    script = build_linear_system_script(equations, var_names, integer=integer)
    if not script:
        return None
    res = run_solver_script(script, timeout_s=timeout_s)
    if res and res.get("ok") and res.get("witnesses"):
        return [str(w) for w in res["witnesses"]]
    return None


def build_recurrence_script(seq: "list", max_order: "int | None" = None) -> str:
    """Build a SymPy script that recovers the MINIMAL linear recurrence of a numeric sequence prefix via the
    HANKEL criterion (Kronecker): for increasing order k, the k×k Hankel block must be non-singular and its
    solved coefficients must predict ALL remaining terms. Prints `{ok, order, coeffs}` (coeffs c₀…c_{k-1} with
    a_{n+k}=Σ cᵢ a_{n+i}) or ok:false. ZERO hallucination — pure exact linear algebra over ℚ. `seq` entries are
    int / rational-string literals."""
    if not seq or len(seq) < 3:
        return ""
    sj = json.dumps([str(s) for s in seq])
    mo = "None" if max_order is None else int(max_order)
    return (
        "import sympy, json\n"
        f"seq = [sympy.Rational(s) for s in {sj}]\n"
        "N = len(seq)\n"
        f"maxo = ({mo}) if ({mo}) is not None else (N - 1)//2\n"
        "res = {'ok': False}\n"
        "def _hdet(m):\n"                       # m×m Hankel determinant D_m (uses seq[0..2m-2])
        "    return sympy.Matrix(m, m, lambda i, j: seq[i + j]).det()\n"
        "try:\n"
        # KRONECKER: the sequence has a minimal linear recurrence of order k IFF the Hankel det D_k ≠ 0 and
        # D_{k+1} = 0 (the Hankel RANK stabilizes at k). Computing D_{k+1} needs seq[0..2k] ⇒ N ≥ 2k+1; this
        # 'rank-stabilized' test is what rejects a SPURIOUS fit (a high-order recurrence coincidentally fitting
        # too-few validation points — e.g. primes fit order 3 under naive fit-and-check-one-point).
        "    for k in range(1, int(maxo) + 1):\n"
        "        if N < 2*k + 1:\n"
        "            break\n"
        "        if _hdet(k) == 0:\n"           # rank-deficient at order k ⇒ not the minimal order; go higher
        "            continue\n"
        "        if _hdet(k + 1) != 0:\n"       # rank still growing ⇒ order > k (or no finite recurrence yet)
        "            continue\n"
        "        H = sympy.Matrix(k, k, lambda i, j: seq[i + j])\n"
        "        c = H.LUsolve(sympy.Matrix([seq[i + k] for i in range(k)]))\n"
        "        if all(seq[n + k] == sum(c[i]*seq[n + i] for i in range(k)) for n in range(N - k)):\n"
        "            res = {'ok': True, 'order': k, 'coeffs': [str(c[i]) for i in range(k)]}\n"
        "            break\n"
        "except Exception:\n"
        "    res = {'ok': False}\n"
        "print(json.dumps(res))\n"
    )


def find_linear_recurrence(seq: "list", max_order: "int | None" = None,
                           timeout_s: int = 10) -> "dict | None":
    """Recover the minimal linear recurrence of a numeric sequence (Kronecker/Hankel) — the EXOGENOUS-TRANSPORT
    primitive for the rational-generating-function / D-finite sub-case. Returns {order, coeffs} (c₀…c_{k-1},
    a_{n+k}=Σ cᵢ a_{n+i}) or None (no recurrence of order ≤ max_order fits, or too few terms). Pure SymPy, no
    LLM, no Lean — the caller transports the recovered coeffs into a Lean witness/SPECIALIZE rung; the kernel
    arbitrates.

    CAVEAT — certifies only fit-ON-THE-PREFIX: a too-short prefix can spuriously fit a low-order recurrence
    (the first 7 primes genuinely satisfy an order-3 one); more terms defeats it. The Hankel-rank stabilization
    (D_k≠0, D_{k+1}=0) needs N≥2k+1, so pass as many terms as available. NEVER a false closure: the kernel
    re-verifies the recurrence for ALL n, so a prefix-overfit recurrence fails honestly (wasted move, not a
    laundered proof)."""
    # Degenerate all-zero prefix: the minimal recurrence is order 1 (a_{n+1}=0·a_n), but the Hankel-det scan
    # skips it (D_k=0 ∀k ⇒ every k `continue`s), so guard it explicitly.
    try:
        if len(seq) >= 2 and all(float(str(s)) == 0.0 for s in seq):
            return {"order": 1, "coeffs": ["0"]}
    except (ValueError, TypeError):
        pass
    script = build_recurrence_script(seq, max_order=max_order)
    if not script:
        return None
    res = run_solver_script(script, timeout_s=timeout_s)
    if res and res.get("ok") and res.get("order"):
        return {"order": int(res["order"]), "coeffs": [str(c) for c in res.get("coeffs", [])]}
    return None


def build_diophantine_script(D: int, N: int, var_names: "list[str]") -> str:
    """Build a SymPy script for the PELL-form existential `∃ x y, x² − D·y² = N` via `diop_DN` (the
    continued-fraction Pell solver) — the witness is the FUNDAMENTAL (smallest positive, y≠0) solution, which
    for many D is ENORMOUS (D=61 ⇒ x=1766319049, y=226153980): trivial for SymPy, impossible for an LLM to
    guess, and the native cascade has no finder. Prints {ok, witnesses:[x,y]} (smallest positive nontrivial)
    or ok:false. var_names = the two ∃-binders in order."""
    if len(var_names) != 2:
        return ""
    return (
        "import sympy, json\n"
        "res = {'ok': False, 'witnesses': []}\n"
        "try:\n"
        "    from sympy.solvers.diophantine.diophantine import diop_DN\n"
        f"    sols = diop_DN({int(D)}, {int(N)})\n"
        # keep POSITIVE, nontrivial (y≠0); pick the smallest x (the fundamental)
        "    cand = sorted(((abs(int(x)), abs(int(y))) for (x, y) in sols if int(y) != 0))\n"
        "    if cand:\n"
        "        x, y = cand[0]\n"
        "        res = {'ok': True, 'witnesses': [str(x), str(y)]}\n"
        "except Exception:\n"
        "    res = {'ok': False, 'witnesses': []}\n"
        "print(json.dumps(res))\n"
    )


def solve_diophantine_pell(D: int, N: int, var_names: "list[str]", timeout_s: int = 10) -> "list[str] | None":
    """Pell-form `∃ x y, x²−D·y²=N`: return the FUNDAMENTAL (smallest positive nontrivial) witness [x, y], or
    None. The genuinely-LLM-impossible / SymPy-trivial niche (huge fundamental solutions). No LLM."""
    script = build_diophantine_script(D, N, var_names)
    if not script:
        return None
    res = run_solver_script(script, timeout_s=timeout_s)
    if res and res.get("ok") and res.get("witnesses"):
        return [str(w) for w in res["witnesses"]]
    return None


def _guard_clause(guards: "tuple[str, ...] | list[str]") -> str:
    """Shared point-admissibility test for the two grid scripts: a sample point COUNTS only when every
    guard (hypothesis relation) evaluates to a definite True there — definite-False ⇒ out of the
    hypotheses' domain (skip), symbolic residue ⇒ not evidence either way (skip). Returns script lines
    that set `_admit` for the current `_vals`."""
    if not guards:
        return "        _admit = True\n"
    return (
        "        _admit = True\n"
        "        for _g in _grds:\n"
        "            _gv = _g.subs(dict(zip(_syms, _vals)))\n"
        "            if not ((hasattr(_gv, 'is_Boolean') and _gv.is_Boolean) or _gv in (sympy.true, sympy.false)) or not bool(_gv):\n"
        "                _admit = False; break\n"
    )


def build_counterexample_script(sympy_relation: str, var_names: "list[str]", integer: bool = True,
                                bound: int = 24, nonneg: bool = False,
                                guards: "tuple[str, ...] | list[str]" = ()) -> str:
    """Build a SymPy script that GRID-SEARCHES a small box for a COUNTEREXAMPLE to a universally-quantified
    relation `sympy_relation` (a relation that SHOULD hold for ALL assignments — e.g. `Eq(n + 1, n)` or
    `n <= n*n`). `nonneg=True` (for ℕ/Nat) searches [0, bound] with nonnegative symbols so a counterexample
    invalid for the actual type is never reported (a false ∀ over ℤ but TRUE over ℕ must not misfire); else
    [−bound, bound]. `guards` (hypothesis relations, for `∀ …, H₁ → … → C` goals): a point is a
    counterexample only if every guard is definite-True there AND the conclusion is definite-False —
    sound for the implication (a guard-satisfying refutation of C refutes the whole statement). Prints
    the first FAILING assignment as a JSON witness, or ok=False. '' if not translatable. (Script-internal
    names are _-prefixed + `_syms` binds first — the goal-var-shadows-harness-name collision class.)"""
    if not var_names:
        return ""
    syms = ", ".join(var_names)
    sym_arg = " ".join(var_names)
    assum = ("integer=True, nonnegative=True" if nonneg else "integer=True") if integer else "real=True"
    lo = "0" if nonneg else f"-{int(bound)}"
    loc = "{" + ", ".join(f"'{v}': {v}" for v in var_names) + "}"
    return (
        "import sympy, json, itertools\n"
        f"{syms} = sympy.symbols('{sym_arg}', {assum})\n"
        f"_syms = [{syms}]\n"
        f"_loc = {loc}\n"
        "_hit = None\n"
        "try:\n"   # sympify INSIDE the try → a malformed relation yields a clean ok:false, not a crash
        f"    _rel = sympy.sympify({json.dumps(sympy_relation)}, locals=_loc)\n"
        f"    _grds = [sympy.sympify(_gs, locals=_loc) for _gs in {json.dumps(list(guards))}]\n"
        f"    for _vals in itertools.product(range({lo}, {int(bound)} + 1), repeat=len(_syms)):\n"
        + _guard_clause(guards) +
        "        if not _admit:\n"
        "            continue\n"
        "        _v = _rel.subs(dict(zip(_syms, _vals)))\n"
        "        if _v is sympy.false or (hasattr(_v, 'is_Boolean') and _v.is_Boolean and not bool(_v)):\n"
        "            _hit = [str(_x) for _x in _vals]; break\n"
        "except Exception:\n"
        "    _hit = None\n"
        "print(json.dumps({'ok': _hit is not None, 'witnesses': _hit or []}))\n"
    )


def find_counterexample(sympy_relation: str, var_names: "list[str]", integer: bool = True,
                        bound: int = 24, timeout_s: int = 8, nonneg: bool = False,
                        guards: "tuple[str, ...] | list[str]" = ()) -> "list[str] | None":
    """Bounded grid-search for a COUNTEREXAMPLE to a ∀-relation; returns the failing assignment or None. The
    falsity signal: a non-None result means the goal is (computably) FALSE in the box → route to falsify.
    `nonneg=True` (ℕ/Nat) restricts the search to non-negative integers so a counterexample invalid for the
    type is never reported. `guards` = hypothesis relations for guarded (`H → C`) goals."""
    script = build_counterexample_script(sympy_relation, var_names, integer=integer, bound=bound,
                                         nonneg=nonneg, guards=guards)
    if not script:
        return None
    res = run_solver_script(script, timeout_s=timeout_s)
    if res and res.get("ok") and res.get("witnesses"):
        return [str(w) for w in res["witnesses"]]
    return None


def build_instance_check_script(sympy_relation: str, var_names: "list[str]", integer: bool = True,
                                bound: int = 24, nonneg: bool = False, k: int = 5,
                                guards: "tuple[str, ...] | list[str]" = ()) -> str:
    """Build a SymPy script that CONFIRMS a ∀-relation at concrete sample points — the POSITIVE DUAL of
    `build_counterexample_script` (#124 instances-first; same relation/var contract, same box semantics:
    `nonneg=True` ⇒ [0, bound], else [−bound, bound]). Samples a deterministic SPREAD (small + spaced
    values, not just consecutive ints), collects up to `k` assignments where the relation evaluates to a
    DEFINITE True, and stops early on a definite False (which is reported as the refuting assignment —
    one script answers both 'looks true at samples' and 'is false here'). Prints
    `{"ok": true, "confirmed": [[..],..], "refuted": [..]|null, "evaluated": n}`. '' if not translatable.
    A relation that never evaluates to a definite Boolean (symbolic residue) yields confirmed=[] — an
    honest NO-SIGNAL, never fake confidence."""
    if not var_names:
        return ""
    syms = ", ".join(var_names)
    sym_arg = " ".join(var_names)
    assum = ("integer=True, nonnegative=True" if nonneg else "integer=True") if integer else "real=True"
    # #130 (mathematician leg): probe the degenerate points (0, ±1) FIRST, then the BOX EXTREMES, then the
    # rest of the spread — so a SINGLE-VARIABLE ∀-claim that holds on small values but breaks at the
    # boundary is caught WITHIN the first few evals (BEFORE the k-confirmation early-stop, which otherwise
    # never reaches a tail-appended extreme — caught live). For MULTI-variable claims this is best-effort:
    # `itertools.product` advances the LAST var fastest, so the first var may not reach its extreme before
    # the early-stop; the gate is advisory (a missed counterexample just funds a real proof attempt that
    # then cannot close a false statement — never a false closure). STRUCTURE-FREE (no parsing the relation
    # for poles/roots — that would be iatrogenic); the kernel stays the only arbiter.
    if nonneg:
        _deg, _rest, _ext = [0, 1], [2, 3, 5, 8, 13, 21], [int(bound), int(bound) - 1]
    else:
        _deg, _rest = [0, 1, -1], [2, -2, 3, 5, -5, 8, 13, -13, 21]
        _ext = [int(bound), int(bound) - 1, -int(bound), -(int(bound) - 1)]
    pts = [v for v in dict.fromkeys(_deg + _ext + _rest) if abs(v) <= int(bound)]   # dedupe, order-preserving, in-box
    loc = "{" + ", ".join(f"'{v}': {v}" for v in var_names) + "}"
    # All script-internal names are _-prefixed AND `_syms` binds BEFORE any other assignment — a goal
    # variable named `n`/`v`/`vals` must never collide with the harness names (the n-shadowed-the-symbol
    # bug this selftest caught: the counter clobbered the symbol ⇒ subs was a no-op ⇒ zero evidence).
    return (
        "import sympy, json, itertools\n"
        f"{syms} = sympy.symbols('{sym_arg}', {assum})\n"
        f"_syms = [{syms}]\n"
        f"_loc = {loc}\n"
        "_confirmed, _refuted, _ne = [], None, 0\n"
        "try:\n"   # sympify INSIDE the try → a malformed relation yields a clean no-signal, not a crash
        f"    _rel = sympy.sympify({json.dumps(sympy_relation)}, locals=_loc)\n"
        f"    _grds = [sympy.sympify(_gs, locals=_loc) for _gs in {json.dumps(list(guards))}]\n"
        f"    for _vals in itertools.product({pts!r}, repeat=len(_syms)):\n"
        + _guard_clause(guards) +
        "        if not _admit:\n"
        "            continue\n"   # outside the hypotheses' domain — not evidence either way
        "        _v = _rel.subs(dict(zip(_syms, _vals)))\n"
        "        if not (hasattr(_v, 'is_Boolean') and _v.is_Boolean) and _v not in (sympy.true, sympy.false):\n"
        "            continue\n"   # symbolic residue at this point — skip, never count as evidence
        "        _ne += 1\n"
        "        if bool(_v):\n"
        "            _confirmed.append([str(_x) for _x in _vals])\n"
        f"            if len(_confirmed) >= {int(k)}:\n"
        "                break\n"
        "        else:\n"
        "            _refuted = [str(_x) for _x in _vals]; break\n"
        "except Exception:\n"
        "    _confirmed, _refuted, _ne = [], None, 0\n"
        "print(json.dumps({'ok': True, 'confirmed': _confirmed, 'refuted': _refuted, 'evaluated': _ne}))\n"
    )


def confirm_instances(sympy_relation: str, var_names: "list[str]", integer: bool = True,
                      bound: int = 24, timeout_s: int = 8, nonneg: bool = False,
                      k: int = 5, guards: "tuple[str, ...] | list[str]" = ()) -> "dict | None":
    """Instances-first evidence (#124): evaluate a ∀-relation at a deterministic spread of concrete
    points. Returns `{"confirmed": [[..],..], "refuted": [..]|None, "evaluated": n}` or None
    (untranslatable / sandbox failure / no definite evaluation — NO-SIGNAL, never fake confidence).
    `find_counterexample`'s positive dual: confirmation is cheap CONFIDENCE + recorded evidence (the
    conjecture-book feed), a refutation is the same falsity signal `looks_false` routes on. ADVISORY
    by contract — the kernel stays the only arbiter. `guards` (for `∀ …, H₁ → … → C`): only points
    where every hypothesis is definite-True count — a guard-satisfying refutation of C refutes the
    implication; guards never satisfied in the box ⇒ evaluated=0 ⇒ no-signal."""
    script = build_instance_check_script(sympy_relation, var_names, integer=integer, bound=bound,
                                         nonneg=nonneg, k=k, guards=guards)
    if not script:
        return None
    res = run_solver_script(script, timeout_s=timeout_s)
    if not res or not res.get("ok") or not int(res.get("evaluated") or 0):
        return None
    return {"confirmed": [list(map(str, c)) for c in (res.get("confirmed") or [])],
            "refuted": ([str(x) for x in res["refuted"]] if res.get("refuted") else None),
            "evaluated": int(res.get("evaluated") or 0)}


def invariant_mismatch(sympy_relation: str, var_names: "list[str]") -> "list[str] | None":
    """INVARIANT-SCREEN (#114, the conservation-law instinct from the deanchored-isomorphism traversal):
    compare CHEAP STRUCTURAL INVARIANTS of an equality's two sides — polynomial degree per variable, parity on
    an integer sample, leading growth. A mismatch is a strong it's-FALSE signal at ~ms cost (vs the ~8s grid
    search) — physicists' first check: conserved quantities must balance. `find_counterexample`'s SIBLING and
    cheap FIRST STAGE (same input contract: the `lhs == rhs` relation + var names). ADVISORY: a non-None only
    ROUTES toward falsify; the kernel-proved ¬G stays the only refutation verdict. Equality-only (an inequality
    has no two-sided conservation); returns None on parse failure / non-equality / no-carrier — never blocks."""
    try:
        import sympy as sp
        rel = (sympy_relation or "").strip()
        if "==" in rel:                       # `lhs == rhs` surface form
            l_s, r_s = rel.split("==", 1)
            lhs, rhs = sp.sympify(l_s), sp.sympify(r_s)
        else:                                  # `Eq(lhs, rhs)` functional form (what _lean_relation_to_sympy emits)
            e = sp.sympify(rel)
            if not isinstance(e, sp.Eq):
                return None                    # equality-only (an inequality has no two-sided conservation)
            lhs, rhs = e.lhs, e.rhs
        symbols = [sp.Symbol(v) for v in var_names] or sorted(lhs.free_symbols | rhs.free_symbols, key=str)
        out: "list[str]" = []
        # 1. polynomial degree per variable (identities conserve degree)
        try:
            if all(e.is_polynomial(*symbols) for e in (lhs, rhs)):
                for s in symbols:
                    dl, dr = sp.degree(sp.Poly(lhs, s)), sp.degree(sp.Poly(rhs, s))
                    if dl != dr:
                        out.append(f"degree({s}): lhs={dl} rhs={dr}")
        except Exception:  # noqa: BLE001 — per-leg fail-quiet (skip, never a false mismatch)
            pass
        # 2. parity on integer samples (mod-2 conservation): one break is decisive
        try:
            for base in (-2, 0, 1, 3, 5):
                subs = {s: base + i for i, s in enumerate(symbols)}
                vl, vr = lhs.subs(subs), rhs.subs(subs)
                if getattr(vl, "is_Integer", False) and getattr(vr, "is_Integer", False) \
                        and (int(vl) - int(vr)) % 2 != 0:
                    out.append(f"parity@{subs}: {vl} vs {vr} differ mod 2")
                    break
        except Exception:  # noqa: BLE001
            pass
        # 3. leading growth (identities conserve asymptotics in the first variable)
        try:
            if symbols and sp.limit(lhs / (sp.Abs(rhs) + 1), symbols[0], sp.oo) in (sp.oo, -sp.oo):
                out.append(f"growth: lhs dominates rhs as {symbols[0]}→oo")
        except Exception:  # noqa: BLE001
            pass
        return out or None
    except Exception:  # noqa: BLE001 — no carrier / unparseable ⇒ no signal
        return None


def _selftest() -> int:
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    ok("safe: pure sympy passes", script_is_safe("import sympy, json\nprint('{}')"))
    ok("safe: os rejected", not script_is_safe("import os\nimport sympy"))
    ok("safe: comma-import os rejected", not script_is_safe("import sympy, os\n"))
    ok("safe: subprocess token rejected", not script_is_safe("import sympy\nsubprocess.run(['x'])"))
    ok("safe: empty rejected", not script_is_safe(""))
    ok("run: unsafe blocked", run_solver_script("import os\nprint('{}')") is None)
    ok("run: parses last JSON amid noise",
       (run_solver_script("import json\nprint('warn')\nprint(json.dumps({'ok':True,'witnesses':['1']}))") or {}).get("ok") is True)
    # the real compute: non-linear integer existential x^2 + x = 42 ⇒ x ∈ {6, -7}
    w = solve_existential("x**2 + x == 42", ["x"], integer=True)
    ok("solve: integer non-linear existential finds a witness", w is not None and ({"6", "-7"} & set(w)))
    # real/rational: 2*x == 3 ⇒ 3/2
    wr = solve_existential("2*x == 3", ["x"], integer=False)
    ok("solve: rational existential", wr is not None and any("3/2" in s for s in wr))
    # underdetermined (one eq, two vars) ⇒ a PARAMETRIC solution ⇒ rejected (no concrete witness to inject).
    ok("solve: underdetermined/parametric → None", solve_existential("x + 2*y == 0", ["x", "y"], integer=True) is None)
    ok("solve: unsatisfiable-shape returns None gracefully",
       solve_existential("x**2 == -1", ["x"], integer=True) is None)
    # counterexample search — the falsity signal
    ok("counterexample: false ∀ (n+1=n) found", find_counterexample("Eq(n + 1, n)", ["n"], integer=True) is not None)
    ok("counterexample: true ∀ (n+0=n) → None", find_counterexample("Eq(n + 0, n)", ["n"], integer=True) is None)
    ok("counterexample: false ∀ (n*n=n) found (n=2)", find_counterexample("Eq(n*n, n)", ["n"], integer=True) is not None)
    ok("counterexample: true ∀ (n<=n*n) → None", find_counterexample("n <= n*n", ["n"], integer=True) is None)

    # linear-system existential (the Kronecker Hankel-system shape + general linear Diophantine systems)
    ls = solve_linear_system(["x + y == 5", "x - y == 1"], ["x", "y"], integer=True)
    ok("system: 2x2 determined integer system", ls is not None and ls == ["3", "2"])
    ok("system: inconsistent → None", solve_linear_system(["x == 1", "x == 2"], ["x"], integer=True) is None)
    ok("system: underdetermined/parametric → None",
       solve_linear_system(["x + y == 1"], ["x", "y"], integer=True) is None)
    # a=b, c=b+1 ⇒ sum=3b+1; ==7 ⇒ b=2 ⇒ (a,b,c)=(2,2,3) (the integer solution; ==6 would be non-integer)
    ls3 = solve_linear_system(["a + b + c == 7", "a - b == 0", "c - b == 1"], ["a", "b", "c"], integer=True)
    ok("system: 3x3 determined", ls3 is not None and ls3[0] == "2" and ls3[1] == "2" and ls3[2] == "3")
    # bug-fix 2026-06-07: NONLINEAR fallback (linsolve raises → solve) now reached; x*y=6 ∧ x+y=5 ⇒ {2,3}
    nl = solve_linear_system(["x*y == 6", "x + y == 5"], ["x", "y"], integer=True)
    ok("system: nonlinear fallback reached (xy=6,x+y=5 → integer sol)", nl is not None and set(nl) == {"2", "3"})
    # bug-fix: a whole-number Float witness under integer=True (decimal-coeff eq) accepted as its int form
    ok("system: integral Float under integer=True (0.5x=2 → 4)",
       solve_linear_system(["0.5*x == 2"], ["x"], integer=True) == ["4"])

    # linear-recurrence recovery (Kronecker / Hankel rank) — the EXOGENOUS-TRANSPORT primitive
    fib = find_linear_recurrence([0, 1, 1, 2, 3, 5, 8, 13])
    ok("recurrence: Fibonacci → order 2, coeffs [1,1]", fib is not None and fib["order"] == 2 and fib["coeffs"] == ["1", "1"])
    geo = find_linear_recurrence([1, 2, 4, 8, 16, 32])
    ok("recurrence: geometric 2^n → order 1, coeff [2]", geo is not None and geo["order"] == 1 and geo["coeffs"] == ["2"])
    sq = find_linear_recurrence([0, 1, 4, 9, 16, 25, 36])
    ok("recurrence: n^2 → order 3, coeffs [1,-3,3]", sq is not None and sq["order"] == 3 and sq["coeffs"] == ["1", "-3", "3"])
    # PREFIX-OVERFIT GUARD: a too-short prefix can spuriously fit (the FIRST 7 primes genuinely satisfy an
    # order-3 recurrence — D₄=0 by coincidence); enough terms defeats it. This is why the caller/kernel must
    # verify the transported recurrence holds GLOBALLY (the primitive certifies only fit-on-the-prefix).
    ok("recurrence: 7-prime prefix DOES fit order 3 (honest prefix-overfit)",
       (find_linear_recurrence([2, 3, 5, 7, 11, 13, 17]) or {}).get("order") == 3)
    ok("recurrence: 11 primes (no low-order fit) → None", find_linear_recurrence([2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31]) is None)
    ok("recurrence: Catalan (non-constant-coeff) → None", find_linear_recurrence([1, 1, 2, 5, 14, 42, 132, 429]) is None)
    ok("recurrence: too-few-terms → None", find_linear_recurrence([1, 2]) is None)
    # bug-fix: degenerate all-zero prefix ⇒ order-1 a_{n+1}=0 (the Hankel-det scan skips it; guarded)
    ok("recurrence: all-zeros → order 1 coeff [0]", find_linear_recurrence([0, 0, 0, 0, 0]) == {"order": 1, "coeffs": ["0"]})

    # Pell-form diophantine (the genuinely-LLM-impossible / SymPy-trivial niche)
    ok("pell: D=2,N=1 → fundamental (3,2)", solve_diophantine_pell(2, 1, ["x", "y"]) == ["3", "2"])
    ok("pell: D=13,N=1 → (649,180)", solve_diophantine_pell(13, 1, ["x", "y"]) == ["649", "180"])
    ok("pell: D=61,N=1 → the HUGE fundamental (1766319049, 226153980)",
       solve_diophantine_pell(61, 1, ["x", "y"]) == ["1766319049", "226153980"])
    ok("pell: D=3,N=2 (impossible mod 3) → None", solve_diophantine_pell(3, 2, ["x", "y"]) is None)

        # invariant_mismatch (#114): the conservation-law screen — find_counterexample's cheap stage 1
    ok("invariant: true identity ⇒ None", invariant_mismatch("(n+1)**2 == n**2 + 2*n + 1", ["n"]) is None)
    _im = invariant_mismatch("n**3 == n**2 + 5", ["n"])
    ok("invariant: degree mismatch caught", _im is not None and any("degree" in m for m in _im))
    _im = invariant_mismatch("2*n == 2*n + 1", ["n"])
    ok("invariant: parity break at equal degree caught", _im is not None and any("parity" in m for m in _im))
    ok("invariant: inequality ⇒ None (equality-only)", invariant_mismatch("n <= n + 1", ["n"]) is None)
    ok("invariant: garbage ⇒ None (advisory)", invariant_mismatch("?? == ]]", ["n"]) is None)

    # confirm_instances (#124 instances-first): the POSITIVE dual of find_counterexample
    _ci = confirm_instances("Eq((n+1)**2, n**2 + 2*n + 1)", ["n"], integer=True)
    ok("confirm: true identity ⇒ k confirmed, no refutation",
       _ci is not None and len(_ci["confirmed"]) == 5 and _ci["refuted"] is None)
    _ci = confirm_instances("n <= n*n", ["n"], integer=True, nonneg=True)
    ok("confirm: true-over-ℕ inequality confirmed (nonneg samples)",
       _ci is not None and len(_ci["confirmed"]) >= 3 and _ci["refuted"] is None)
    _ci = confirm_instances("Eq(n + 1, n)", ["n"], integer=True)
    ok("confirm: false relation ⇒ refuting assignment, zero fake confidence",
       _ci is not None and _ci["refuted"] is not None and len(_ci["confirmed"]) == 0)
    _ci = confirm_instances("n*n >= n", ["n"], integer=True)   # false over ℝ-mindset? true over ℤ: n²≥n ∀n∈ℤ
    ok("confirm: true-over-ℤ inequality confirmed on the signed spread",
       _ci is not None and len(_ci["confirmed"]) >= 3 and _ci["refuted"] is None)
    ok("confirm: garbage ⇒ None (no-signal, never fake confidence)",
       confirm_instances("?? == ]]", ["n"]) is None)
    ok("confirm: no vars ⇒ None", confirm_instances("Eq(1, 1)", []) is None)

    # GUARDED (H → C) legs: only hypothesis-satisfying points count, both duals
    _ci = confirm_instances("2*n <= n*n", ["n"], integer=True, nonneg=True, guards=["n >= 2"])
    ok("guard confirm: 2≤n → 2n≤n² holds on the admitted points (n≥2)",
       _ci is not None and len(_ci["confirmed"]) >= 3 and _ci["refuted"] is None)
    _ci = confirm_instances("n*n <= 2*n", ["n"], integer=True, nonneg=True, guards=["n >= 2"])
    ok("guard confirm: 2≤n → n²≤2n refuted at an ADMITTED point (n≥3), n=0,1 never misfire",
       _ci is not None and _ci["refuted"] is not None and int(_ci["refuted"][0]) >= 3)
    _ci = confirm_instances("Eq(n, n)", ["n"], integer=True, nonneg=True, guards=["n >= 1000"])
    ok("guard confirm: guards never satisfied in the box ⇒ no-signal (never fake confidence)",
       _ci is None)
    _cx = find_counterexample("n*n <= 2*n", ["n"], integer=True, nonneg=True, guards=["n >= 2"])
    ok("guard counterexample: guard-satisfying refutation found (n≥3)",
       _cx is not None and int(_cx[0]) >= 3)
    _cx = find_counterexample("2*n <= n*n", ["n"], integer=True, nonneg=True, guards=["n >= 2"])
    ok("guard counterexample: true-under-guard ⇒ None (n=1 not misreported)", _cx is None)
    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
