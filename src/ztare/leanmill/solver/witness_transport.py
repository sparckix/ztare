"""Cross-substrate WITNESS TRANSPORT — Lean glue over the general SymPy capability (MOVE_WITNESS_TRANSPORT,
2026-06-07).

The exogenous move: for a COMPUTABLE leaf (a non-linear existential / Diophantine / algebraic witness goal) that
the native cascade cannot CLOSE, transport a witness from the COMPUTATIONAL substrate (Python/SymPy) into
Lean. The sound decomposition:

    witness-FINDING (SymPy — complete on its fragment)  ⟂  PROVING (the Lean kernel — the arbiter)

SymPy (directly, or via an LLM-written script) FINDS the satisfying witness; we INJECT it as a Lean tactic
(`refine ⟨<witness : T>, ?_⟩ <;> norm_num`); the kernel RE-VERIFIES. A wrong/hallucinated witness merely
fails to compile (a MISS) — ZERO hallucination risk, never a false closure. The niche is exactly the gap left
by Lean's native bridges (`omega`=linear-ℤ, `polyrith`=CAS linear-combination, `decide`=finite,
`nlinarith`=inequalities): NON-LINEAR EXISTENTIALS, where Lean has no native FINDER.

SEPARATION OF CONCERNS (per the operator): the general, substrate-agnostic SymPy compute (safety guard,
bounded isolated runner, the solve-script builder) lives in `ztare.common.symbolic_witness` and is IMPORTED
here; this module owns only the LEAN-specific glue — the ∃-gate on Lean syntax, the Lean→SymPy translation,
the type-aware tactic injection, and (in solver_core) the kernel-verified move runner. SMT/Z3 is a future
extension of the COMMON module (absent today). See `reference_sympy_capability_no_smt`.
"""
from __future__ import annotations

import os
import re

from ztare.common.symbolic_witness import (run_solver_script, solve_existential,  # the general SymPy capability
                                           solve_linear_system, find_linear_recurrence,
                                           solve_diophantine_pell)

# ── 1. Trigger gate (regex, no LLM) ───────────────────────────────────────────────────────────────
_ARITH = re.compile(r"\^|\*\*|(?<![:=<>!])=(?!=)|[+\-*]")   # arithmetic / equality markers
_EXISTS = re.compile(r"^\s*(?:∃|\\?exists\b|Exists)\s*(?P<vars>[^,:]+?)\s*(?::\s*(?P<typ>[^,]+?))?\s*,\s*(?P<body>.+)$",
                     re.DOTALL)
_INT_TYPES = {"ℕ", "Nat", "ℤ", "Int"}
_NAT_TYPES = {"ℕ", "Nat"}   # nonnegative — the counterexample grid must not search negatives
_FIELD_TYPES = {"ℝ", "Real", "ℚ", "Rat", "ℂ", "Complex"}


def _closed_prop(goal_text: str) -> str:
    """The goal's closed Prop (reuse conjecture._closed_goal_prop so the binder parse is consistent).
    BARE-PROP fallback (#124): solve-time callers (the instances-first gate) hand the LEAF goal, which
    `_leaf_goal_from_source` has already closed to a bare `∀ …` Prop — not a declaration, so the decl
    parser yields ''. A non-declaration text IS its own prop."""
    try:
        from ztare.leanmill.solver.conjecture import _closed_goal_prop
        p = _closed_goal_prop(goal_text) or ""
    except Exception:  # noqa: BLE001
        p = ""
    if p:
        return p
    t = (goal_text or "").strip()
    if t and not re.match(r"^\s*(?:@\[[^\]]*\]\s*)?(?:private\s+|protected\s+|noncomputable\s+)*(?:theorem|lemma|def|example|instance)\b", t):
        return t
    return ""


def is_computable_existential(goal_text: str) -> "dict | None":
    """REGEX gate (no LLM): an existential over an ARITHMETIC body — the witness-transport niche. Returns
    {vars, typ, body, prop} or None. Permissive (a false positive wastes one bounded SymPy call + a compile;
    the kernel is the arbiter). EXCLUDES abstract existentials (no `+,*,^,=` — e.g. `∃ f, Continuous f`),
    which belong to the abstract path, not SymPy."""
    prop = _closed_prop(goal_text)
    tail = prop
    m_all = re.match(r"^\s*(?:∀|\\?forall)\s*[^,]+,\s*(.+)$", tail, re.DOTALL)
    if m_all:
        tail = m_all.group(1)
    m = _EXISTS.match(tail.strip())
    if not m:
        return None
    body = (m.group("body") or "").strip()
    if not _ARITH.search(body):
        return None
    vars_ = [v for v in re.split(r"\s+", (m.group("vars") or "").strip()) if v]
    if not vars_:
        return None
    return {"vars": vars_, "typ": (m.group("typ") or "").strip(), "body": body, "prop": prop}


