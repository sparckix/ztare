"""MOVE_REFLECTION generation + kernel-checked closure gate — the "reflection / proof-by-evaluation"
solver-core primitive for FINITE / DECIDABLE goals. Same shape + governance as
`ztare.leanmill.solver.conjecture` (read that first): `reflection_generate` = LLM generation,
`reflection_closes` = a KERNEL-checked gate via `ztare.gates.v33_preflight_risk_detector._compile_probe`
(sorry-OK typecheck primitive). The move is wired in `solver_core._build_dag_move_runner`'s move_runner
exactly like MOVE_GENERALIZE — it GENERATES, GATES through the kernel, calls `_record_attempt`, returns a
typed MoveResult. NEW self-contained module; it does NOT re-implement governance (no parallel frankenstein):
soundness is the SAME `_compile_probe` kernel the rest of the solver uses, plus the `#print axioms` allowlist
already canonical in `agentic_leaf.parse_verify_output`.

THE MOVE (the mathematician's "proof by reflection / evaluation"). For a goal `P x` that is FINITE /
DECIDABLE, instead of a hand proof we write a DECIDABLE Boolean PROGRAM `def check (…) : Bool := …` that
decides P, prove ONCE that the program is SOUND — `theorem check_sound (…) : check … = true → P …` — and
then close the node by `... (check_sound (by decide))`: the kernel REDUCES `check …` to `true` and the
soundness theorem transports that into a proof of `P …`. This is the canonical Lean idiom for "the goal is
a finite computation"; it is exactly what `decide`/`Decidable.decide` does under the hood, surfaced as a
reusable solver move so the leaf can attack `∀ n < N, …` / concrete-instance / enumerable-case goals by
EVALUATION rather than by tactic search.

SOUNDNESS (no false-closure surface — this is the whole point of the kernel gate):
  * The closing term is `check_sound (by decide : check … = true)`. For the node to close, BOTH
    `theorem check_sound : check … = true → P …` must kernel-typecheck SORRY-FREE *and* the `by decide`
    must reduce `check …` to `true` in the kernel. A `check` that does NOT actually decide P cannot have a
    sorry-free `check_sound`; a `decide` that does not reduce to `true` does not typecheck. So a wrong
    `check` is a MISS, never a laundered closure.
  * The node theorem the kernel ratifies is the ORIGINAL goal `P …` (we own its signature; the leaf
    supplies only `check`, the soundness proof, and the `decide`-invocation). `reflection_closes` returns a
    SINGLE self-contained block whose final theorem IS the goal — the caller routes it through the EXACT
    SAME governance as a direct move (`_verify_compile` + `_validate_against_contract` = kernel-compile
    receipt + matched-negative-control + statement_integrity), like MOVE_GENERALIZE. There is no separate
    closure path.

ANTI-LAUNDERING legs the gate adds on top of the kernel typecheck (each a MISS, never a false close):
  (a) the block is SORRY/admit-free (the soundness proof can't hide a `sorry`);
  (b) `check`'s body is NOT a TRIVIAL CONSTANT (`:= true` / `:= false` / a literal) — a constant `check`
      makes `check_sound` either vacuous (`false → P`, trivially true, proves nothing) or a disguised
      direct proof of `P` (`true → P` requires a real proof of P inside `check_sound`, so the EVALUATION
      did no work). Both are rejected: the move must close by COMPUTATION, not by smuggling the proof into
      `check_sound`.
  (c) AXIOM NOTE / `native_decide` ban. `decide` is KERNEL reduction and is axiom-clean (stays within
      `{propext, Classical.choice, Quot.sound}` = `agentic_leaf.AXIOM_ALLOWLIST`). `native_decide`
      compiles the decision procedure to native code and trusts its result via the `Lean.ofReduceBool`
      axiom, which is OUTSIDE that allowlist (the anti-laundering kernel / `#print axioms` audit BANS it).
      So this move PREFERS plain `decide`; `native_decide` is rejected UNLESS the explicit opt-in
      `ZTARE_LEANMILL_REFLECT_NATIVE_DECIDE=1` is set, and even then it is FLAGGED in the verdict so the
      downstream `#print axioms` gate (which sees `Lean.ofReduceBool`) blocks the closure on the kernel
      side — i.e. opt-in only relaxes THIS move's pre-filter, never the kernel allowlist.

FLAG: `ZTARE_LEANMILL_REFLECT` (default OFF ⇒ byte-parity; the move is never offered by `move_policy`
unless the flag is on — registered next to the other STRATEGIST_MOVES). STRICTLY for FINITE / DECIDABLE
goals: on a genuinely infinite / undecidable goal there is no sound `decide`, so the gate simply never
admits a closure (a MISS) — it cannot manufacture one.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

# Single source of truth for the kernel axiom allowlist (the same set the leaf's #print-axioms gate uses).
# `Lean.ofReduceBool` (the native_decide axiom) is DELIBERATELY absent ⇒ a native_decide closure is flagged.
from ztare.gates.lean_compile_primitives import AXIOM_ALLOWLIST

# The env opt-in for native_decide (default off). When unset/0 the gate REJECTS native_decide pre-kernel
# (saves a compile that the #print-axioms gate would reject anyway); when "1" it lets the block through to
# the kernel but FLAGS the ofReduceBool axiom so the downstream audit blocks it.
_NATIVE_DECIDE_ENV = "ZTARE_LEANMILL_REFLECT_NATIVE_DECIDE"
# The native_decide axiom — outside AXIOM_ALLOWLIST, so the anti-laundering kernel bans it.
NATIVE_DECIDE_AXIOM = "Lean.ofReduceBool"


_REFLECTION_PROMPT = (
    "You are a Lean 4 prover using PROOF BY REFLECTION / EVALUATION. The GOAL below is FINITE / DECIDABLE "
    "(a concrete instance, a bounded `∀ n < N`, an enumerable case split, a fixed numeric/finite-set fact). "
    "Do NOT prove it by hand. Instead:\n"
    "  1. Write an EFFICIENT, structurally-recursive Boolean PROGRAM `def {cname} {binders} : Bool := <body>` "
    "that DECIDES the goal's predicate by COMPUTATION. CRITICAL — the whole point of reflection is a Bool "
    "program the KERNEL reduces FASTER than the goal's auto-derived `Decidable` instance, so:\n"
    "     • USE a fold / `.all` / `.any` / `.filter` over `List.range N` (or an `Array`) with cheap `Nat` "
    "ops (`Nat.ble`, `==`, `%`, `&&`, `||`, binary arithmetic). This avoids the unary `Nat.decidableBallLT` / "
    "`Finset.decidableBAll` recursion that makes plain `decide` blow up.\n"
    "     • Do NOT write `def {cname} := decide (<the goal>)` or call `decide`/`Decidable` INSIDE the body — "
    "that just re-runs the SAME slow instance plain `decide` already uses and gains ZERO lift (it is rejected).\n"
    "     • The body MUST do real work — NOT the constant `true`/`false`.\n"
    "  2. Prove its SOUNDNESS: `theorem {sname} {binders} : {cname} {args} = true → <the goal's conclusion> "
    ":= by <proof>` — i.e. if the program returns `true`, the goal's predicate HOLDS. NO sorry.\n"
    "  3. Close the ORIGINAL goal by EVALUATION: apply the soundness theorem to a `by decide` proof that the "
    "program returns `true` on the goal's arguments.\n"
    "Use plain `by decide` (it is kernel-checked and axiom-clean); do NOT use `native_decide` (it adds the "
    "Lean.ofReduceBool axiom, which is BANNED here).\n"
    "Output EXACTLY three fenced blocks:\n"
    "CHECK:\n```lean\ndef {cname} {binders} : Bool := <decision procedure — NOT a constant>\n```\n"
    "SOUND:\n```lean\ntheorem {sname} {binders} : {cname} {args} = true → <goal conclusion> := by\n  <proof, NO sorry>\n```\n"
    "CLOSE:\n```lean\n<the proof body that goes after the goal's `:=` — e.g. `{sname} (by decide)` or "
    "`by exact {sname} (by decide)` — NO sorry, NO native_decide>\n```\n"
    "Self-contained against `import Mathlib` + the PREAMBLE. If the goal is NOT finite/decidable (no "
    "terminating decision procedure exists), output an EMPTY CHECK block (an honest non-attempt, NOT a sorry).\n"
    "{pre}GOAL to decide by reflection:\n{goal}\n"
)


def _name_base(row: dict, default: str) -> str:
    """A safe Lean identifier base derived from the target theorem name."""
    return re.sub(r"[^A-Za-z0-9_]", "", (row.get("target_theorem_name") or default))[:24] or default


def _goal_conclusion(goal_text: str) -> str:
    """The goal's conclusion (after the top-level `:`, before `:=`) — bracket-aware. '' if unparseable.
    Reuses the canonical conjecture parsers so we don't re-implement Lean signature splitting."""
    from ztare.leanmill.solver.conjecture import _lemma_conclusion
    return _lemma_conclusion(goal_text or "")


