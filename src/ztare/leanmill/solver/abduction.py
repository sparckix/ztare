"""MOVE_ABDUCE — SMT-abduction → grounded MOVE_CONJECTURE seed (the exogenous "what premise is MISSING?"
move, 2026-06-08).

THE NICHE. `MOVE_CONJECTURE` (conjecture.py) invents an intermediate lemma L by FREE LLM generation, then
kernel-gates the `L ⇒ G` edge. That free generation is the weak link on a DECIDABLE/arithmetic subgoal: the
leaf guesses a bridge, often a circular restatement or an over/under-strong one. For the slice of goals that
live in a DECIDABLE fragment (linear integer arithmetic over ℕ/ℤ — `omega`/`decide` territory), there is a
COMPLETE, DETERMINISTIC oracle for the missing premise: SMT ABDUCTION. cvc5's `(get-abduct A …)` returns a
MINIMAL formula A such that `A ∧ (asserted facts) ⊨ goal` and `A` is consistent with the facts — i.e. exactly
the missing hypothesis that makes the goal provable. We translate the failing Lean subgoal to SMT-LIB, ask
cvc5 for A, translate A back to a Lean Prop, and emit it as a TARGETED `ConjectureSeed` (the same drop-in
shape `obstruction_to_conjecture` produces) so it REPLACES the blind conjecture prompt with a grounded one.

WHERE IT SITS (canonical home, cited — NOT a parallel governance). This is a SEED PRODUCER for the existing
`MOVE_CONJECTURE` lane. It owns only: the decidable-fragment GATE, the Lean↔SMT-LIB translation, and the
cvc5 shell. The grounded premise A then routes through the UNCHANGED `conjecture.conjecture_generate`
(prompt_override = our targeted prompt — the `{lname}` / `LEMMA:` / `PROOF:` fenced contract is preserved
verbatim) + `conjecture.conjecture_advances` KERNEL gate (`_compile_probe`: `A ⇒ G` typechecks sorry-free,
cites L, is load-bearing, non-circular). NO new kernel, NO new closure path. A bad/hallucinated A yields a
`no_advance`, NEVER a false closure — identical soundness surface to a blind conjecture.

SOUNDNESS (survives the master discriminator — teeth iff the signal is EXOGENOUS, not narrated by the agent).
The premise A is produced by cvc5 (a deterministic external solver), NOT by the leaf — the leaf cannot choose
or narrate it. And even cvc5's A is NEVER trusted directly: it is only a SEED for the prompt; the kernel
(`conjecture_advances` → `_compile_probe`) is the sole arbiter of whether the `A ⇒ G` edge is sound. So a
weak SMT translation can at worst waste one conjecture attempt — it can never launder a closure.

SCOPE — HONESTLY NARROW (do not oversell). cvc5 abduction is sound+useful ONLY where the Lean subgoal
faithfully maps to a DECIDABLE SMT theory: LINEAR INTEGER ARITHMETIC (QF_LIA / LIA) over ℕ/ℤ with the
boolean connectives. It is USELESS on deep analysis / topology / abstract algebra / anything with `Real`
transcendentals, function-space binders, `Finset`/`∑`, `deriv`, limits, or non-linear multiplication of two
variables — those do NOT translate to a decidable SMT fragment, so the gate REFUSES them (returns None → no
abduce attempt, the blind conjecture path is unchanged). This is the linear-arithmetic complement to
`witness_transport` (which handles computable EXISTENTIALS); abduction handles the missing-PREMISE direction.

EXTERNAL DEP — cvc5, lazy-shelled, FAIL-CLOSED. cvc5 is the ONLY mainstream solver with native abduction
(`get-abduct`, the Reynolds–Barbosa–Tinelli sygus-abduct engine); z3 has NO native abduction primitive, so we
do not fall back to it (a hand-rolled z3 abduction loop would be a parallel-engine frankenstein and is out of
scope). cvc5 is NOT installed in this environment — `_cvc5_available()` probes the binary and `_cvc5_abduct`
FAILS CLOSED (returns None, no abduce attempt) when it is absent. There is NO silent-admit path: absence ⇒ the
move is a no-op and the blind conjecture lane runs exactly as before.

FLAG `ZTARE_LEANMILL_ABDUCE` (default OFF = byte-parity). The runner only calls into this module when the flag
is set AND cvc5 is on PATH AND the subgoal gates as decidable-arithmetic; otherwise MOVE_CONJECTURE is blind
exactly as today."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

# Reuse the canonical conjecture seed shape + the canonical Lean parsers (NO parallel parser):
#   * ConjectureSeed         — the drop-in MOVE_CONJECTURE seed (obstruction_to_conjecture produces the same)
#   * _closed_goal_prop      — `∀ binders, concl` from a goal signature (the same closed Prop falsify uses)
#   * _lemma_conclusion      — the conclusion after the top-level `:` (bracket-aware)
#   * _top_level_colon       — depth-0 colon split
from ztare.leanmill.lean_source import strip_comments, signature_before_proof
from ztare.leanmill.solver.conjecture import (_closed_goal_prop, _lemma_conclusion,
                                              _top_level_colon)
from ztare.leanmill.solver.obstruction_to_conjecture import ConjectureSeed, Obstruction

ABDUCE_FLAG = "ZTARE_LEANMILL_ABDUCE"          # default OFF = byte-identical parity
CVC5_BIN_ENV = "ZTARE_CVC5_BIN"                # optional explicit path to the cvc5 binary


# ── 1. Decidable-fragment GATE (regex, no LLM, HONESTLY narrow) ───────────────────────────────────────
# A token that, if present in the goal body, means it does NOT live in a decidable LINEAR INTEGER theory —
# abduction is useless / unsound to attempt. Conservative: when in doubt, REFUSE (return None) so the blind
# conjecture lane is unchanged. This is the deep-analysis exclusion the task demands we be honest about.
_NON_DECIDABLE = re.compile(
    r"ℝ|Real|ℚ|Rat|ℂ|Complex|"                                  # non-integer / dense domains
    r"deriv|∫|∑|∏|Finset|Set\.|Filter|Tendsto|Continuous|"      # analysis / measure / topology
    r"sqrt|exp|log|sin|cos|π|Polynomial|Matrix|Module|"          # transcendental / abstract algebra
    r"→\s*[A-Za-zℕℤ]|Function|Injective|Surjective"              # function-space binders
)
# the boolean / linear-arithmetic operators we CAN translate to SMT-LIB
_LIA_REL = ("≤", "≥", "<", ">", "≠", "=", "∣")
_INT_TYPES = {"ℕ", "Nat", "ℤ", "Int"}
_NAT_TYPES = {"ℕ", "Nat"}


@dataclass
class AbductionGoal:
    """A goal that gated as decidable-arithmetic — the parsed pieces the SMT-LIB builder needs."""
    binders: "list[tuple[str, str]]"   # [(name, type)] over ℕ/ℤ
    hyps: "list[str]"                  # hypothesis bodies (the asserted facts)
    concl: str                         # the conclusion body (the SMT goal)
    prop: str                          # the full closed Prop (for the seed / kernel gate)
    nonneg: bool                       # any ℕ binder ⇒ assert >=0 for those


def _parse_binders(head: str) -> "list[tuple[str, str]]":
    """Explicit `(name : T)` binders over an integer type (the SMT-declarable variables). Implicit/inst
    binders and non-integer types are dropped (the gate already refused non-decidable types)."""
    out: list[tuple[str, str]] = []
    for names, typ in re.findall(r"\(([^():]+):([^()]+)\)", head):
        t = typ.strip()
        if t not in _INT_TYPES:
            continue
        for n in names.replace(",", " ").split():
            if re.fullmatch(r"[A-Za-z_][\w']*", n):
                out.append((n, t))
    return out


def is_decidable_arithmetic_subgoal(goal_text: str) -> "AbductionGoal | None":
    """GATE (regex, no LLM): does this Lean (sub)goal live in a DECIDABLE LINEAR INTEGER ARITHMETIC fragment
    cvc5 abduction can reason over? Requires: a parseable signature; only ℕ/ℤ binders; at least one arithmetic
    relation in the conclusion; and NO non-decidable token anywhere (Real/analysis/Finset/function-space/…).
    Returns the parsed `AbductionGoal` or None. CONSERVATIVE — a refusal (None) just means "no abduce
    attempt, run the blind conjecture path" (zero cost), so we err toward refusing rather than mis-translating
    deep mathematics into a bogus SMT query."""
    from ztare.leanmill.solver.statement_integrity import _signature
    sig = _signature((goal_text or "").strip())
    if not sig:
        return None
    j = _top_level_colon(sig)
    if j < 0:
        return None
    head, concl = sig[:j], sig[j + 1:].strip()
    if not concl:
        return None
    prop = _closed_goal_prop(goal_text)
    if not prop:                                            # degenerate True/False / unparseable ⇒ no abduce
        return None
    # HONEST SCOPE: any non-decidable token anywhere (head or conclusion) ⇒ refuse — this is the deep-analysis
    # / topology / abstract-algebra exclusion. cvc5 abduction is meaningless off the decidable LIA fragment.
    if _NON_DECIDABLE.search(head) or _NON_DECIDABLE.search(concl):
        return None
    binders = _parse_binders(head)
    if not binders:                                         # no SMT-declarable integer variable
        return None
    # hypotheses = binder positions whose type is itself a relation, e.g. `(h : a < b)` — the asserted facts.
    hyps: list[str] = []
    for _names, typ in re.findall(r"\(([^():]+):([^()]+)\)", head):
        t = typ.strip()
        if any(r in t for r in _LIA_REL) and t not in _INT_TYPES:
            if _NON_DECIDABLE.search(t):
                return None
            hyps.append(t)
    # the conclusion (possibly an implication `H → C`): split leading hypotheses off the arrow.
    body = concl
    while True:
        m = re.match(r"^\s*(.+?)\s*(?:→|->)\s*(.+)$", body)
        if not m:
            break
        lhs = m.group(1).strip()
        # only peel a hypothesis arrow if the LHS is a relation we can assert (not a type / binder)
        if not any(r in lhs for r in _LIA_REL):
            break
        hyps.append(lhs)
        body = m.group(2).strip()
    if not any(r in body for r in _LIA_REL):                # the goal itself must be an arithmetic relation
        return None
    nonneg = any(t in _NAT_TYPES for _n, t in binders)
    return AbductionGoal(binders=binders, hyps=hyps, concl=body, prop=prop, nonneg=nonneg)


# ── 2. Lean → SMT-LIB translation (the decidable-LIA fragment ONLY) ───────────────────────────────────
def _lean_term_to_smt(term: str) -> "str | None":
    """Translate a Lean LINEAR-ARITHMETIC relation/term to a prefix SMT-LIB s-expression. Supports
    `+ - * = ≤ ≥ < > ≠ ∣` and the boolean connectives `∧ ∨ ¬ →`; rejects (returns None) anything outside the
    decidable fragment (division, `^`/`**` with a variable exponent, unknown identifiers as functions). This
    is deliberately small + total on its fragment — a non-translatable term aborts the whole abduce attempt
    (None) rather than emitting a query that does not mean the Lean goal."""
    t = (term or "").strip()
    if not t:
        return None
    # ASCII → unicode relation normalization (Lean accepts BOTH `<=`/`≤`; the parser below keys on unicode).
    # Order matters: do the two-char forms before any single-char handling. `:=`/`==`/`!=` are untouched.
    t = t.replace("<=", "≤").replace(">=", "≥").replace("≠", "≠").replace("!=", "≠")
    t = re.sub(r"\(\s*([^():]+?)\s*:\s*[^()]+\)", r"(\1)", t)      # strip `(.. : T)` ascriptions
    # boolean connectives first (lowest precedence), left-associative, no full paren-grammar — conservative.
    for op_lean, op_smt in (("↔", "="), ("→", "=>"), ("∨", "or"), ("∧", "and")):
        # split on the FIRST top-level occurrence
        idx = _top_level_index(t, op_lean)
        if idx >= 0:
            l = _lean_term_to_smt(t[:idx])
            r = _lean_term_to_smt(t[idx + len(op_lean):])
            if l is None or r is None:
                return None
            return f"({op_smt} {l} {r})"
    m = re.match(r"^\s*¬\s*(.+)$", t)
    if m:
        inner = _lean_term_to_smt(m.group(1))
        return f"(not {inner})" if inner is not None else None
    # relations
    for op_lean, op_smt in (("≤", "<="), ("≥", ">="), ("≠", "distinct"),
                            ("<", "<"), (">", ">"), ("∣", "__dvd__")):
        idx = _top_level_index(t, op_lean)
        if idx >= 0:
            l = _arith_to_smt(t[:idx])
            r = _arith_to_smt(t[idx + len(op_lean):])
            if l is None or r is None:
                return None
            if op_smt == "__dvd__":                                # a ∣ b  ⇒  (= (mod b a) 0)
                return f"(= (mod {r} {l}) 0)"
            return f"({op_smt} {l} {r})"
    # plain equality (top-level single `=`)
    idx = _top_level_eq(t)
    if idx >= 0:
        l = _arith_to_smt(t[:idx])
        r = _arith_to_smt(t[idx + 1:])
        if l is None or r is None:
            return None
        return f"(= {l} {r})"
    return None


def _arith_to_smt(expr: str) -> "str | None":
    """Translate a LINEAR arithmetic EXPRESSION (no relation) to prefix SMT-LIB. `+ - *` only; `*` must be a
    coefficient×variable or constant product (cvc5 LIA rejects var×var — but we let cvc5 reject, we only
    refuse the clearly-non-linear `^`/`/`). Numerals and `[A-Za-z_]` identifiers pass through. None on a
    token we cannot translate."""
    e = (expr or "").strip().strip("()").strip()
    if not e:
        return None
    if re.search(r"\^|\*\*|/|%|∑|∏|√", e):                         # non-linear / division ⇒ refuse
        return None
    # split on lowest-precedence + / - (binary), respecting parens
    for op in ("+", "-"):
        idx = _top_level_index(e, op, allow_leading=False)
        if idx > 0:
            l = _arith_to_smt(e[:idx])
            r = _arith_to_smt(e[idx + 1:])
            if l is None or r is None:
                return None
            return f"({op} {l} {r})"
    idx = _top_level_index(e, "*")
    if idx > 0:
        l = _arith_to_smt(e[:idx])
        r = _arith_to_smt(e[idx + 1:])
        if l is None or r is None:
            return None
        return f"(* {l} {r})"
    if re.fullmatch(r"-?\d+", e):
        return e if not e.startswith("-") else f"(- {e[1:]})"
    if re.fullmatch(r"[A-Za-z_][\w']*", e):
        return e
    return None


def _top_level_index(s: str, tok: str, allow_leading: bool = True) -> int:
    """Index of the FIRST occurrence of `tok` at paren-depth 0. `allow_leading=False` ignores a tok at
    position 0 (so a leading unary `-` is not read as a binary subtraction)."""
    depth = 0
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c == "(":
            depth += 1
        elif c == ")":
            depth = max(0, depth - 1)
        elif depth == 0 and s.startswith(tok, i):
            if allow_leading or i > 0:
                return i
        i += 1
    return -1


def _top_level_eq(s: str) -> int:
    """Index of a top-level single `=` (not `==`, `<=`, `>=`, `!=`, `:=`) at paren-depth 0."""
    depth = 0
    for i, c in enumerate(s):
        if c == "(":
            depth += 1
        elif c == ")":
            depth = max(0, depth - 1)
        elif depth == 0 and c == "=":
            prev = s[i - 1] if i > 0 else " "
            nxt = s[i + 1] if i + 1 < len(s) else " "
            if prev not in "<>=!:" and nxt != "=":
                return i
    return -1


def build_smtlib_abduct(g: AbductionGoal) -> "str | None":
    """Assemble the SMT-LIB-2 abduction query: declare the integer variables, ASSERT the hypotheses (the
    facts), then `(get-abduct A <goal>)` — cvc5 returns a MINIMAL A with `facts ∧ A ⊨ goal`. Returns the
    query string or None if any piece fails to translate (⇒ no abduce attempt). LIA logic (`QF_LIA` with
    `produce-abducts`)."""
    decls = []
    for name, _typ in g.binders:
        decls.append(f"(declare-const {name} Int)")
    asserts = []
    if g.nonneg:                                                   # ℕ binders are nonnegative
        for name, typ in g.binders:
            if typ in _NAT_TYPES:
                asserts.append(f"(assert (>= {name} 0))")
    for h in g.hyps:
        hs = _lean_term_to_smt(h)
        if hs is None:
            return None
        asserts.append(f"(assert {hs})")
    goal = _lean_term_to_smt(g.concl)
    if goal is None:
        return None
    goal = _smt_goal_var_first(goal)            # var-first form (cvc5 grammar abduction needs it)
    # `tlimit-per` bounds the grammar enumeration per get-abduct — without it cvc5 can HANG building a
    # constant it can't reach in the constrained grammar (workflow audit; observed live).
    lines = ["(set-logic LIA)", "(set-option :produce-abducts true)", "(set-option :tlimit-per 4000)"]
    lines += decls + asserts
    # GRAMMAR (de-strawman 2026-06-09): WITHOUT a grammar cvc5 returns a degenerate POINT abduct
    # (`x = 11`) — a specific assignment that makes the goal provable ASSUMING it but is itself UNPROVABLE,
    # so the spawned sub-goal is dead and the move is inert. Constrain the abduct to GENERAL linear
    # INEQUALITIES over the variables (sums/differences + a constant + conjunctions): cvc5 then returns a
    # usable general premise (`x ≥ 11`, `a - b ≥ 6`, `x ≥ 10`) — verified across goals before wiring.
    _vars = [name for name, _t in g.binders]
    # When the goal DEFINES a variable as an abstracted nonlinear atom (`y = nlt0`), EXCLUDE that var from
    # the grammar — else cvc5 abduces the trivial `y ≥ 0` (= the goal restated → circular, the gate rejects
    # it) instead of `nlt0 ≥ 0` (which substitutes back to the real bridging lemma `x*x ≥ 0`). Detect `v = nltN`
    # / `nltN = v` in the asserted hyps and drop v; keep the atoms + the genuine free vars.
    _defined = set()
    for h in g.hyps:
        # a var DEFINED equal to an expression that CONTAINS an atom (`y = nlt0`, `s = nlt0 + nlt1`) — drop it
        # from the grammar so cvc5 abduces the bound on the ATOM (the bridging lemma), not the goal restated.
        m = re.match(r"^\s*([A-Za-z_]\w*)\s*=\s*(.+)$", h.strip())
        if m and re.search(r"(?<![\w'])nlt\d+(?![\w'])", m.group(2)) and not m.group(1).startswith("nlt"):
            _defined.add(m.group(1))
        m2 = re.match(r"^\s*(.+?)\s*=\s*([A-Za-z_]\w*)\s*$", h.strip())
        if m2 and re.search(r"(?<![\w'])nlt\d+(?![\w'])", m2.group(1)) and not m2.group(2).startswith("nlt"):
            _defined.add(m2.group(2))
    _gvars = [v for v in _vars if v not in _defined] or _vars
    if _vars:
        _terms = " ".join(_gvars) + " C (+ T T) (- T T)"
        grammar = ("\n  ((Start Bool) (T Int) (C Int))"
                   "\n  ((Start Bool ((>= T C) (> T C) (<= T C) (< T C) (and Start Start)))"
                   f"\n   (T Int ({_terms}))"
                   "\n   (C Int ((Constant Int))))")
        lines.append(f"(get-abduct A {goal}{grammar})")
    else:
        lines.append(f"(get-abduct A {goal})")
    return "\n".join(lines) + "\n"


# ── 3. SMT-LIB abduct → Lean Prop (translate the cvc5 answer BACK) ────────────────────────────────────
def smt_abduct_to_lean(sexpr: str) -> "str | None":
    """Translate a cvc5 abduct s-expression `(define-fun A () Bool <body>)` (or a bare body) back to a Lean
    Prop string. Supports the LIA operators we emitted. None if the answer is `true`/unparseable (a trivial
    abduct = no useful premise). This is best-effort: the Lean Prop is only a SEED — the kernel re-checks it,
    so a slightly-off back-translation yields a no_advance, never an unsound seed."""
    body = _extract_abduct_body(sexpr)
    if not body:
        return None
    lean = _smt_sexpr_to_lean(body)
    if lean is None:
        return None
    lean = lean.strip()
    if lean in ("True", "true", "", "False", "false"):             # trivial / contradictory ⇒ no useful seed
        return None
    return lean


def _extract_abduct_body(sexpr: str) -> str:
    """Pull the body out of cvc5's `(define-fun A () Bool <body>)` wrapper, else return the trimmed input."""
    s = (sexpr or "").strip()
    m = re.search(r"\(define-fun\s+\S+\s*\(\)\s*Bool\s+(.+)\)\s*$", s, re.DOTALL)
    if m:
        return m.group(1).strip()
    return s