# ── 2. Lean → SymPy translation ───────────────────────────────────────────────────────────────────
def lean_body_to_sympy(body: str) -> str:
    """Translate a Lean equality body to a SymPy `lhs == rhs` string (conservative): `^`→`**`, drop
    `(.. : T)` ascriptions, single top-level `=`→`==`. Returns '' if it is not a single equality (richer
    goals fall through to the LLM-script path, which does its own extraction)."""
    if "=" not in body or any(op in body for op in ("<", ">", "∧", "∨", "¬", "↔", "→")):
        return ""
    lhs, rhs = body.split("=", 1)

    def _tr(e: str) -> str:
        e = e.replace("^", "**")
        e = re.sub(r"\(\s*([^():]+?)\s*:\s*[^()]+\)", r"(\1)", e)   # strip `(.. : T)`
        return e.strip()
    return f"{_tr(lhs)} == {_tr(rhs)}"


# ── 3. Transport injector (type-aware Lean tactic) ────────────────────────────────────────────────
_NATIVE_CLOSERS = ("norm_num", "ring", "decide", "omega", "simp_all")


def _cast(witness: str, typ: str) -> str:
    """Render a witness for a Lean binder of type `typ`. Field types get an explicit ascription so `42`
    elaborates as `(42 : ℝ)` (the type-coercion trap); integers/Nats stay bare; already-ascribed pass through."""
    w = str(witness).strip()
    if not typ or ":" in w or w.startswith("("):
        return w
    return f"({w} : {typ})" if typ in _FIELD_TYPES else w


def inject_witness_tactic(info: dict, witnesses: list, closer: "str | None" = None) -> str:
    """`by refine ⟨<w0:T>, …, ?_⟩ <;> (<closer>)` — plug in the witness(es), let a native closer finish the
    now-concrete goal. Multiple ∃-binders ⇒ an anonymous-constructor tuple; default closer = a first-of
    cascade over the native arithmetic tactics."""
    typ = info.get("typ", "")
    cast = [_cast(w, typ) for w in witnesses]
    if not cast:
        return ""
    fin = closer if (closer and closer in _NATIVE_CLOSERS) else ("first | " + " | ".join(_NATIVE_CLOSERS))
    return f"by refine ⟨{', '.join(cast)}, ?_⟩ <;> ({fin})"


# ── 4. The move: gate → SymPy (direct, then LLM-script) → inject ──────────────────────────────────
SCRIPT_PROMPT = (
    "You are a Python tool-writer. Below is a Lean 4 EXISTENTIAL goal. Do NOT prove it. WRITE A PYTHON SCRIPT "
    "using ONLY sympy (and json/math) that EXTRACTS the algebraic constraints and FINDS a satisfying witness "
    "for the existential variables, then prints EXACTLY ONE JSON object to stdout:\n"
    '  {{"ok": true, "witnesses": ["<v0>", "<v1>", ...]}}\n'
    "Solve in the goal’s domain (integers for ℕ/ℤ; reals/rationals for ℝ/ℚ). Output integer/rational "
    'LITERALS (no floats — use 6 or 3/2). If no witness, print {{"ok": false, "witnesses": []}}. Output ONLY '
    "the script in one ```python block — no prose, no file/network/os access.\nGOAL:\n{goal}\n"
)


def _solve_via_llm(info: dict, goal_text: str, dispatch, lean_root, timeout_s: int) -> "list[str] | None":
    prompt = SCRIPT_PROMPT.format(goal=goal_text)
    try:
        raw = dispatch(prompt, repo=lean_root, timeout=timeout_s) or ""
    except Exception:  # noqa: BLE001
        return None
    m = re.search(r"```(?:python)?\s*\n(.*?)```", raw, re.DOTALL)
    res = run_solver_script((m.group(1).strip() if m else raw.strip()), timeout_s=timeout_s)
    if res and res.get("ok") and res.get("witnesses"):
        return [str(w) for w in res["witnesses"]]
    return None


_FORALL = re.compile(r"^\s*(?:∀|\\?forall)\s*(?P<vars>[^,:]+?)\s*(?::\s*(?P<typ>[^,]+?))?\s*,\s*(?P<body>.+)$",
                     re.DOTALL)


_FORALL_GROUPS = re.compile(r"^\s*(?:∀|\\?forall)\s*(?P<groups>(?:\([^()]*\)\s*)+),\s*(?P<body>.+)$",
                            re.DOTALL)
_BINDER_GROUP = re.compile(r"\(\s*([^:()]+?)\s*:\s*([^()]+?)\s*\)")
_REL_MARK = re.compile(r"≤|≥|<|>|≠|(?<![:=<>!])=(?!=)")   # a relation in a binder TYPE ⇒ a Prop (hypothesis) binder
_IDENT = re.compile(r"[A-Za-z_][\w']*\Z")