def reflection_generate(row: dict, goal_text: str, lean_root: Path, timeout_s: int,
                        preamble: str = "") -> "tuple[str, str, str, str, str]":
    """Ask the leaf for a reflection closure of a FINITE/DECIDABLE goal: a `def check`, its soundness
    theorem, and a `by decide`-based closing term. Returns
    `(check_block, sound_block, close_body, cname, raw_tail)`. ('', '', '', cname, err) on failure / a
    non-finite goal (⇒ no closure, never a false close). The three pieces are GATED + ASSEMBLED by
    `reflection_closes`; the statement the kernel ratifies is the ORIGINAL goal (we own it)."""
    base = _name_base(row, "tgt")
    cname = f"refl_check_{base}"
    sname = f"refl_sound_{base}"
    # the goal's binder telescope + the conclusion, so the prompt can shape `check`/`check_sound` to match
    from ztare.leanmill.solver.statement_integrity import _signature
    from ztare.leanmill.solver.conjecture import _top_level_colon
    from ztare.leanmill import lean_source as _ls
    sig = _signature((goal_text or "").strip())
    j = _top_level_colon(sig)
    binders = _ls.strip_decl_prefix(sig[:j]) if j >= 0 else ""
    # argument list to apply `check`/`check_sound` to: the bound variable names (best-effort).
    args = " ".join(re.findall(r"[(\{⦃]\s*([A-Za-z_][\w']*)", binders))
    pre = ("\nPREAMBLE:\n" + preamble.strip() + "\n") if preamble.strip() else ""
    prompt = _REFLECTION_PROMPT.format(cname=cname, sname=sname, binders=binders or "",
                                       args=args, goal=goal_text, pre=pre)
    try:
        from ztare.leanmill.solver.agentic_leaf import default_dispatch
        raw = default_dispatch(prompt, repo=lean_root, timeout=timeout_s) or ""
    except Exception as e:  # noqa: BLE001
        return "", "", "", cname, f"dispatch_error: {e!r}"

    from ztare.leanmill.solver.agent_output import fenced_block
    check_block, sound_block, close_body = (fenced_block(raw, "CHECK:"), fenced_block(raw, "SOUND:"),
                                            fenced_block(raw, "CLOSE:"))
    return check_block, sound_block, close_body, cname, (raw or "")[-200:]