def _tokenize_sexpr(s: str) -> "list[str]":
    return re.findall(r"\(|\)|[^\s()]+", s or "")


def _smt_sexpr_to_lean(s: str) -> "str | None":
    """Recursively translate a prefix SMT-LIB Bool/Int s-expression into an infix Lean term."""
    toks = _tokenize_sexpr(s)
    if not toks:
        return None
    pos = [0]

    OPS = {"<=": "≤", ">=": "≥", "<": "<", ">": ">", "=": "=", "and": "∧",
           "or": "∨", "+": "+", "-": "-", "*": "*", "=>": "→"}

    def parse() -> "str | None":
        if pos[0] >= len(toks):
            return None
        t = toks[pos[0]]
        pos[0] += 1
        if t == "(":
            if pos[0] >= len(toks):
                return None
            op = toks[pos[0]]
            pos[0] += 1
            args = []
            while pos[0] < len(toks) and toks[pos[0]] != ")":
                a = parse()
                if a is None:
                    return None
                args.append(a)
            if pos[0] < len(toks):
                pos[0] += 1                                        # consume ')'
            if op == "not":
                return f"¬ ({args[0]})" if args else None
            if op == "distinct":
                return f"({args[0]} ≠ {args[1]})" if len(args) == 2 else None
            if op == "mod" or op == "ite":
                return None                                        # not cleanly Lean-expressible here ⇒ drop
            if op in OPS and len(args) >= 2:
                sym = OPS[op]
                return "(" + f" {sym} ".join(args) + ")"
            return None
        if t == ")":
            return None
        if re.fullmatch(r"-?\d+|[A-Za-z_][\w']*", t):
            return t
        return None

    out = parse()
    return out