def _forall_parts(prop: str) -> "tuple[list[str], str, str, list[str]] | None":
    """Shared ∀-parse for `looks_false` / `instance_evidence` (one home — they must agree). Handles the
    unparenthesized `∀ n : ℕ, …`, the parenthesized `∀ (n : ℕ), …` that `_closed_goal_prop` emits, a
    MULTI-GROUP telescope `∀ (a : ℤ) (b : ℤ), …` (all TYPE groups must share one type — mixed types
    degrade to a clean None), and HYPOTHESIS BINDERS `∀ (n : ℕ) (h : 2 ≤ n), …` whose Prop type (it
    contains a relation marker) becomes a GUARD, not a variable. Var names are validated as identifiers
    — never garbage-to-SymPy. Returns (vars, typ, body, guard_props) or None."""
    prop = (prop or "").strip()
    m = _FORALL_GROUPS.match(prop)
    if m:
        vars_: "list[str]" = []
        typs: "set[str]" = set()
        guard_props: "list[str]" = []
        for names_raw, typ_raw in _BINDER_GROUP.findall(m.group("groups")):
            typ_raw = typ_raw.strip()
            names = [v for v in re.split(r"\s+", names_raw.strip()) if v]
            if not names or any(not _IDENT.fullmatch(v) for v in names):
                return None
            if _REL_MARK.search(typ_raw):          # Prop binder: (h : 2 ≤ n) — the binder NAME is dropped
                guard_props.append(typ_raw)
            else:
                typs.add(typ_raw)
                vars_.extend(names)
        if not vars_ or len(typs) != 1:
            return None                             # no numeric vars / mixed-type telescope: conservative
        return vars_, typs.pop(), (m.group("body") or "").strip(), guard_props
    m = _FORALL.match(prop)
    if not m:
        return None
    vars_raw = (m.group("vars") or "").strip()
    typ = (m.group("typ") or "").strip()
    vars_ = [v for v in re.split(r"\s+", vars_raw) if v]
    if not vars_ or any(not _IDENT.fullmatch(v) for v in vars_):
        return None
    return vars_, typ, (m.group("body") or "").strip(), []


def _split_implication_chain(body: str) -> "list[str]":
    """Split a Lean Prop body on TOP-LEVEL `→`/`->` (paren/bracket-depth aware): the parts before the
    last arrow are hypotheses (guards), the last is the conclusion. A single-part list = unguarded."""
    parts, depth, cur, i = [], 0, [], 0
    while i < len(body):
        ch = body[i]
        if ch in "([{⟨⦃":
            depth += 1
        elif ch in ")]}⟩⦄":
            depth -= 1
        if depth == 0 and ch == "→":
            parts.append("".join(cur)); cur = []; i += 1; continue
        if depth == 0 and body.startswith("->", i):
            parts.append("".join(cur)); cur = []; i += 2; continue
        cur.append(ch); i += 1
    parts.append("".join(cur))
    return [p.strip() for p in parts if p.strip()]


def _guarded_relation(parts: "tuple[list[str], str, str, list[str]]") -> "tuple[str, list[str]] | None":
    """(vars, typ, body, props) → (conclusion_rel, guard_rels) in SymPy form, or None. EVERY hypothesis
    (binder Prop + each top-level →-antecedent) must translate cleanly — an untranslatable guard means
    point-admissibility cannot be certified, so NO signal at all (conservative, both duals)."""
    _, _, body, props = parts
    chain = _split_implication_chain(body)
    rel = _lean_relation_to_sympy(chain[-1])
    if not rel:
        return None
    guards: "list[str]" = []
    for h in props + chain[:-1]:
        g = _lean_relation_to_sympy(h)
        if not g:
            return None
        guards.append(g)
    return rel, guards


def _lean_relation_to_sympy(body: str) -> str:
    """Translate a Lean arithmetic relation to a SymPy relation string (`lhs = rhs` → `Eq(lhs, rhs)`;
    ≤/≥/< /> kept). '' if the body has hypotheses/connectives (→/∧/∨/¬) — conservative: only a BARE relation
    is a clean falsity signal."""
    b = body.strip()
    if any(op in b for op in ("→", "->", "∧", "∨", "¬", "↔", "∃", "∀")):
        return ""
    b = b.replace("^", "**")
    b = re.sub(r"\(\s*([^():]+?)\s*:\s*[^()]+\)", r"(\1)", b)               # strip ascriptions
    b = b.replace("≤", "<=").replace("≥", ">=").replace("≠", "!=")
    if any(op in b for op in ("<=", ">=", "!=", "<", ">")):
        return b
    if re.search(r"(?<![<>=!])=(?!=)", b):                                  # a single top-level equality
        lhs, rhs = re.split(r"(?<![<>=!])=(?!=)", b, maxsplit=1)
        return f"Eq({lhs.strip()}, {rhs.strip()})"
    return ""