def _check_is_trivial_constant(check_block: str, cname: str) -> bool:
    """True iff `def check … := <body>` has a TRIVIALLY-CONSTANT body — `true`/`false` or a bare Bool
    literal — i.e. the decision procedure does NO computation. Such a `check` either makes `check_sound`
    vacuous (`false → P`) or smuggles the real proof into `check_sound` (`true → P`), so reflection did no
    evaluation work. Bracket-aware split on the def's top-level `:=` (a `:=` inside binders is ignored)."""
    from ztare.leanmill.solver.statement_integrity import _signature
    if not (check_block or "").strip():
        return True
    # body = everything after the def's top-level `:=`
    sig = _signature(check_block.strip())
    body = check_block.strip()[len(sig):].lstrip()
    if body.startswith(":="):
        body = body[2:].strip()
    # strip a leading `by` + a leading `exact` (a tactic-built constant `by exact true` is still a
    # constant) and outer parens/comments. NOTE: this catches the SYNTACTIC constant only — a constant
    # that REDUCES from a non-literal expression is out of cheap reach; the kernel/soundness legs are the
    # backstop (a constant `check` forces `check_sound`'s `true → P` to carry a real proof of P, so the
    # evaluation does no work, but that case is the caller's MNC/governance concern, not this pre-filter).
    from ztare.leanmill.lean_source import strip_comments
    body_nc = strip_comments(body).strip()
    core = re.sub(r"^by\b", "", body_nc).strip().strip("()").strip()
    core = re.sub(r"^exact\b", "", core).strip().strip("()").strip()
    return core in ("true", "false", "True", "False", "Bool.true", "Bool.false", "")