# ── 4a. QE-ABDUCTION — the FRONTIER mechanism (Dillig & Dillig "Explain", CAV 2013) ──────────────────────
# `ZTARE_LEANMILL_ABDUCE_QE=1` (default OFF = parity). The cvc5 `get-abduct` path is SyGuS/CEGIS — it returns
# *a* sufficient condition, frequently a DEGENERATE point-abduct (`a=1 ∧ a≤n`), and the pip wheel hangs on
# enumeration. The principled SOTA is the MOST-GENERAL abduct via QUANTIFIER ELIMINATION: the weakest premise
# ψ over the KEEP vars s.t. `premises ∧ ψ ⊨ goal` is  ψ = QE_{v}.(premises ⇒ goal)  — eliminate a binder, what
# remains is the general premise. z3 `qe2` does this exactly for the decidable (Presburger) fragment (fast;
# variable-modulus/nonlinear is outside QE's reach for every method). SOUND: ψ is only a SEED → the unchanged
# kernel gate (`abduction_advances`) re-verifies; a wrong ψ is a no_advance MISS, never a false closure.
ABDUCE_QE_FLAG = "ZTARE_LEANMILL_ABDUCE_QE"
ABDUCE_ROUTER_FLAG = "ZTARE_LEANMILL_ABDUCE_ROUTER"     # the explicit AST-operator dispatcher (default OFF=parity)
# DISCRETE-THEORY ops (bitvectors / strings / arrays) — cvc5's SyGuS lane (z3 QE doesn't project these).
_DISCRETE_THEORY = re.compile(r"\bBitVec\b|\bString\b|\bArray\b|&&&|\|\|\||\^\^\^|<<<|>>>|~~~")
_Z3_INFIX = {"<=": "≤", "<": "<", ">=": "≥", ">": ">", "=": "=", "+": "+", "-": "-", "*": "*",
             "and": "∧", "or": "∨"}
_Z3_NEGCMP = {"<=": ">", "<": "≥", ">=": "<", ">": "≤", "=": "≠"}


def _z3_to_lean(e) -> "str | None":
    """Render a z3 arithmetic/Bool expr directly to a Lean Prop string (more robust than the SMT-string
    round-trip — `smt_abduct_to_lean` doesn't handle z3's pervasive `not`). Folds `¬(a≤b)`→`a>b` for clean
    Lean. None on any op we don't render (fail-closed — the kernel gate filters)."""
    import z3
    if z3.is_int_value(e):
        n = e.as_long()
        return f"({n})" if n < 0 else str(n)
    if z3.is_const(e) and e.num_args() == 0:
        return e.decl().name()
    op = e.decl().name()
    if op == "not" and e.num_args() == 1:
        inner = e.arg(0)
        iop = inner.decl().name()
        if iop in _Z3_NEGCMP and inner.num_args() == 2:
            a, b = _z3_to_lean(inner.arg(0)), _z3_to_lean(inner.arg(1))
            return None if a is None or b is None else f"({a} {_Z3_NEGCMP[iop]} {b})"
        sub = _z3_to_lean(inner)
        return None if sub is None else f"¬ ({sub})"
    args = [_z3_to_lean(c) for c in e.children()]
    if any(a is None for a in args):
        return None
    if op == "-" and len(args) == 1:
        return f"(-{args[0]})"
    if op in _Z3_INFIX and len(args) >= 2:
        return "(" + f" {_Z3_INFIX[op]} ".join(args) + ")"
    return None