def looks_false(goal_text: str, timeout_s: int = 8) -> "list[str] | None":
    """The falsity SIGNAL for the move router: parse a BARE ∀ arithmetic goal, translate the body to a SymPy
    relation, grid-search for a COUNTEREXAMPLE. Returns the failing assignment (⇒ the goal is computably FALSE
    in the search box → route to falsify) or None (no counterexample / not a computable ∀). Conservative — a
    non-None result is a HIGH-confidence falsity signal; the kernel still arbitrates the actual ¬G."""
    parts = _forall_parts(_closed_prop(goal_text))
    if not parts:
        return None
    vars_, _typ, _body, _props = parts
    gr = _guarded_relation(parts)
    if not gr:
        return None
    rel, guards = gr
    from ztare.common.symbolic_witness import find_counterexample, invariant_mismatch
    # STAGE 1 (#114 invariant-screen, ~ms): a degree/parity/growth mismatch of the two sides is a decisive
    # falsity signal BEFORE the ~8s grid search — the conservation-law check. Same advisory contract: a
    # non-None only routes toward falsify; the kernel-proved ¬G stays the only refutation verdict.
    # UNGUARDED ONLY: under hypotheses the domain is restricted, so a global degree/growth mismatch is
    # NOT decisive (e.g. h : n ≤ 5 caps the growth) — guarded goals go straight to the admitted-point grid.
    if not guards:
        mm = invariant_mismatch(rel, vars_)
        if mm:
            return mm
    return find_counterexample(rel, vars_, integer=(_typ in _INT_TYPES or not _typ),
                               nonneg=(_typ in _NAT_TYPES), timeout_s=timeout_s, guards=guards)


def instance_evidence(goal_text: str, k: int = 5, timeout_s: int = 8) -> "dict | None":
    """INSTANCES-FIRST evidence (#124) — `looks_false`'s POSITIVE DUAL, same parse (`_closed_prop` +
    `_FORALL`) and same translation (`_lean_relation_to_sympy`), one home for the Lean→SymPy glue.
    For a computable-shaped bare-∀ arithmetic goal, CONFIRM up to `k` concrete instances before the
    apparatus funds an expensive dispatch on it. Returns
    `{"relation", "vars", "confirmed", "refuted", "evaluated"}` or None (not computable-shaped /
    no definite evaluation — NO-SIGNAL). ADVISORY by contract: confirmed instances are cheap
    confidence + conjecture-book evidence; a `refuted` assignment is the SAME falsity signal
    `looks_false` routes on; the kernel-proved ¬G stays the only refutation verdict."""
    parts = _forall_parts(_closed_prop(goal_text))
    if not parts:
        return None
    vars_, _typ, _body, _props = parts
    gr = _guarded_relation(parts)
    if not gr:
        return None
    rel, guards = gr
    from ztare.common.symbolic_witness import confirm_instances
    ev = confirm_instances(rel, vars_, integer=(_typ in _INT_TYPES or not _typ),
                           nonneg=(_typ in _NAT_TYPES), timeout_s=timeout_s, k=k, guards=guards)
    if ev is None:
        return None
    return {"relation": rel, "vars": vars_, "guards": guards, **ev}


# ── 5. Kronecker / linear-system route (ZTARE_LEANMILL_KRONECKER=1) ────────────────────────────────
# The exogenous-transport niche EXTENDED from a single equality to a CONJUNCTION of equalities — a linear /
# Diophantine SYSTEM existential `∃ c0 c1 …, e0 ∧ e1 ∧ …`. The motivating case is KRONECKER's theorem: a
# rational generating function ⇔ finite Hankel rank, and recovering the recurrence coefficients IS solving the
# Hankel LINEAR SYSTEM for the c's. SymPy solves the system (zero hallucination); the kernel verifies the
# FINITE conjunction (decidable) — a clean closure, unlike the ∀n recurrence claim (which is a SPECIALIZE
# seed, see `recurrence_specialize_seed`). Gated default-OFF (parity); meta path = 'kronecker_system'.
def _split_top_level_conjunction(body: str) -> "list[str]":
    """Split a Lean Prop body on top-level ∧ (also `\\and`, `/\\`). Conservative: no paren-nesting tracking —
    the conjuncts are simple equalities here, and a conjunct that fails to translate aborts the system route."""
    parts = re.split(r"∧|\\and\b|/\\\\?", body)
    return [p.strip() for p in parts if p.strip()]


def is_system_existential(goal_text: str) -> "dict | None":
    """Gate: an existential whose body is a CONJUNCTION of ≥2 arithmetic EQUALITIES (the Hankel-system /
    linear-Diophantine-system shape). Returns {…info, equations:[sympy 'lhs == rhs']} or None. Any conjunct
    that is not a clean single equality (an inequality / connective) aborts → None (conservative)."""
    info = is_computable_existential(goal_text)
    if not info:
        return None
    parts = _split_top_level_conjunction(info["body"])
    if len(parts) < 2:
        return None
    eqs = []
    for p in parts:
        e = lean_body_to_sympy(p)          # the single-equality translator ('' if not a bare equality)
        if not e:
            return None
        eqs.append(e)
    return {**info, "equations": eqs}


_PELL_RE = re.compile(r"(?P<x>\w+)\s*\^\s*2\s*-\s*(?P<D>\d+)\s*\*\s*(?P<y>\w+)\s*\^\s*2\s*=\s*(?P<N>-?\d+)")