def _check_delegates_to_decide(check_block: str, cname: str) -> bool:
    """True iff `def check … := <body>` DELEGATES to plain `decide` — i.e. the body is `decide <…>` /
    `decide (<…>)` (optionally `by decide`). This is the LIFT-KILLING strawman (workflow audit 2026-06-09):
    such a checker re-runs the SAME auto-derived `Decidable` instance plain `decide` already uses, so
    `check args = true` reduces with the IDENTICAL kernel blowup — reflection gains ZERO over the cascade.
    The whole point of reflection is a custom Bool program that reduces FASTER than the derived instance;
    a `decide`-delegating checker is reflection in name only. Rejected as a MISS (not a false-closure)."""
    from ztare.leanmill.solver.statement_integrity import _signature
    if not (check_block or "").strip():
        return False
    sig = _signature(check_block.strip())
    body = check_block.strip()[len(sig):].lstrip()
    if body.startswith(":="):
        body = body[2:].strip()
    from ztare.leanmill.lean_source import strip_comments
    body_nc = strip_comments(body).strip()
    core = re.sub(r"^by\b", "", body_nc).strip().strip("()").strip()
    core = re.sub(r"^exact\b", "", core).strip()
    return bool(re.match(r"^(?:decide|Decidable\.decide)\b", core))


def _uses_native_decide(*blocks: str) -> bool:
    """True iff any block invokes `native_decide` in real (comment-stripped) tactic/term text."""
    from ztare.leanmill.lean_source import strip_comments
    for b in blocks:
        if not b:
            continue
        nc = strip_comments(b)
        if re.search(r"(?<![\w'])native_decide(?![\w'])", nc):
            return True
    return False


def assemble_reflection_closure(check_block: str, sound_block: str, close_body: str,
                                goal_text: str, preamble: str = "") -> str:
    """PURE (no dispatch/compile ⇒ unit-testable) assembly of the self-contained reflection block:
    `[import] + [preamble] + def check + theorem check_sound + <goal signature> := <close_body>`. The
    FINAL theorem is the ORIGINAL goal (we own its signature; the leaf supplies only the RHS). Returns ''
    if any piece is missing or a piece carries sorry/admit (an honest non-closure — never an unsound
    partial). The downstream kernel gate (`reflection_closes`) decides whether it actually compiles."""
    if not (check_block.strip() and sound_block.strip() and close_body.strip() and (goal_text or "").strip()):
        return ""
    from ztare.leanmill.lean_source import has_sorry as _has_sorry   # comment-stripping (2026-06-13 audit)
    blob = check_block + "\n" + sound_block + "\n" + close_body
    if _has_sorry(blob):
        return ""
    # the goal's statement up to `:=` (we own it); replace the body with the close term
    from ztare.leanmill.solver.statement_integrity import _signature
    gsig = _signature((goal_text or "").strip()).rstrip()
    if not gsig:
        return ""
    goal_decl = f"{gsig} := {close_body.strip()}"
    _pre = (preamble.strip() + "\n\n") if preamble.strip() else ""
    snippet = _pre + check_block.strip() + "\n\n" + sound_block.strip() + "\n\n" + goal_decl
    if not snippet.lstrip().startswith("import"):
        snippet = "import Mathlib\n\n" + snippet
    # UNCAP HEARTBEATS (cold-agent advice, valid): the WHOLE point of reflection is brute KERNEL EVALUATION
    # (`by decide` on the Bool program). Lean's default `maxHeartbeats 200000` aborts a SOUND, TERMINATING
    # checker mid-reduction → a false-closed rejection (a real lift-killer for non-trivial computations). 0 =
    # unlimited; the SUBPROCESS wallclock (verify_timeout) is the real backstop, so this can't hang the run.
    # `set_option` MUST follow all imports — insert it after the leading consecutive import lines.
    _lines = snippet.split("\n")
    _i = 0
    while _i < len(_lines) and (_lines[_i].lstrip().startswith("import") or not _lines[_i].strip()):
        _i += 1
    _lines.insert(_i, "set_option maxHeartbeats 0\n")
    return "\n".join(_lines)