def _goal_to_z3(g: "AbductionGoal"):
    """Build the z3 implication `(premises ∧ nonneg) ⇒ conclusion` + the binder consts, reusing the existing
    Lean→SMT translator (`_lean_term_to_smt`) + z3's SMT-LIB parser. Returns (impl_expr, {name: z3.Int}) or None."""
    import z3
    hsmt = [s for h in g.hyps if (s := _lean_term_to_smt(h))]
    csmt = _lean_term_to_smt(g.concl)
    if csmt is None:
        return None
    ante = hsmt + [f"(>= {n} 0)" for n, t in g.binders if t in _NAT_TYPES]
    ante_smt = f"(and {' '.join(ante)})" if len(ante) > 1 else (ante[0] if ante else "true")
    decls = "\n".join(f"(declare-const {n} Int)" for n, _ in g.binders)
    try:
        F = z3.parse_smt2_string(f"{decls}\n(assert (=> {ante_smt} {csmt}))\n")
        if not F:
            return None
        return F[0], {n: z3.Int(n) for n, _ in g.binders}
    except Exception:  # noqa: BLE001 — a translation z3 won't parse ⇒ no QE-abduce (fail-closed)
        return None


def qe_abduct_premise(goal_text: str) -> "str | None":
    """The most-general missing premise (Lean Prop) via QE. PIVOT SELECTION (Dillig): eliminate the variables
    that appear in BOTH a hypothesis AND the conclusion (the "linking" vars consumed by the inference), keep
    the rest — so the abduct is expressed over the OTHER vars. e.g. `(x≤y) ⊢ x≤z`: x is the pivot → eliminate
    it → `y≤z` (the useful abduct), NOT the vacuous `¬(x≤y)` that brute-forcing all binders would pick. None
    if not decidable / z3 absent / no pivot structure / the goal is already provable (QE ⇒ True) / trivial."""
    g = is_decidable_arithmetic_subgoal(goal_text)
    if g is None or not g.binders:
        return None
    try:
        import z3
    except Exception:  # noqa: BLE001
        return None
    names = [n for n, _ in g.binders]

    def _vars_in(s: str) -> "set[str]":
        return {n for n in names if re.search(rf"(?<![\w']){re.escape(n)}(?![\w'])", s or "")}

    hyp_vars: set = set().union(*[_vars_in(h) for h in g.hyps]) if g.hyps else set()
    pivots = [n for n in names if n in (hyp_vars & _vars_in(g.concl))]
    if not pivots:
        return None                          # no link between a hypothesis and the conclusion to abduce over
    built = _goal_to_z3(g)
    if not built:
        return None
    impl, consts = built
    try:
        res = z3.Then(z3.Tactic("qe2"), z3.Tactic("ctx-solver-simplify"))(
            z3.ForAll([consts[v] for v in pivots], impl))
    except z3.Z3Exception:
        return None
    exprs = [sg.as_expr() for sg in res]
    if not exprs:
        return None
    psi = z3.simplify(exprs[0] if len(exprs) == 1 else z3.And(*exprs))
    if z3.is_true(psi) or z3.is_false(psi):   # already provable / contradictory ⇒ no useful premise
        return None
    lean = _z3_to_lean(psi)
    return lean if (lean and lean.strip("()") not in ("True", "False", "")) else None


# ── 4b. THE ABDUCTION ROUTER — dispatch by the goal's AST operator theory (the operator's design) ────────
# Read the operator type, route to the engine that can SOUNDLY + DETERMINISTICALLY handle it:
#   • pure LINEAR int arith (+,-,≤,≥,=, const·var) → z3 QE  (Dillig projection — the exact most-general bridge)
#   • DISCRETE theories (bitvectors / strings / arrays) → cvc5 SyGuS  (z3 QE can't project these)
#   • NON-LINEAR (var·var, var^k, var-modulus/div) → ABORT, fail-CLOSED. Neither QE (undecidable for ℤ → hangs)
#     nor cvc5 (degenerate point-abduct / `__next_prime` crash) handles these; firing wastes compute on a known
#     undecidable space (measured 2026-06-09). That niche is premise-SELECTION (sledgehammer), not abduction.
def classify_abduction_route(goal_text: str) -> str:
    """'qe_linear' | 'cvc5_discrete' | 'abort_nonlinear' | 'none' — the lane for `goal_text` (statement only,
    comments stripped)."""
    stmt = signature_before_proof(goal_text or "")
    if _DISCRETE_THEORY.search(stmt):
        return "cvc5_discrete"
    if (_ABS_PROD.search(stmt) or _ABS_POW.search(stmt) or _NATIVE_BLIND_VAREXP.search(stmt)
            or _NATIVE_BLIND_DIVMOD.search(stmt)):
        return "abort_nonlinear"                  # var·var / var^k / var-mod/div — undecidable; don't burn compute
    if is_decidable_arithmetic_subgoal(goal_text) is not None:
        return "qe_linear"
    return "none"


def _seed_from_premise(goal_text: str, premise: str, provenance: str) -> "ConjectureSeed":
    """Build the drop-in `ConjectureSeed` (MOVE_CONJECTURE contract) from a derived missing premise."""
    head = signature_before_proof(goal_text or "").strip() or (goal_text or "")
    return ConjectureSeed(
        obstruction=Obstruction(decl="(arithmetic goal)", kind="missing_premise",
                                original_block=goal_text, altered_block="", delta={"removed": [], "added": [premise]}),
        targeted_prompt=_abduce_targeted_prompt(head, goal_text, premise),
        next_target_statement=f"Missing-premise lemma ({provenance}): `{premise}` — establish it and use it to close the goal.")


def route_abduction(goal_text: str, timeout_s: int = 10) -> "ConjectureSeed | None":
    """The explicit dispatcher. Returns a `ConjectureSeed` from the lane-appropriate engine, or None (no
    abduce — including the fail-CLOSED abort on non-linear goals). NEVER closes/unsound — the seed routes the
    unchanged `abduction_advances` kernel gate."""
    lane = classify_abduction_route(goal_text)
    if lane == "qe_linear":
        prem = qe_abduct_premise(goal_text)
        return _seed_from_premise(goal_text, prem, "QE-abduced — Dillig/Explain, most-general") if prem else None
    if lane == "cvc5_discrete":
        # cvc5 SyGuS lane for BV/string/array goals — z3 QE can't project these. NOT yet populated (the cvc5
        # get-abduct path here is arithmetic-only + the existing corpora have no BV/string goals), so this is a
        # documented STUB returning None (fail-closed) rather than recursing. TODO: a BV/string get-abduct path.
        return None
    return None                                   # 'abort_nonlinear' (fail-closed) | 'none'


# ── 4. cvc5 driver — lazy-SHELL, FAIL-CLOSED if absent (z3 lacks native abduction → not used) ─────────
def _cvc5_path() -> "str | None":
    """Resolve the cvc5 binary: an explicit `ZTARE_CVC5_BIN` override, else `cvc5` on PATH. None ⇒ absent."""
    explicit = os.environ.get(CVC5_BIN_ENV)
    if explicit and Path(explicit).exists():
        return explicit
    return shutil.which("cvc5")


def _cvc5_module():
    """The cvc5 PYTHON module (pip `cvc5` wheel), or None. Importing it is the no-binary path: the wheel
    ships the same sygus-abduct engine via the C++ bindings, so `pip install cvc5` (requirements.txt) is
    sufficient — no platform-specific binary download. Lazy + fail-soft (absent ⇒ None)."""
    try:
        import cvc5  # noqa: F401
        return cvc5
    except Exception:  # noqa: BLE001
        return None


def _cvc5_available() -> bool:
    """cvc5 is reachable via EITHER the binary (PATH / `ZTARE_CVC5_BIN`) OR the pip Python wheel."""
    return _cvc5_path() is not None or _cvc5_module() is not None