def is_pell_existential(goal_text: str) -> "dict | None":
    """Gate: a PELL-form existential `∃ x y : ℤ, x² − D·y² = N [∧ <positivity>]` — the genuinely-LLM-impossible
    witness niche (the fundamental solution can be ENORMOUS). Returns {…info, D, N} or None. Any extra
    conjuncts (e.g. `0 < y` to exclude the trivial (±1,0)) are fine — the diophantine fundamental solution is
    positive and `norm_num` closes them; we only need to find the x²−Dy²=N conjunct to read D, N."""
    info = is_computable_existential(goal_text)
    if not info or len(info["vars"]) != 2 or info["typ"] not in _INT_TYPES:
        return None
    for conj in _split_top_level_conjunction(info["body"]):
        m = _PELL_RE.search(conj.replace(" ", " "))
        if m and {m.group("x"), m.group("y")} == set(info["vars"]):
            return {**info, "D": int(m.group("D")), "N": int(m.group("N")),
                    "pell_vars": [m.group("x"), m.group("y")]}
    return None


_FACTOR_RE = re.compile(r"(?P<a>\w+)\s*\*\s*(?P<b>\w+)\s*=\s*(?P<N>\d{5,})")


def is_factoring_existential(goal_text: str) -> "dict | None":
    """Gate: an INTEGER-factorization existential `∃ x y : ℤ/ℕ, x * y = N ∧ 1 < x ∧ x < N` (bounds in any
    order) — the cleanest exogenous-compute niche: given ONLY the product N (composite, ≥5 digits), find a
    NON-TRIVIAL factor. A pure-text model cannot factor a large semiprime (measured); SymPy `factorint` does it
    instantly. DISTINCT from `kronecker_system` (which is given x+y=S too ⇒ a quadratic, NOT factoring). The
    `1<x` / `x<N` bounds are what make it factoring (they exclude the trivial x=1,y=N); we require at least one
    such bound conjunct so a sumless `x*y=N` alone (trivially witnessed) does NOT fire here.
    Returns {…info, N, factor_vars} or None."""
    info = is_computable_existential(goal_text)
    if not info or len(info["vars"]) != 2 or info["typ"] not in _INT_TYPES:
        return None
    conjs = _split_top_level_conjunction(info["body"])
    prod = None
    for conj in conjs:
        m = _FACTOR_RE.search(conj)
        if m and {m.group("a"), m.group("b")} == set(info["vars"]):
            prod = int(m.group("N")); break
    if prod is None:
        return None
    # require a non-triviality bound (`1 < x`, `x < N`, `x ≠ 1`, …) so this only fires on genuine factoring
    has_bound = any(("<" in c or ">" in c or "≠" in c) for c in conjs)
    if not has_bound:
        return None
    from sympy import isprime  # cheap primality (no factoring) — only fire when N is actually composite
    if prod < 10000 or isprime(prod):
        return None
    return {**info, "N": prod, "factor_vars": list(info["vars"])}


def solve_factor(N: int, timeout_s: int = 12) -> "list[str] | None":
    """EXOGENOUS-COMPUTE: SymPy factors N; return a non-trivial factor pair [x, y] with x the smallest prime
    factor and y = N/x (so 1 < x ≤ y < N). None if N is prime / a unit (no non-trivial factorization). The
    kernel RE-VERIFIES x*y=N ∧ bounds, so a wrong factor cannot mint a closure — sound by construction."""
    from sympy import factorint
    try:
        fic = factorint(int(N))
    except Exception:  # noqa: BLE001
        return None
    primes = sorted(fic)
    if not primes or (len(primes) == 1 and fic[primes[0]] == 1):
        return None  # prime ⇒ no non-trivial factor
    x = primes[0]                       # smallest prime factor (1 < x < N)
    y = N // x
    if x <= 1 or y <= 1 or x * y != N:
        return None
    return [str(x), str(y)]


def recurrence_specialize_seed(seq: "list", max_order: "int | None" = None) -> "dict | None":
    """Kronecker EXOGENOUS-TRANSPORT for the rational/D-finite SUB-case: given a numeric sequence prefix,
    SymPy recovers the minimal linear recurrence (Hankel rank). Returns {order, coeffs, claim} — a SPECIALIZE
    rung seed (the ∀n recurrence is not finitely closable, so this is a transported CONJECTURE the kernel must
    prove, not a direct close). None if no recurrence fits the prefix."""
    rec = find_linear_recurrence(seq, max_order=max_order)
    if not rec:
        return None
    k = rec["order"]
    rhs = " + ".join(f"({rec['coeffs'][i]}) * a (n + {i})" for i in range(k))
    return {**rec, "claim": f"∀ n, a (n + {k}) = {rhs}"}