def reflection_closes(check_block: str, sound_block: str, close_body: str, cname: str,
                      goal_text: str, lean_root: Path, timeout_s: int,
                      preamble: str = "") -> "tuple[bool, str, dict]":
    """Kernel-gated CLOSURE test for a reflection attempt (the verified-closure gate). Closes iff:
      (a) all three pieces present + SORRY/admit-free (the soundness proof can't hide a `sorry`);
      (b) `check` is NOT a trivial constant (the EVALUATION did real work — not a disguised direct proof
          smuggled into `check_sound`, not a vacuous `false → P`);
      (c) `native_decide` is rejected unless `ZTARE_LEANMILL_REFLECT_NATIVE_DECIDE=1` (axiom-clean `decide`
          preferred; native_decide adds `Lean.ofReduceBool`, banned by the kernel allowlist — see (e));
      (d) the assembled block COMPILES sorry-free against preamble+Mathlib via `_compile_probe` (the
          soundness theorem typechecks AND the `by decide` reduces — so `P` genuinely follows by COMPUTATION);
      (e) the closure stays within the axiom allowlist `{propext, Classical.choice, Quot.sound}` — i.e. no
          `Lean.ofReduceBool`. A `decide` closure is axiom-clean; a (opted-in) native_decide closure is
          FLAGGED (`info['axiom_flag']`) so the downstream `#print axioms` governance blocks it.

    Returns `(closed, reason, info)`. NEVER a false closure: a wrong `check`/soundness/decide is a MISS
    (the kernel typecheck or `decide` reduction fails). `info` carries `block` (the assembled .lean),
    `trivial_check`, `native_decide`, `axiom_flag`. The caller still routes `info['block']` through the
    SAME `_verify_compile` + `_validate_against_contract` governance as any direct move (so MNC +
    statement_integrity + the #print-axioms audit run on the kernel side; this gate is the pre-filter)."""
    info: dict = {"trivial_check": None, "native_decide": False, "axiom_flag": None, "block": ""}
    if not (check_block.strip() and sound_block.strip() and close_body.strip()):
        return False, "missing CHECK/SOUND/CLOSE block (honest non-closure)", info
    from ztare.leanmill.lean_source import has_sorry as _has_sorry2   # comment-stripping (2026-06-13 audit)
    if _has_sorry2(check_block + "\n" + sound_block + "\n" + close_body):
        return False, "reflection block not sorry-free (soundness proof must not hide a sorry)", info
    # (b) anti-laundering: a constant `check` is a disguised direct proof / vacuous — reject.
    info["trivial_check"] = _check_is_trivial_constant(check_block, cname)
    if info["trivial_check"]:
        return False, ("`check` is a trivial constant (true/false) — reflection did no evaluation work "
                       "(disguised direct proof or vacuous `false → P`)"), info
    # (b2) anti-strawman (workflow 2026-06-09): reject a `check := decide (…)` body — it delegates to the
    # SAME auto-Decidable instance plain `decide` uses ⇒ reflection inherits the cascade's blowup, zero lift.
    info["delegates_decide"] = _check_delegates_to_decide(check_block, cname)
    if info["delegates_decide"]:
        return False, ("`check` delegates to plain `decide` (body is `decide …`) — reflection-in-name-only; "
                       "it re-runs the slow derived Decidable instance and gains no lift over the cascade. "
                       "Write an EFFICIENT Bool fold/all over List.range instead"), info
    # (c) native_decide gate: default REJECT (axiom-unclean); explicit opt-in lets it through to the kernel
    # but it WILL be flagged + blocked by the axiom allowlist (e).
    info["native_decide"] = _uses_native_decide(sound_block, close_body, check_block)
    _native_optin = os.environ.get(_NATIVE_DECIDE_ENV) == "1"
    if info["native_decide"] and not _native_optin:
        return False, (f"uses native_decide (adds the banned {NATIVE_DECIDE_AXIOM} axiom); prefer plain "
                       f"`decide`, or set {_NATIVE_DECIDE_ENV}=1 to opt in (still axiom-flagged + blocked)"), info
    # (d) assemble OUR-signature block + kernel-compile (sorry-OK probe; the block is itself sorry-free).
    block = assemble_reflection_closure(check_block, sound_block, close_body, goal_text, preamble)
    if not block:
        return False, "could not assemble the reflection block (missing piece / unparseable goal signature)", info
    info["block"] = block
    from ztare.gates.v33_preflight_risk_detector import _compile_probe
    ok = _compile_probe(block, lean_root, "ReflectClose", timeout_s)
    if ok is None:
        return False, "kernel compile INADMISSIBLE (lake sandbox missing / timeout) — not a real closure", info
    if ok is not True:
        return False, "reflection block does NOT compile (soundness theorem or `by decide` failed — a MISS)", info
    # (e) AXIOM NOTE: surface whether the closure is axiom-clean. A native_decide closure (only reachable
    # via the opt-in above) carries Lean.ofReduceBool ∉ AXIOM_ALLOWLIST ⇒ flag it so the downstream
    # #print-axioms governance blocks it; a plain-`decide` closure is clean.
    if info["native_decide"]:
        info["axiom_flag"] = (f"{NATIVE_DECIDE_AXIOM} (native_decide) ∉ allowlist "
                              f"{sorted(AXIOM_ALLOWLIST)} — downstream #print-axioms gate will block")
        return True, ("compiled — goal closes by reflection, but via native_decide (AXIOM-FLAGGED: "
                      f"{NATIVE_DECIDE_AXIOM}); the #print-axioms governance blocks it"), info
    return True, "compiled — goal closes by reflection (decide), axiom-clean (no Lean.ofReduceBool)", info