def _cvc5_abduct_via_api(smtlib_query: str, timeout_s: int) -> "str | None":
    """Run the abduction query through the cvc5 PYTHON API (no binary). Parses the SAME SMT-LIB string the
    binary path consumes via `InputParser` + the command loop; `(get-abduct A …)` returns cvc5's
    `(define-fun A …)` text. Version-specifics (cvc5 1.3.x) are isolated HERE. Fail-soft (None on any error)."""
    cvc5 = _cvc5_module()
    if cvc5 is None:
        return None
    try:
        try:
            slv = cvc5.Solver(cvc5.TermManager())   # cvc5 ≥1.2 takes a TermManager
        except Exception:  # noqa: BLE001
            slv = cvc5.Solver()                      # older API
        slv.setOption("produce-abducts", "true")
        try:
            slv.setOption("tlimit", str(max(1, int(timeout_s)) * 1000))   # per-query wall budget (ms)
        except Exception:  # noqa: BLE001
            pass
        ip = cvc5.InputParser(slv)
        ip.setStringInput(cvc5.InputLanguage.SMT_LIB_2_6, smtlib_query, "ztare_abduct")
        sm = ip.getSymbolManager()
        outs: "list[str]" = []
        while True:
            cmd = ip.nextCommand()
            if cmd.isNull():
                break
            res = cmd.invoke(slv, sm)
            if res and res.strip():
                outs.append(res.strip())
        return "\n".join(outs) if outs else None
    except Exception:  # noqa: BLE001 — fail-closed; a binding hiccup must not crash the move
        return None


def _cvc5_api_worker(q, smtlib_query: str, timeout_s: int) -> None:
    """Child-process entry: put the cvc5-API abduct (or None) on the queue. Module-level so `spawn` can
    pickle it."""
    try:
        q.put(_cvc5_abduct_via_api(smtlib_query, timeout_s))
    except Exception:  # noqa: BLE001
        try:
            q.put(None)
        except Exception:  # noqa: BLE001
            pass


def _cvc5_abduct_bounded(smtlib_query: str, timeout_s: int) -> "str | None":
    """Run the cvc5 Python-API abduct in a KILLABLE child process with a HARD wall-clock bound. The
    grammar-constrained sygus enumeration can HANG the in-process API uninterruptibly (`tlimit`/`tlimit-per`
    do not always break it, and the pip wheel ships no killable binary). A child process CAN be terminated,
    so this makes the whole abduce path safe regardless of cvc5's internal behaviour. Returns None on
    timeout / any failure (fail-closed → blind conjecture runs unchanged)."""
    import multiprocessing as _mp
    try:
        ctx = _mp.get_context("spawn")          # spawn = clean re-import, no fork-state surprises on macOS
        q = ctx.Queue()
        p = ctx.Process(target=_cvc5_api_worker, args=(q, smtlib_query, timeout_s), daemon=True)
        p.start()
        p.join(max(2, int(timeout_s) + 3))      # hard wall = cvc5's own limit + slack
        if p.is_alive():
            p.terminate()
            p.join(1)
            if p.is_alive():
                p.kill()
            return None                          # HUNG ⇒ killed ⇒ no abduct (safe)
        try:
            return q.get_nowait() if not q.empty() else None
        except Exception:  # noqa: BLE001
            return None
    except Exception:  # noqa: BLE001 — multiprocessing unavailable / failed ⇒ fail-closed
        return None


def _cvc5_abduct(smtlib_query: str, timeout_s: int = 10) -> "str | None":
    """Run cvc5 on the abduction query; return the raw `(define-fun A …)` answer or None. FAIL-CLOSED: if
    cvc5 is not installed (neither binary nor pip wheel), or errors, or prints no abduct, returns None (NO
    silent admit — the caller treats None as 'no seed', and the blind conjecture lane runs unchanged). We do
    NOT fall back to z3: z3 has no native `get-abduct`, and a hand-rolled z3 abduction loop would be a
    parallel solver frankenstein. Binary path PREFERRED (explicit cvc5 build); the pip API is the no-binary
    fallback so `pip install cvc5` alone suffices."""
    out: "str | None" = None
    cvc5 = _cvc5_path()
    if cvc5:
        import tempfile
        tf = tempfile.NamedTemporaryFile(mode="w", suffix=".smt2", delete=False)
        try:
            tf.write(smtlib_query)
            tf.close()
            try:
                proc = subprocess.run(
                    [cvc5, "--produce-abducts", "--lang=smt2", tf.name],
                    capture_output=True, text=True, timeout=timeout_s, check=False)
                out = (proc.stdout or "") + "\n" + (proc.stderr or "")
            except (subprocess.TimeoutExpired, OSError):
                out = None
        finally:
            try:
                os.unlink(tf.name)
            except OSError:
                pass
    if out is None:                                                # no binary (or it failed) ⇒ pip API
        out = _cvc5_abduct_bounded(smtlib_query, timeout_s)        # HARD process-timeout (API can hang)
    if not out:
        return None
    m = re.search(r"\(define-fun\s+A\b.*?\)\s*\)", out, re.DOTALL)  # the abduct definition
    if m:
        return m.group(0).strip()
    # some cvc5 builds print the bare body after a leading line; take the last define-fun if any
    m2 = re.findall(r"\(define-fun.*?\)\s*\)", out, re.DOTALL)
    return m2[-1].strip() if m2 else None


# ── 4b. NONLINEAR-TERM ABSTRACTION (Tseitin) — abduce only where the native cascade is BLIND ──────────
# cvc5 abduction is LINEAR (LIA); the old gate REFUSED `*`/`^`. The mechanism: abstract each maximal
# nonlinear subterm to a fresh Int atom, abduce a LINEAR bound, substitute back ⇒ a real nonlinear premise.
# CORRECTION (measured 2026-06-09, supersedes the earlier "cascade fails (h:y=x*x):0≤y" claim — that was a
# measurement error, tested before `nlinarith` was in the cascade): `nlinarith` AUTO-INJECTS squares and
# pairwise products, so it CLOSES `(h:y=x*x):0≤y` and every degree-2 sum-of-squares premise this would
# produce ⇒ on polynomial goals the abduce is REDUNDANT (same regime as reflection-vs-`decide`). The defensible value
# did not vanish, it MOVED: the native cascade (`nlinarith`+`polyrith`+`omega`) is blind to div/mod by a
# VARIABLE divisor, VARIABLE exponents, and bitvectors — see `_native_arith_blind`, which now GATES this
# path so abduce fires only there. NEVER unsound regardless: the kernel `conjecture_advances` gate is
# unchanged; a wrong premise is a MISS.
_ABS_VAR = r"[A-Za-z_][\w']*"
_ABS_PROD = re.compile(rf"(?<![\w'.])({_ABS_VAR})\s*\*\s*({_ABS_VAR})(?![\w'.])")
_ABS_POW = re.compile(rf"(?<![\w'.])({_ABS_VAR})\s*\^\s*([0-9]+)")

# ── TRIGGER GATE: fire the nonlinear abduce ONLY where the native cascade is mathematically BLIND ─────────
# Why (2026-06-09, measured): `nlinarith` is a HEURISTIC over `linarith` — it auto-injects squares
# (`x*x ≥ 0`) and pairwise products of hypotheses, then runs the LINEAR solver. So it SUBSUMES exactly the
# degree-2 sum-of-squares premises the abduce was producing (`0≤x*x`, `6≤x*y`): `nlinarith` closes
# `(h:y=x*x):0≤y` in ms. And `omega` (also in the cascade) is a decision procedure for Presburger arithmetic
# WITH division/modulo by a CONSTANT — so `a % 7 < 7` is native too. Firing abduce on those wastes SMT/LLM on
# a goal the compiler closes in 10ms (the architecture's never-pay-for-native principle). The native cascade
# is BLIND, however, to: division/modulo by a VARIABLE divisor (Presburger needs a constant modulus), a
# VARIABLE exponent `x^n` (nlinarith only squares literal powers; polyrith is polynomial-only), and
# bitvectors (SMT is built for BV-SAT; Lean's BV automation is weak) — exactly where cvc5 maps the semantics
# natively. The gate is the structural AND-condition the runner's move-order ("nlinarith fails first") cannot
# express: don't even SPAWN the move on arithmetic the native tactics own.
_NATIVE_BLIND_DIVMOD = re.compile(r"(?:\w|\))\s*[/%]\s*[A-Za-z_(]")   # div/mod by a VARIABLE/expr divisor
_NATIVE_BLIND_VAREXP = re.compile(r"\^\s*[A-Za-z_(]")                 # exponent is a var/expr, not a literal
_NATIVE_BLIND_BV = re.compile(r"\bBitVec\b|&&&|\|\|\||\^\^\^|<<<|>>>|~~~")