def solve_witness(goal_text: str, dispatch=None, lean_root=None, timeout_s: int = 12) -> "tuple[str, dict] | None":
    """The full move: gate → direct-SymPy (no LLM) → [Kronecker system route] → LLM-script fallback → inject.
    Returns (lean_tactic, meta) or None. NEVER closes anything — the runner sends the returned tactic to the
    kernel (_verify_compile)."""
    info = is_computable_existential(goal_text)
    if not info:
        return None
    integer = info["typ"] in _INT_TYPES
    sympy_eq = lean_body_to_sympy(info["body"])
    witnesses, path = None, ""
    if sympy_eq:
        witnesses = solve_existential(sympy_eq, info["vars"], integer=integer, timeout_s=timeout_s)
        path = "direct_sympy"
    # Pell-form diophantine route (default-OFF parity): `∃ x y, x²−D·y²=N [∧ 0<y]` — the genuinely-LLM-
    # impossible witness (huge fundamental solution). Checked BEFORE the linear-system route (a Pell body is a
    # single NON-linear equality the direct/system paths can't solve).
    if not witnesses and os.environ.get("ZTARE_LEANMILL_KRONECKER", "1") != "0":
        pell = is_pell_existential(goal_text)
        if pell:
            w = solve_diophantine_pell(pell["D"], pell["N"], pell["pell_vars"], timeout_s=timeout_s)
            if w:
                _vmap = dict(zip(pell["pell_vars"], w))   # reorder to the ∃-binder order for injection
                witnesses = [_vmap[v] for v in info["vars"]]
                path = "pell_diophantine"
    # Factorization route: `∃ x y, x*y = N ∧ 1<x ∧ x<N` — given ONLY the product, find a non-trivial factor.
    # The cleanest exogenous-compute niche (a pure-text model cannot factor a large semiprime; SymPy does it
    # instantly). Distinct from kronecker_system (which leaks the answer via the sum). Same gate flag.
    if not witnesses and os.environ.get("ZTARE_LEANMILL_KRONECKER", "1") != "0":
        fac = is_factoring_existential(goal_text)
        if fac:
            w = solve_factor(fac["N"], timeout_s=timeout_s)
            if w:
                witnesses = w
                path = "factorization"
    # Kronecker / linear-system route (default-OFF parity): a conjunction-bodied existential SymPy can solve as
    # a system, BEFORE spending an LLM call. Only engages when the single-equality direct path found nothing.
    if not witnesses and os.environ.get("ZTARE_LEANMILL_KRONECKER", "1") != "0":
        sysinfo = is_system_existential(goal_text)
        if sysinfo:
            witnesses = solve_linear_system(sysinfo["equations"], sysinfo["vars"], integer=integer, timeout_s=timeout_s)
            path = "kronecker_system"
    if not witnesses and dispatch is not None:
        witnesses = _solve_via_llm(info, goal_text, dispatch, lean_root, timeout_s)
        path = "llm_script"
    if not witnesses:
        return None
    tac = inject_witness_tactic(info, witnesses)
    return (tac, {"info": info, "witnesses": witnesses, "path": path}) if tac else None