def reflection_solve(row: dict, goal_text: str, lean_root: Path, timeout_s: int,
                     preamble: str = "") -> "tuple[str, str, str, dict]":
    """One-call wrapper used by the move_runner: GENERATE then GATE. Returns
    `(close_body, helper_preamble, reason, info)`, integration-shaped for the SAME governance as a direct
    move (like MOVE_GENERALIZE/MOVE_TACTIC_STEP route through `_verify_compile` + `_validate_against_contract`):

      * `close_body` is the proof body that goes after the goal's `:=` (e.g. `refl_sound (by decide)` or a
        `by exact …` block) — what the runner passes as `proof_text` so the kernel ratifies the ORIGINAL goal;
      * `helper_preamble` is the invented `def check` + `theorem check_sound`, to be PREPENDED to the source
        preamble (`_preamble_from_source(r)`) so the goal body can cite them — the SAME invented-helper
        threading the warm/cold path already uses (helpers in the prelude, the target body cites them).

    Both are '' unless the pre-filter kernel gate passed AND the closure is axiom-CLEAN (a flagged
    native_decide closure compiles but the downstream `#print axioms` gate would reject it ⇒ fail-closed:
    do NOT present it as a closure). `info` carries the gate diagnostics (trivial_check / native_decide /
    axiom_flag / block / tail). The runner still RE-VERIFIES through `_verify_compile` + `_govern`
    (MNC + statement_integrity + the #print-axioms audit) — this gate is the pre-filter, the contract is
    the ratifier (no separate closure path, no false-closure surface)."""
    cb, sb, close, cname, tail = reflection_generate(row, goal_text, lean_root, timeout_s, preamble=preamble)
    closed, reason, info = reflection_closes(cb, sb, close, cname, goal_text, lean_root, timeout_s, preamble=preamble)
    info["tail"] = tail
    if closed and not info.get("axiom_flag"):
        helper_preamble = cb.strip() + "\n\n" + sb.strip()
        return close.strip(), helper_preamble, reason, info
    return "", "", reason, info