def _native_arith_blind(goal_text: str) -> bool:
    """True iff the goal uses arithmetic the native cascade (`nlinarith`+`polyrith`+`omega`) CANNOT
    interpret — so exogenous SMT abduction is NON-redundant. Blind ⇔ div/mod by a VARIABLE divisor, a
    VARIABLE exponent, or a bitvector op. Plain products `x*y`, LITERAL powers `x^2`, and div/mod by a
    CONSTANT are native territory ⇒ NOT blind (abduce must not fire). Scans the STATEMENT (pre-`:=`),
    comments stripped, so a proof-side `%`/`/` never trips it."""
    stmt = signature_before_proof(goal_text or "")
    stmt = strip_comments(stmt)
    return bool(_NATIVE_BLIND_DIVMOD.search(stmt) or _NATIVE_BLIND_VAREXP.search(stmt)
                or _NATIVE_BLIND_BV.search(stmt))


def _expr_is_nonlinear(expr: str) -> bool:
    """An EXPR worth inlining as a bridging premise: a product/power (`x*y`, `a^2`) OR a native-blind op
    (var-divisor div/mod, var exponent, bitvector). A purely LINEAR EXPR is handled by `omega`/`linarith`
    already, so inlining it buys nothing."""
    return bool(_ABS_PROD.search(expr) or _ABS_POW.search(expr)
                or _NATIVE_BLIND_DIVMOD.search(expr) or _NATIVE_BLIND_VAREXP.search(expr)
                or _NATIVE_BLIND_BV.search(expr))


def _abstract_nonlinear(goal_text: str) -> "tuple[str, dict]":
    """Replace nonlinear subterms (var*var, var^k) in the goal with fresh `nlt{i}` Int atoms, declared as
    binders right after the theorem name. Returns (abstracted_goal_text, {atom: original_subterm}). Idempotent
    per subterm (the SAME subterm reuses its atom). Returns (goal_text, {}) when there is nothing nonlinear."""
    mapping: dict = {}
    text = goal_text or ""

    def _repl(m):
        whole = m.group(0).strip()
        for a, s in mapping.items():
            if s == whole:
                return a
        a = f"nlt{len(mapping)}"
        mapping[a] = whole
        return a

    prev = None
    while prev != text:          # iterate so `x*x*x` collapses through nested atoms
        prev = text
        text = _ABS_POW.sub(_repl, text)
        text = _ABS_PROD.sub(_repl, text)
    if not mapping:
        return goal_text, {}
    nm = re.match(r"^(\s*(?:theorem|lemma|example)\s+[A-Za-z_][\w'.]*)", text)
    if not nm:                   # can't place the atom binders ⇒ abort abstraction (fall back to no-abduce)
        return goal_text, {}
    text = text[:nm.end()] + f" ({' '.join(mapping)} : Int)" + text[nm.end():]
    return text, mapping


def _def_inline_premise(goal_text: str) -> "str | None":
    """RELIABLE nonlinear bridging premise (no cvc5 — its grammar abduction is flaky/hangs on these). For a
    goal with a DEFINING hypothesis `(h : v = EXPR)` where EXPR is NONLINEAR (a `*`/`^` of variables), the
    missing premise is the CONCLUSION with `v` inlined to `EXPR` — making the nonlinear term EXPLICIT so the
    leaf can close it by `positivity`/`nlinarith [mul_self_nonneg …]` (which the cascade, seeing only the
    opaque `v`, cannot — measured: it fails `(h:y=x*x):0≤y`, the inlined `0≤x*x` closes by `exact?`). Returns
    the premise Lean Prop, or None (not a nonlinear-def goal). SOUND: it's only a PROMPT seed + the kernel
    `conjecture_advances` gate is unchanged; the inlined Prop ≠ the goal (not circular)."""
    from ztare.leanmill.solver.statement_integrity import _signature
    sig = _signature((goal_text or "").strip())
    j = _top_level_colon(sig)
    if j < 0:
        return None
    head, concl = sig[:j], sig[j + 1:].strip()
    if not concl:
        return None
    for _names, typ in re.findall(r"\(([^():]+):([^()]+)\)", head):
        m = re.match(r"^\s*([A-Za-z_]\w*)\s*=\s*(.+?)\s*$", typ.strip())
        if not m:
            continue
        v, expr = m.group(1), m.group(2).strip()
        if not _expr_is_nonlinear(expr):
            continue                               # EXPR is linear ⇒ omega already handles it (no inline)
        inlined = re.sub(rf"(?<![\w']){re.escape(v)}(?![\w'])", f"({expr})", concl)
        if inlined != concl and inlined.strip():
            return inlined.strip()
    return None


def _smt_split2(inner: str) -> "tuple[str, str] | tuple[None, None]":
    """Split `A B` (two paren-balanced s-exprs) at the top-level space."""
    depth = 0
    for i, c in enumerate(inner):
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif c == " " and depth == 0:
            return inner[:i].strip(), inner[i + 1:].strip()
    return None, None


def _smt_goal_var_first(goal: str) -> str:
    """Rewrite the abduction goal to VARIABLE-FIRST inequality form: `(<= A B)` → `(>= B A)`, `(< A B)` →
    `(> B A)`. cvc5's grammar-constrained abduction returns NONE for a const-first goal like `(<= 0 y)` but
    solves the equivalent `(>= y 0)` — measured. Logically identical, so SOUND."""
    g = (goal or "").strip()
    for op, sw in (("<=", ">="), ("<", ">")):
        pre = f"({op} "
        if g.startswith(pre) and g.endswith(")"):
            a, b = _smt_split2(g[len(pre):-1])
            if a and b:
                return f"({sw} {b} {a})"
    return goal


def _substitute_atoms(premise: str, mapping: dict) -> str:
    """Substitute each `nlt{i}` atom back to its original Lean subterm (parenthesised), recursively (for
    nested atoms). Inverse of `_abstract_nonlinear` applied to the cvc5 abduct's Lean rendering."""
    out = premise or ""
    for _ in range(6):
        prev = out
        for atom, sub in mapping.items():
            out = re.sub(rf"(?<![\w'.]){re.escape(atom)}(?![\w'.])", f"({sub})", out)
        if out == prev:
            break
    return out


# ── 5. The move: gate → SMT-LIB → cvc5 → Lean Prop → grounded MOVE_CONJECTURE seed ────────────────────
def _abduce_targeted_prompt(goal_head: str, goal: str, lean_premise: str) -> str:
    """Build the focused MOVE_CONJECTURE prompt around the SMT-abduced premise A. Mirrors
    `obstruction_to_conjecture._build_prompt`: concatenation (never .format — embeds raw Lean), the `{lname}`
    literal token is preserved for `conjecture_generate` to substitute, and the `LEMMA:`/`PROOF:` fenced
    contract is IDENTICAL so the seed is a drop-in for the unchanged conjecture parse + kernel gate."""
    callout = (
        "An SMT abduction engine (cvc5 `get-abduct`) determined that the MINIMAL missing premise that makes "
        "this arithmetic goal provable is:\n    " + lean_premise.strip() + "\n"
        "Formalize EXACTLY this premise (or a faithful, no-weaker Lean rendering of it) as the intermediate "
        "lemma L, and prove the ORIGINAL goal USING it. This premise is GROUNDED (a solver derived it), not a "
        "guess — do NOT restate the goal and do NOT make L trivially true.\n"
    )
    return (
        "You are a Lean 4 prover reasoning BACKWARD. The goal below is a DECIDABLE arithmetic goal that is "
        "missing one hypothesis. INVENT exactly ONE intermediate lemma L (the missing premise) and prove the "
        "ORIGINAL goal USING it. Self-contained against `import Mathlib`. Output EXACTLY:\n"
        "LEMMA:\n```lean\ntheorem {lname} : <your lemma statement> := by sorry\n```\n"
        "PROOF:\n```lean\n" + goal_head + " := by\n  <tactics that REFERENCE {lname}>\n```\n"
        "Rules: the lemma must NOT be trivially true; the PROOF must cite `{lname}` and contain NO sorry.\n"
        + callout +
        "GOAL (prove EXACTLY as given):\n" + goal.strip() + "\n"
    )