def _selftest() -> int:
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    g = is_computable_existential("theorem t : ∃ x : ℤ, x^2 + x = 42 := by sorry")
    ok("gate: detects ∃ over arithmetic", g is not None and g["vars"] == ["x"] and g["typ"] == "ℤ")
    ok("gate: rejects abstract ∃", is_computable_existential("theorem t : ∃ f : ℝ → ℝ, Continuous f := by sorry") is None)
    ok("gate: rejects ∀", is_computable_existential("theorem t : ∀ n : ℕ, n + 0 = n := by sorry") is None)
    ok("gate: strips ∀-telescope", (is_computable_existential("theorem t : ∀ a : ℤ, ∃ x : ℤ, x + a = 0 := by sorry") or {}).get("vars") == ["x"])
    ok("translate: lean ^ → sympy **", lean_body_to_sympy("x^2 + x = 42") == "x**2 + x == 42")
    ok("translate: drops ascription", lean_body_to_sympy("(x : ℤ) = 5").replace(" ", "") in ("x==5", "(x)==5"))
    ok("translate: rejects inequality", lean_body_to_sympy("x^2 < 9") == "")
    ok("inject: integer bare", inject_witness_tactic({"typ": "ℤ"}, ["6"], "norm_num") == "by refine ⟨6, ?_⟩ <;> (norm_num)")
    ok("inject: real cast", "(3/2 : ℝ)" in inject_witness_tactic({"typ": "ℝ"}, ["3/2"], "ring"))
    ok("inject: multi-binder tuple", inject_witness_tactic({"typ": "ℤ"}, ["3", "4"], "decide") == "by refine ⟨3, 4, ?_⟩ <;> (decide)")
    # END-TO-END (real sympy via the COMMON module, no LLM, no Lean): ∃ x : ℤ, x^2 + x = 42 ⇒ x ∈ {6,-7}
    out = solve_witness("theorem t : ∃ x : ℤ, x^2 + x = 42 := by sorry")
    ok("e2e: finds witness + emits refine tactic",
       out is not None and out[1]["path"] == "direct_sympy" and out[0].startswith("by refine ⟨")
       and ({"6", "-7"} & set(out[1]["witnesses"])))
    ok("e2e: abstract goal → None (no transport)",
       solve_witness("theorem t : ∃ f : ℝ → ℝ, Continuous f := by sorry") is None)
    # FACTORIZATION route (exogenous compute): given ONLY the product (no sum), find a non-trivial factor of a
    # composite N. 1000003*1000033 = 1000036000099. A bare text model can't factor; SymPy does.
    _fc = solve_witness("theorem t : ∃ x y : ℤ, x * y = 1000036000099 ∧ 1 < x ∧ x < 1000036000099 := by sorry")
    ok("e2e: factorization path finds a non-trivial factor",
       _fc is not None and _fc[1]["path"] == "factorization"
       and sorted(int(w) for w in _fc[1]["witnesses"]) == [1000003, 1000033])
    ok("factoring gate: a PRIME N → None (no non-trivial factorization)",
       is_factoring_existential("theorem t : ∃ x y : ℤ, x * y = 1000003 ∧ 1 < x ∧ x < 1000003 := by sorry") is None)
    ok("factoring gate: no non-triviality bound → None (x=1 is a trivial witness, not factoring)",
       is_factoring_existential("theorem t : ∃ x y : ℤ, x * y = 1000036000099 := by sorry") is None)
    ok("solve_factor: prime returns None", solve_factor(1000003) is None)
    # looks_false — the falsity signal (router → falsify)
    ok("looks_false: a FALSE ∀ (n+1=n) is detected",
       looks_false("theorem t : ∀ n : ℤ, n + 1 = n := by sorry") is not None)
    ok("looks_false: a TRUE ∀ (n+0=n) → None",
       looks_false("theorem t : ∀ n : ℤ, n + 0 = n := by sorry") is None)
    ok("looks_false: guarded-TRUE ∀ (H → C, C holds under H) → None",
       looks_false("theorem t : ∀ n : ℕ, n = n → n + 1 = n + 1 := by sorry") is None)
    _lf = looks_false("theorem t : ∀ n : ℕ, 2 <= n → n * n <= 2 * n := by sorry")
    ok("looks_false: guarded-FALSE detected at an ADMITTED point (n≥3; n=0,1 never misfire)",
       _lf is not None and int(_lf[0]) >= 3)
    ok("looks_false: untranslatable hypothesis ⇒ None (admissibility uncertifiable)",
       looks_false("theorem t : ∀ n : ℕ, Nat.Prime n → n + 1 = n := by sorry") is None)
    # ℕ vs ℤ: `0 ≤ n` is TRUE over ℕ (no counterexample) but FALSE over ℤ (n=-1) — the type MUST gate the
    # grid so a counterexample invalid for the actual type never misfires the router to falsify.
    ok("looks_false: true-over-ℕ not misfired (nonneg grid)",
       looks_false("theorem t : ∀ n : ℕ, 0 <= n := by sorry") is None)
    ok("looks_false: false-over-ℤ detected", looks_false("theorem t : ∀ n : ℤ, 0 <= n := by sorry") is not None)
    # instance_evidence (#124) — looks_false's POSITIVE dual through the SAME parse/translation
    _ie = instance_evidence("theorem t : ∀ n : ℕ, n <= n * n := by sorry")
    ok("instances: true-over-ℕ confirmed (≥3 instances, no refutation)",
       _ie is not None and len(_ie["confirmed"]) >= 3 and _ie["refuted"] is None)
    _ie = instance_evidence("theorem t : ∀ n : ℤ, n + 1 = n := by sorry")
    ok("instances: false ∀ ⇒ refuting assignment (the looks_false signal, zero fake confidence)",
       _ie is not None and _ie["refuted"] is not None and not _ie["confirmed"])
    ok("instances: binder-signature goal closed to ∀ (theorem (n : ℕ) : …)",
       (instance_evidence("theorem t (n : ℕ) : n <= n + 1 := by sorry") or {}).get("refuted", "x") is None)
    # the parenthesized-∀ hole the gate exposed: `∀ (n : ℕ), …` (what _closed_goal_prop emits) used to
    # mis-split as vars='(n' typ='ℕ)' ⇒ silent no-signal in looks_false TOO. Both duals must parse it.
    ok("looks_false: parenthesized binder parsed (false-over-ℤ detected)",
       looks_false("theorem t (n : ℤ) : 0 <= n := by sorry") is not None)
    _ie = instance_evidence("theorem t : ∀ (a : ℤ) (b : ℤ), a + b = b + a := by sorry")
    ok("instances: same-type multi-group telescope PEELED (commutativity confirmed)",
       _ie is not None and len(_ie["confirmed"]) >= 3 and _ie["refuted"] is None)
    ok("instances: MIXED-type telescope degrades to None (conservative)",
       instance_evidence("theorem t : ∀ (a : ℤ) (x : ℝ), a + 0 = a := by sorry") is None)
    # GUARDED goals (H → C) — formerly skipped, now evaluated on hypothesis-ADMITTED points only
    _ie = instance_evidence("theorem t : ∀ n : ℕ, 2 <= n → 2 * n <= n * n := by sorry")
    ok("instances: guarded-TRUE confirmed on admitted points (2≤n → 2n≤n²)",
       _ie is not None and len(_ie["confirmed"]) >= 3 and _ie["refuted"] is None and len(_ie["guards"]) == 1)
    _ie = instance_evidence("theorem t : ∀ n : ℕ, 2 <= n → n * n <= 2 * n := by sorry")
    ok("instances: guarded-FALSE refuted at an admitted point (n≥3; n=0,1 never misfire)",
       _ie is not None and _ie["refuted"] is not None and int(_ie["refuted"][0]) >= 3)
    _ie = instance_evidence("theorem t : ∀ (n : ℕ) (h : 2 <= n), 2 * n <= n * n := by sorry")
    ok("instances: hypothesis-BINDER (h : 2 ≤ n) becomes a guard, not a variable",
       _ie is not None and len(_ie["confirmed"]) >= 3 and _ie["refuted"] is None and len(_ie["guards"]) == 1)
    ok("instances: untranslatable hypothesis ⇒ None (admissibility uncertifiable)",
       instance_evidence("theorem t : ∀ n : ℕ, Nat.Prime n → n + 1 = n := by sorry") is None)
    ok("instances: abstract goal → None (no carrier)",
       instance_evidence("theorem t : ∀ f : ℝ → ℝ, Continuous f := by sorry") is None)

    # ── Kronecker / linear-system route (gated, default-OFF) ──
    _sys_goal = "theorem t : ∃ c0 c1 : ℤ, c0 + c1 = 5 ∧ c0 - c1 = 1 := by sorry"
    ok("system: gate detects conjunction existential",
       (is_system_existential(_sys_goal) or {}).get("equations") == ["c0 + c1 == 5", "c0 - c1 == 1"])
    ok("system: gate rejects single-equality (not a system)",
       is_system_existential("theorem t : ∃ x : ℤ, x + 1 = 5 := by sorry") is None)
    _ksave = os.environ.get("ZTARE_LEANMILL_KRONECKER")
    try:
        os.environ["ZTARE_LEANMILL_KRONECKER"] = "0"   # default is ON now; =0 is the explicit A/B baseline
        # PARITY: flag OFF + no dispatch ⇒ the system goal is NOT solved by the deterministic route (None).
        ok("system: parity when flag =0 (no kronecker route)", solve_witness(_sys_goal) is None)
        os.environ["ZTARE_LEANMILL_KRONECKER"] = "1"
        _out = solve_witness(_sys_goal)
        ok("system: flag ON solves the system + emits multi-binder refine",
           _out is not None and _out[1]["path"] == "kronecker_system"
           and _out[1]["witnesses"] == ["3", "2"] and _out[0] == "by refine ⟨3, 2, ?_⟩ <;> (first | norm_num | ring | decide | omega | simp_all)")
    finally:
        os.environ.pop("ZTARE_LEANMILL_KRONECKER", None) if _ksave is None else os.environ.__setitem__("ZTARE_LEANMILL_KRONECKER", _ksave)
    # ── Pell-form diophantine route (the genuinely-LLM-impossible witness niche) ──
    _pell_goal = "theorem t : ∃ x y : ℤ, x ^ 2 - 61 * y ^ 2 = 1 ∧ 0 < y := by sorry"
    _pi = is_pell_existential(_pell_goal)
    ok("pell: gate detects x²−61y²=1 (D=61, N=1)", _pi is not None and _pi["D"] == 61 and _pi["N"] == 1)
    ok("pell: gate rejects a non-Pell existential", is_pell_existential("theorem t : ∃ x : ℤ, x + 1 = 5 := by sorry") is None)
    _ksave2 = os.environ.get("ZTARE_LEANMILL_KRONECKER")
    try:
        os.environ["ZTARE_LEANMILL_KRONECKER"] = "0"   # default is ON now; =0 is the explicit A/B baseline
        ok("pell: parity when flag =0", solve_witness(_pell_goal) is None)
        os.environ["ZTARE_LEANMILL_KRONECKER"] = "1"
        _po = solve_witness(_pell_goal)
        ok("pell: flag ON emits the HUGE fundamental witness via diophantine",
           _po is not None and _po[1]["path"] == "pell_diophantine"
           and _po[1]["witnesses"] == ["1766319049", "226153980"]
           and _po[0].startswith("by refine ⟨1766319049, 226153980, ?_⟩"))
    finally:
        os.environ.pop("ZTARE_LEANMILL_KRONECKER", None) if _ksave2 is None else os.environ.__setitem__("ZTARE_LEANMILL_KRONECKER", _ksave2)
    # recurrence → SPECIALIZE seed (Kronecker rational/D-finite sub-case): Fibonacci ⇒ a(n+2)=a(n+1)+a(n)
    _seed = recurrence_specialize_seed([0, 1, 1, 2, 3, 5, 8, 13])
    ok("recurrence seed: Fibonacci ⇒ order-2 claim",
       _seed is not None and _seed["order"] == 2 and "a (n + 2) =" in _seed["claim"] and "a (n + 0)" in _seed["claim"])
    ok("recurrence seed: non-recurrent prefix → None", recurrence_specialize_seed([2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31]) is None)

    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(_selftest())