def _selftest() -> int:
    """Deterministic (NO compile) checks of the PURE legs — parse/assembly/trivial-constant/native_decide/
    axiom-flag — with POSITIVE and NEGATIVE controls. The compile-dependent legs (the kernel `_compile_probe`
    typecheck + the `by decide` reduction) need the live lake box, like conjecture.py's specialize/falsify
    legs; they are exercised by the lake calibration script, not here."""
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    # ── (b) trivial-constant detector: POSITIVE (real check admitted) + NEGATIVE (constant rejected) ──
    ok("trivial-check: `:= true` constant FLAGGED (no work) [neg control]",
       _check_is_trivial_constant("def refl_check_t (n : ℕ) : Bool := true", "refl_check_t") is True)
    ok("trivial-check: `:= false` constant FLAGGED [neg control]",
       _check_is_trivial_constant("def c : Bool := false", "c") is True)
    ok("trivial-check: empty body FLAGGED",
       _check_is_trivial_constant("", "c") is True)
    ok("trivial-check: real decision procedure ADMITTED [pos control]",
       _check_is_trivial_constant("def refl_check_t (n : ℕ) : Bool := decide (n < 10)", "refl_check_t") is False)
    ok("trivial-check: enumerating body ADMITTED [pos control]",
       _check_is_trivial_constant("def c (n : ℕ) : Bool := (List.range 100).all (fun k => k * k ≥ k)", "c") is False)
    ok("trivial-check: `:= by decide`-built constant still a constant (FLAGGED)",
       _check_is_trivial_constant("def c : Bool := by exact true", "c") is True)

    # ── (c) native_decide detector: POS (plain decide clean) + NEG (native_decide caught) ──
    ok("native_decide: caught in SOUND block [neg control]",
       _uses_native_decide("theorem s : c = true → P := by native_decide", "x") is True)
    ok("native_decide: caught in CLOSE body [neg control]",
       _uses_native_decide("", "by native_decide") is True)
    ok("native_decide: plain `decide` is NOT flagged [pos control]",
       _uses_native_decide("theorem s : c = true → P := by decide", "refl_sound (by decide)") is False)
    ok("native_decide: comment mentioning native_decide is NOT flagged (comment-stripped)",
       _uses_native_decide("-- avoid native_decide here\nby decide") is False)

    # ── (a)+assembly: PURE assembler — POSITIVE (assembles) + NEGATIVE (sorry / missing piece → '') ──
    _goal = "theorem t (n : ℕ) (h : n < 5) : n * n < 25 := by"
    # EFFICIENT Bool fold (NOT `decide (...)` — that delegates to the slow derived instance, the strawman the
    # 2026-06-09 audit flagged + the gate now rejects). A bounded `.all` over `List.range` with `Nat.blt`.
    _cb = "def refl_check_t (n : ℕ) : Bool := (List.range 5).all (fun k => Nat.blt (k * k) 25)"
    _sb = "theorem refl_sound_t (n : ℕ) : refl_check_t n = true → (n < 5 → n * n < 25) := by\n  simp [refl_check_t]"
    _close = "fun h => (refl_sound_t n (by decide)) h"
    _block = assemble_reflection_closure(_cb, _sb, _close, _goal)
    ok("assemble: final theorem is the OWNED goal signature [pos control]",
       "theorem t (n : ℕ) (h : n < 5) : n * n < 25 :=" in _block)
    ok("assemble: includes the def check + soundness theorem [pos control]",
       "def refl_check_t" in _block and "theorem refl_sound_t" in _block)
    ok("assemble: leaf NEVER writes the goal signature (we own it; close body is its only RHS contribution)",
       _block.rstrip().endswith("fun h => (refl_sound_t n (by decide)) h"))
    ok("assemble: adds `import Mathlib` when no preamble starts with import",
       _block.lstrip().startswith("import Mathlib"))
    ok("assemble: sorry in any piece → '' (never an unsound partial) [neg control]",
       assemble_reflection_closure(_cb, _sb + "\n  sorry", _close, _goal) == "")
    ok("assemble: missing CHECK block → '' [neg control]",
       assemble_reflection_closure("", _sb, _close, _goal) == "")
    ok("assemble: missing goal text → '' [neg control]",
       assemble_reflection_closure(_cb, _sb, _close, "") == "")

    # ── reflection_closes PURE-leg rejections (the kernel-compile leg needs the live box) ──
    # NEGATIVE controls: each laundered/bad input must be a MISS without a compile.
    ok("closes: missing block → reject (honest non-closure) [neg control]",
       reflection_closes("", _sb, _close, "refl_check_t", _goal, Path("/tmp"), 5)[0] is False)
    ok("closes: sorry in soundness → reject [neg control]",
       reflection_closes(_cb, _sb + "\n  sorry", _close, "refl_check_t", _goal, Path("/tmp"), 5)[0] is False)
    ok("closes: trivial constant check → reject (no evaluation work) [neg control]",
       reflection_closes("def refl_check_t (n : ℕ) : Bool := true", _sb, _close, "refl_check_t",
                         _goal, Path("/tmp"), 5)[0] is False)
    # (b2) decide-delegation detector (anti-strawman): a `:= decide (…)` checker is reflection-in-name-only
    ok("delegates-decide: `:= decide (…)` body FLAGGED [pos control]",
       _check_delegates_to_decide("def refl_check_t (n : ℕ) : Bool := decide (n < 5 → n*n < 25)", "refl_check_t") is True)
    ok("delegates-decide: efficient `.all`/`Nat.blt` fold NOT flagged [neg control]",
       _check_delegates_to_decide(_cb, "refl_check_t") is False)
    ok("closes: decide-delegating check → reject (no lift over cascade) [neg control]",
       reflection_closes("def refl_check_t (n : ℕ) : Bool := decide (n < 5 → n*n < 25)", _sb, _close,
                         "refl_check_t", _goal, Path("/tmp"), 5)[0] is False)
    # native_decide default-OFF: rejected pre-kernel; with opt-in it gets PAST the pre-filter but the
    # /tmp sandbox makes _compile_probe return None ⇒ still not a closure (INADMISSIBLE, fail-closed).
    _saved = os.environ.get(_NATIVE_DECIDE_ENV)
    try:
        os.environ.pop(_NATIVE_DECIDE_ENV, None)
        _r_nd = reflection_closes(_cb, "theorem refl_sound_t (n:ℕ) : refl_check_t n = true → True := by trivial",
                                  "by native_decide", "refl_check_t", _goal, Path("/tmp"), 5)
        ok("closes: native_decide WITHOUT opt-in → reject (axiom-unclean) [neg control]",
           _r_nd[0] is False and "native_decide" in _r_nd[1])
        os.environ[_NATIVE_DECIDE_ENV] = "1"
        _r_nd2 = reflection_closes(_cb, "theorem refl_sound_t (n:ℕ) : refl_check_t n = true → True := by trivial",
                                   "by native_decide", "refl_check_t", _goal, Path("/tmp"), 5)
        # passes the native_decide pre-filter (opt-in) but the /tmp sandbox has no Mathlib ⇒ _compile_probe
        # returns False/None ⇒ NOT closed. The load-bearing invariant: opt-in only relaxes THIS pre-filter,
        # the KERNEL still has to admit it — so no live box ⇒ no false close (fail-closed). The native_decide
        # flag is recorded regardless (so the downstream #print-axioms gate sees ofReduceBool).
        ok("closes: native_decide WITH opt-in → past pre-filter, but no live box ⇒ NOT closed (fail-closed)",
           _r_nd2[0] is False and _r_nd2[2]["native_decide"] is True)
    finally:
        if _saved is None:
            os.environ.pop(_NATIVE_DECIDE_ENV, None)
        else:
            os.environ[_NATIVE_DECIDE_ENV] = _saved

    # AXIOM allowlist sanity: the native_decide axiom is NOT in the allowlist (so it WOULD be flagged/banned).
    ok("axiom: Lean.ofReduceBool ∉ AXIOM_ALLOWLIST (native_decide is banned by the kernel)",
       NATIVE_DECIDE_AXIOM not in AXIOM_ALLOWLIST and AXIOM_ALLOWLIST == frozenset(
           {"propext", "Classical.choice", "Quot.sound"}))

    # goal-conclusion parse (reuses the canonical conjecture parser) — POSITIVE.
    ok("goal-conclusion: parsed from the goal signature",
       _goal_conclusion("theorem t (n : ℕ) (h : n < 5) : n * n < 25 := by") == "n * n < 25")

    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