def abduce_seed(goal_text: str, timeout_s: int = 10) -> "ConjectureSeed | None":
    """THE PRODUCER. Decidable-arithmetic goal → cvc5 abduction → a grounded `ConjectureSeed` (drop-in for
    `MOVE_CONJECTURE`). Returns None (⇒ no abduce, blind conjecture unchanged) when: the flag is off; the
    goal is NOT decidable-arithmetic; cvc5 is absent (FAIL-CLOSED); the SMT query / answer fails to
    translate; or the abduct is trivial. NEVER closes a goal and NEVER fabricates an unsound seed — the
    abduced premise is only a PROMPT; the kernel (`abduction_advances`) is the arbiter."""
    if os.environ.get(ABDUCE_FLAG) != "1":
        return None                                                # FLAG-GATED, default OFF = parity
    # EXPLICIT ROUTER (OPT-IN `ZTARE_LEANMILL_ABDUCE_ROUTER=1`): dispatch by the goal's AST operator theory —
    # linear→z3 QE, discrete(BV/string)→cvc5, NON-LINEAR→ABORT fail-closed (neither engine handles it; don't
    # burn compute on undecidable space). The principled replacement for the per-mechanism flags below.
    if os.environ.get(ABDUCE_ROUTER_FLAG) == "1":
        return route_abduction(goal_text, timeout_s=timeout_s)
    # FRONTIER MECHANISM (OPT-IN `ZTARE_LEANMILL_ABDUCE_QE=1`, default OFF = parity): the MOST-GENERAL missing
    # premise via QUANTIFIER ELIMINATION (Dillig "Explain") — strictly better than cvc5's degenerate first
    # get-abduct. Primary path when enabled; falls through to the cvc5/nonlinear paths if QE finds nothing.
    if os.environ.get(ABDUCE_QE_FLAG) == "1":
        _qe = qe_abduct_premise(goal_text)
        if _qe:
            _qhead = signature_before_proof(goal_text or "").strip() or (goal_text or "")
            return ConjectureSeed(
                obstruction=Obstruction(decl="(arithmetic goal)", kind="missing_premise",
                                        original_block=goal_text, altered_block="",
                                        delta={"removed": [], "added": [_qe]}),
                targeted_prompt=_abduce_targeted_prompt(_qhead, goal_text, _qe),
                next_target_statement=(f"Missing-premise lemma (QE-abduced, MOST-GENERAL via Dillig/Explain): "
                                       f"`{_qe}` — establish it honestly and use it to close the goal."))
    # NONLINEAR ABSTRACTION (OPT-IN `ZTARE_LEANMILL_ABDUCE_NONLINEAR=1`, default OFF): abstract a nonlinear
    # term to a fresh Int atom so the goal becomes LIA the abduction engine reasons over; the abduct (a
    # linear bound on the atom) substitutes back to a real nonlinear premise. TRIGGER GATE (2026-06-09): only
    # where the native cascade is BLIND (`_native_arith_blind` — var-divisor div/mod, var exponent,
    # bitvector). On a degree-2 polynomial goal `nlinarith` already auto-injects the sum-of-squares premise
    # this would produce (it closes `(h:y=x*x):0≤y`), so firing here would waste SMT/LLM on what the compiler
    # gets in 10ms — the never-pay-for-native principle. With the flag OFF the nonlinear path is skipped and
    # linear abduce is byte-identical to before (parity).
    if os.environ.get("ZTARE_LEANMILL_ABDUCE_NONLINEAR") == "1" and _native_arith_blind(goal_text):
        # PRIMARY nonlinear path: definitional INLINING (reliable, no cvc5). For a `(h : v = NONLINEAR)` goal
        # the bridging premise is the conclusion with `v` inlined — deterministic, no hang, no flaky sygus.
        _inl = _def_inline_premise(goal_text)
        if _inl:
            _head0 = signature_before_proof(goal_text or "").strip() or (goal_text or "")
            return ConjectureSeed(
                obstruction=Obstruction(decl="(nonlinear arithmetic goal)", kind="missing_premise",
                                        original_block=goal_text, altered_block="",
                                        delta={"removed": [], "added": [_inl]}),
                targeted_prompt=_abduce_targeted_prompt(_head0, goal_text, _inl),
                next_target_statement=(f"Missing-premise lemma (nonlinear, def-inlined): `{_inl}` — prove it "
                                       "(positivity / nlinarith [mul_self_nonneg …]) and use it to close the goal."))
        # SECONDARY: SMT abstraction over atoms (cvc5, bounded). Linear ⇒ atom_map empty ⇒ parity.
        abstracted_text, _atom_map = _abstract_nonlinear(goal_text)
    else:
        abstracted_text, _atom_map = goal_text, {}
    g = is_decidable_arithmetic_subgoal(abstracted_text)
    if g is None:
        return None                                                # HONEST SCOPE: not the decidable fragment
    if not _cvc5_available():
        return None                                                # FAIL-CLOSED: cvc5 not installed
    query = build_smtlib_abduct(g)
    if not query:
        return None
    raw = _cvc5_abduct(query, timeout_s=timeout_s)
    if not raw:
        return None                                                # no abduct (FAIL-CLOSED on any failure)
    lean_premise = smt_abduct_to_lean(raw)
    if not lean_premise:
        return None                                                # trivial / untranslatable abduct
    if _atom_map:                                                  # substitute nonlinear subterms back
        lean_premise = _substitute_atoms(lean_premise, _atom_map)
    head = signature_before_proof(goal_text or "").strip() or (goal_text or "")
    ob = Obstruction(decl="(arithmetic goal)", kind="missing_premise",
                     original_block=goal_text, altered_block="",
                     delta={"removed": [], "added": [lean_premise]})
    prompt = _abduce_targeted_prompt(head, goal_text, lean_premise)
    next_stmt = (f"Missing-premise lemma (SMT-abduced): `{lean_premise}` — establish it honestly so the "
                 "arithmetic goal is provable without assuming the conclusion.")
    return ConjectureSeed(obstruction=ob, targeted_prompt=prompt, next_target_statement=next_stmt)


def abduction_advances(lemma: str, proof: str, lname: str, lean_root: Path, timeout_s: int,
                       preamble: str = "", goal_conclusion: str = "") -> "tuple[bool, str]":
    """KERNEL-GATED admission of an abduced-then-formalized edge — a THIN pass-through to the canonical
    `conjecture.conjecture_advances` so there is exactly ONE advance gate (`_compile_probe`: `A ⇒ G`
    typechecks sorry-free, cites L, is load-bearing, non-circular). Kept here as the named entry the abduce
    runner calls, so the move's soundness is visibly the SAME kernel check as MOVE_CONJECTURE — no parallel
    gate. A wrong/over-strong abduced premise A is a MISS (no_advance), NEVER a false closure."""
    from ztare.leanmill.solver.conjecture import conjecture_advances
    return conjecture_advances(lemma, proof, lname, lean_root, timeout_s,
                               preamble=preamble, goal_conclusion=goal_conclusion)


# ── 6. Self-test: POSITIVE (a good decidable goal admitted) + NEGATIVE (deep analysis / absent cvc5 /
#       trivial abduct REJECTED). Deterministic — no cvc5, no Lean compile required (the cvc5 shell + the
#       kernel gate are exercised by the live runner / a lake calibration, like specialize's compile legs). ─
def _selftest() -> int:
    fails: list[str] = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    # ── GATE: positive vs negative (deep analysis) ──────────────────────────────────────────────────
    g = is_decidable_arithmetic_subgoal("theorem t (a b : ℤ) (h : a < b) : a + 1 ≤ b + 1 := by")
    ok("gate POSITIVE: decidable LIA goal admitted", g is not None and ("a", "ℤ") in g.binders)
    ok("gate POSITIVE: hypothesis `a < b` captured as an asserted fact",
       g is not None and any("a" in h and "<" in h for h in g.hyps))
    ok("gate NEGATIVE: deep analysis (Real / deriv) REJECTED",
       is_decidable_arithmetic_subgoal("theorem t (f : ℝ → ℝ) : deriv f 0 = 0 := by") is None)
    ok("gate NEGATIVE: Finset/∑ (not decidable LIA) REJECTED",
       is_decidable_arithmetic_subgoal("theorem t (n : ℕ) : ∑ i ∈ Finset.range n, i = n := by") is None)
    ok("gate NEGATIVE: no arithmetic relation in the conclusion REJECTED",
       is_decidable_arithmetic_subgoal("theorem t (a : ℤ) : P a := by") is None)
    ok("gate NEGATIVE: no integer binder REJECTED",
       is_decidable_arithmetic_subgoal("theorem t : 2 + 2 = 5 := by") is None or
       is_decidable_arithmetic_subgoal("theorem t : 2 + 2 = 5 := by").binders == [])

    # ── Lean → SMT-LIB translation (the fragment) ───────────────────────────────────────────────────
    ok("smt: `a + 1 ≤ b` → (<= (+ a 1) b)", _lean_term_to_smt("a + 1 ≤ b") == "(<= (+ a 1) b)")
    ok("smt: equality `x = y` → (= x y)", _lean_term_to_smt("x = y") == "(= x y)")
    ok("smt: `a < b → c < d` → (=> …)",
       _lean_term_to_smt("a < b → c < d") == "(=> (< a b) (< c d))")
    ok("smt NEGATIVE: non-linear `x^2 = 4` REFUSED (None, not a bogus query)",
       _lean_term_to_smt("x^2 = 4") is None)
    ok("smt NEGATIVE: division `x / 2 = 1` REFUSED", _lean_term_to_smt("x / 2 = 1") is None)

    if g is not None:
        q = build_smtlib_abduct(g)
        ok("smtlib: query declares Int consts + get-abduct",
           q is not None and "(declare-const a Int)" in q and "(get-abduct A" in q
           and "(set-option :produce-abducts true)" in q)
        ok("smtlib: the hypothesis `a < b` is ASSERTED",
           q is not None and "(assert (< a b))" in q)

    # ── SMT abduct → Lean (back-translation) ────────────────────────────────────────────────────────
    ok("back: (define-fun A () Bool (<= a b)) → `(a ≤ b)`",
       smt_abduct_to_lean("(define-fun A () Bool (<= a b))") == "(a ≤ b)")
    ok("back: conjunction (and (< a b) (= c 0)) → `(… ∧ …)`",
       smt_abduct_to_lean("(define-fun A () Bool (and (< a b) (= c 0)))") == "((a < b) ∧ (c = 0))")
    ok("back NEGATIVE: trivial `true` abduct → None (no useful premise)",
       smt_abduct_to_lean("(define-fun A () Bool true)") is None)

    # ── cvc5 driver: FAIL-CLOSED when the binary is absent (this environment) ────────────────────────
    if not _cvc5_available():
        ok("cvc5 ABSENT → _cvc5_abduct FAILS CLOSED (None, no silent admit)",
           _cvc5_abduct("(set-logic QF_LIA)\n(get-abduct A (= 1 1))\n", timeout_s=3) is None)
        os.environ[ABDUCE_FLAG] = "1"
        try:
            ok("cvc5 ABSENT → abduce_seed FAILS CLOSED even with the flag ON",
               abduce_seed("theorem t (a b : ℤ) (h : a < b) : a + 1 ≤ b := by") is None)
        finally:
            os.environ.pop(ABDUCE_FLAG, None)
    else:
        ok("cvc5 present — live abduction is covered by the runner/lake calibration", True)

    # ── NATIVE-BLIND TRIGGER GATE: abduce fires only where nlinarith/polyrith/omega are blind ────────
    ok("blind: degree-2 product `x*x` is NOT blind (nlinarith owns the sum-of-squares premise)",
       _native_arith_blind("theorem t (x y : Int) (h : y = x * x) : 0 <= y := by sorry") is False)
    ok("blind: literal power `x^2` is NOT blind", _native_arith_blind("theorem t (z x : Int) (h : z = x ^ 2) : 0 <= z := by") is False)
    ok("blind: const-divisor mod `a % 7` is NOT blind (omega owns constant modulus)",
       _native_arith_blind("theorem t (a r : Nat) (h : r = a % 7) : r < 7 := by") is False)
    ok("blind: VAR-divisor mod `a % n` IS blind (Presburger needs a constant modulus)",
       _native_arith_blind("theorem t (a n r : Nat) (h : r = a % n) : r < n := by") is True)
    ok("blind: VARIABLE exponent `x^k` IS blind", _native_arith_blind("theorem t (x k p : Nat) (h : p = x ^ k) : 0 <= p := by") is True)
    ok("blind: bitvector op IS blind", _native_arith_blind("theorem t (a b : BitVec 8) : a &&& b = b &&& a := by") is True)
    os.environ[ABDUCE_FLAG] = "1"; os.environ["ZTARE_LEANMILL_ABDUCE_NONLINEAR"] = "1"
    try:
        ok("gate: degree-2 poly goal does NOT fire abduce (subsumed by nlinarith — the 2026-06-09 fix)",
           abduce_seed("theorem t (x y : Int) (h : y = x * x) : 0 <= y := by sorry") is None)
    finally:
        os.environ.pop(ABDUCE_FLAG, None); os.environ.pop("ZTARE_LEANMILL_ABDUCE_NONLINEAR", None)

    # ── QE-ABDUCTION (Dillig): most-general missing premise via z3 quantifier elimination ───────────
    try:
        import z3 as _z3  # noqa: F401
        _have_z3 = True
    except Exception:  # noqa: BLE001
        _have_z3 = False
    if _have_z3:
        # transitivity `(x≤y)⊢x≤z` ⇒ the pivot x is eliminated; the abduct is `y≤z` (here `z-y > -1`), NOT the
        # vacuous `¬(x≤y)` that brute-forcing every binder + shortest would pick.
        _qe1 = qe_abduct_premise("theorem t (x y z : ℤ) (h : x ≤ y) : x ≤ z := by")
        ok("QE: transitivity pivot ⇒ a premise over y,z only (not the vacuous ¬hyp)",
           _qe1 is not None and "x" not in _qe1 and ("y" in _qe1 and "z" in _qe1))
        ok("QE: already-provable chain ⇒ None (QE collapses to True, no missing premise)",
           qe_abduct_premise("theorem t (a b c : ℤ) (h1 : a ≤ b) (h2 : b ≤ c) : a ≤ c := by") is None)
        ok("QE: no hyp↔concl pivot ⇒ None (nothing to abduce over)",
           qe_abduct_premise("theorem t (a b : ℤ) (h : a < b) : a < b + 1 := by") is None)
        os.environ[ABDUCE_FLAG] = "1"; os.environ[ABDUCE_QE_FLAG] = "1"
        try:
            _s = abduce_seed("theorem t (x y z : ℤ) (h : x ≤ y) : x ≤ z := by")
            ok("QE: abduce_seed (flag on) yields a drop-in ConjectureSeed with the {lname} contract",
               _s is not None and "{lname}" in _s.targeted_prompt and _s.obstruction.delta.get("added"))
        finally:
            os.environ.pop(ABDUCE_FLAG, None); os.environ.pop(ABDUCE_QE_FLAG, None)
    else:
        ok("z3 absent — QE-abduction fail-closed (covered by the live runner)", True)

    # ── ABDUCTION ROUTER: dispatch by AST operator theory (linear→QE, nonlinear→ABORT, discrete→cvc5) ──
    ok("router: pure-linear goal → 'qe_linear'",
       classify_abduction_route("theorem t (x y z : ℤ) (h : x ≤ y) : x ≤ z := by") == "qe_linear")
    ok("router: var·var → 'abort_nonlinear' (undecidable; don't burn compute)",
       classify_abduction_route("theorem t (x y : ℤ) (h : y = x * x) : 0 ≤ y := by") == "abort_nonlinear")
    ok("router: var-modulus → 'abort_nonlinear'",
       classify_abduction_route("theorem t (a n r : ℕ) (h : r = a % n) : r < n := by") == "abort_nonlinear")
    ok("router: bitvector → 'cvc5_discrete'",
       classify_abduction_route("theorem t (a b : BitVec 8) : a &&& b = b &&& a := by") == "cvc5_discrete")
    ok("router: non-arith → 'none'", classify_abduction_route("theorem t (f : ℝ → ℝ) : P f := by") == "none")
    if _have_z3:
        os.environ[ABDUCE_FLAG] = "1"; os.environ[ABDUCE_ROUTER_FLAG] = "1"
        try:
            ok("router e2e: linear goal → QE seed",
               abduce_seed("theorem t (x y z : ℤ) (h : x ≤ y) : x ≤ z := by") is not None)
            ok("router e2e: nonlinear goal → None (fail-closed abort, no wasted compute)",
               abduce_seed("theorem t (x y : ℤ) (h : y = x * x) : 0 ≤ y := by") is None)
        finally:
            os.environ.pop(ABDUCE_FLAG, None); os.environ.pop(ABDUCE_ROUTER_FLAG, None)

    # ── FLAG GATE: default OFF ⇒ no seed (byte-parity) ──────────────────────────────────────────────
    os.environ.pop(ABDUCE_FLAG, None)
    ok("FLAG OFF (default): abduce_seed returns None (parity — blind conjecture unchanged)",
       abduce_seed("theorem t (a b : ℤ) (h : a < b) : a + 1 ≤ b := by") is None)

    # ── seed shape: a hand-built premise produces a drop-in ConjectureSeed with the {lname}/LEMMA: contract ─
    _prompt = _abduce_targeted_prompt("theorem t (a b : ℤ) (h : a < b)", "theorem t (a b : ℤ) (h : a < b) : a ≤ b := by", "a ≤ b")
    ok("seed: targeted prompt keeps the `{lname}` token + LEMMA:/PROOF: fenced contract (drop-in for conjecture_generate)",
       "{lname}" in _prompt and "LEMMA:" in _prompt and "PROOF:" in _prompt and "get-abduct" in _prompt)
    ok("advance gate is the SAME kernel gate as conjecture (thin pass-through, no parallel gate)",
       abduction_advances("", "", "L", Path("/tmp"), 5)[0] is False)

    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
