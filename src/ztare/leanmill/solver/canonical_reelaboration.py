"""Canonical RE-ELABORATION gate — the airtight general guard against the context-semantic-hijack class
(2026-06-06; the FALSIFY false-statement control's instance-shadowing was the first instance).

The instance-shadowing leg in `statement_integrity` is a fast LEXICAL catch for ADDED core-class
instances. This is the EXOGENOUS backstop for the WHOLE class (instances + `notation`/`macro`/`set_option`
elaboration manipulation): strip the agent's ADDED context-elaboration commands from the probe — but KEEP
legitimate scaffolding (`open`s, helper lemmas/defs the proof cites) — then RECOMPILE. If the target
theorem no longer closes sorry-free in the stripped (canonical) context, the proof DEPENDED on a
context manipulation to make a verbatim statement true ⇒ laundering. Precision: a HARMLESS added instance
(not used) survives stripping → not flagged (no false positive); a legit `open Finset` is KEPT → no false
positive. Only the proof that NEEDED the hijack is caught. Deterministic (GP-248: no learned gate); the
recompile is exogenous (the kernel decides). Returns (ok, detail) — ok=False ⇒ blocked.
"""
from __future__ import annotations

import re
from pathlib import Path

# Top-level COMMANDS that manipulate elaboration (can hijack what a verbatim statement MEANS). `open` is
# deliberately NOT here — it is common + legit scaffolding (stripping it false-positives on real proofs).
_HIJACK_CMD = re.compile(
    r"^\s*(?:local\s+|scoped\s+)?(?:notation|macro|macro_rules|elab|syntax|set_option|infixl|infixr|infix|prefix|postfix)\b")
# ADDED decl keywords that can hijack meaning (2026-06-06 re-mine): an `axiom` is an unproven assumption
# (never a legit proof helper); an `abbrev`/`def`/`opaque` SHADOWING a name the statement uses redirects it.
_ADDED_DECL_KW = re.compile(
    r"^\s*(?:@\[[^\]]*\]\s*)?(?:private\s+|protected\s+|noncomputable\s+|scoped\s+|local\s+|partial\s+|unsafe\s+)*"
    r"(abbrev|def|opaque|axiom)\b")


def _strip_hijack_context(probe_source: str, original_source: str,
                          target_sig_tokens: "frozenset[str]" = frozenset()) -> "tuple[str, list[str]]":
    """Return (stripped_source, removed) — the probe with ADDED hijack context removed (instances of a
    hijack class, elaboration commands, added `axiom`s, and `abbrev`/`def`/`opaque` SHADOWING a name in the
    target's signature) but opens / legit lemmas / non-shadowing defs / the target KEPT."""
    from ztare.leanmill.solver.statement_integrity import (
        decl_blocks, _signature, _INSTANCE_HEAD, _CORE_CLASS)
    orig_names = {n for n, _ in decl_blocks(original_source)}
    # ALSO treat the REGISTERED campaign substrate's decls as ORIGINAL (2026-07-05): the CITED-rung governance
    # passes a row/probe source as `original_source` that OMITS substrate defs resolved via the warm env, so a
    # legitimate substrate instance (`instDecidableMarketable`) looked 'added' → got stripped → the stripped probe
    # couldn't resolve `Decidable (Marketable …)` → FALSE context_hijack, run after run. A decl the SUBSTRATE
    # declares is NEVER a hijack. Sound: a same-named MALICIOUS shadow clashes at substrate-append bank ⇒
    # reverted_noncompile (no laundering); a genuinely-ADDED (not-in-substrate) hijack is still stripped + caught.
    try:
        from ztare.formal.repl_compile import get_campaign_substrate
        _subp = get_campaign_substrate()
        if _subp:
            orig_names |= {n for n, _ in decl_blocks(Path(_subp).read_text(encoding="utf-8", errors="replace"))}
    except Exception:  # noqa: BLE001 — substrate union is best-effort; original_source membership still holds
        pass
    _orig_short = {n.split(".")[-1] for n in orig_names}
    drop_blocks: list[str] = []
    removed: list[str] = []
    for name, block in decl_blocks(probe_source):
        # NAME-ROBUST substrate-membership (2026-07-05): a decl the SUBSTRATE also declares is NOT "added" — never
        # strip it, whether the probe names it QUALIFIED (`NS.foo`) or SHORT (`foo`). The exact-only match false-
        # stripped the substrate's OWN `LimitOrderBookV3.instDecidableMarketable` (declared short inside the ns) →
        # the stripped probe couldn't resolve `Decidable (Marketable …)` → FALSE `context_hijack`. NO laundering: a
        # same-named MALICIOUS shadow cannot PERSIST (it clashes at substrate-append bank ⇒ reverted_noncompile),
        # and a genuinely-ADDED (different-named) hijack is still stripped + caught. Mirrors the name-agnostic
        # matching statement_integrity / faithfulness already use (the recurring qualified-vs-short brittleness).
        _sn = name.split(".")[-1]
        if name in orig_names or _sn in _orig_short or any(name.endswith("." + o) for o in orig_names):
            continue
        _short = name.split(".")[-1]
        # 1a. ADDED instance providing a (widened) core class — the shadowing vector.
        if _INSTANCE_HEAD.match(block) and _CORE_CLASS.search(_signature(block)):
            drop_blocks.append(block)
            removed.append(f"instance:{name}")
            continue
        # 1b. ADDED axiom (unconditional — an unproven assumption) / abbrev|def|opaque SHADOWING a name the
        #     target statement uses (name-collision with a target-signature identifier token).
        _km = _ADDED_DECL_KW.match(block)
        if _km:
            _kw = _km.group(1)
            if _kw == "axiom":
                drop_blocks.append(block)
                removed.append(f"axiom:{name}")
            elif _kw in ("abbrev", "def", "opaque") and _short in target_sig_tokens:
                drop_blocks.append(block)
                removed.append(f"shadow_{_kw}:{name}")
    stripped = probe_source
    for b in drop_blocks:
        stripped = stripped.replace(b, "", 1)
    # 2. command-level: drop elaboration-manipulating commands (notation/macro/set_option/…) NOT in original.
    orig_cmds = {ln.strip() for ln in original_source.splitlines() if _HIJACK_CMD.match(ln)}
    kept_lines: list[str] = []
    for ln in stripped.splitlines():
        if _HIJACK_CMD.match(ln) and ln.strip() not in orig_cmds:
            removed.append(f"cmd:{ln.strip()[:60]}")
            continue
        kept_lines.append(ln)
    return "\n".join(kept_lines), removed


def check(original_source: str, probe_source: str, target_name: str, lean_root: "Path",
          timeout_s: int = 120) -> "tuple[bool, str]":
    """The gate. (ok, detail). ok=True (genuine) iff: nothing hijack-class was stripped (fast pass), OR the
    target still COMPILES sorry-free in the stripped context. ok=False ⇒ the proof needed the stripped
    context-manipulation (laundering). Fail-OPEN on a compile-infra error (never block on tooling)."""
    # target-signature identifier tokens (names the statement USES) — to detect abbrev/def SHADOWING.
    from ztare.leanmill.solver.statement_integrity import decl_blocks, _signature as _si_sig
    _pd = dict(decl_blocks(probe_source))
    _tblk = _pd.get(target_name) or next((_pd[n] for n in _pd if n == target_name or n.endswith("." + target_name)), "")
    _toks = frozenset(re.findall(r"[A-Za-z_][\w']*", _si_sig(_tblk))) if _tblk else frozenset()
    stripped, removed = _strip_hijack_context(probe_source, original_source, _toks)
    if not removed:
        return True, "no added instance/notation/macro/set_option/axiom/shadow-decl to strip (nothing to re-elaborate)"
    # ENV-VS-SELF-CONTAINED CLASS (2026-06-25): this recompile goes through the ONE compile door `_compile_probe`,
    # which is CAMPAIGN-ENV-AWARE (warm path: it compiles against `campaign_file_env` when a substrate is
    # registered), so an env-based probe that references the substrate's defs WITHOUT re-inlining them still
    # resolves — no FALSE `context_hijack`. This held silently HOSTAGE to the substrate compiling: when the
    # registered substrate had errors, `campaign_file_env` returned None and `_compile_probe` fell back to a
    # Mathlib-only world, making EVERY recompile organ env-blind at once. The substrate run-start positive control
    # (autoformalize_notes) + loud `campaign_file_env` keep that door honest. The ONLY governance organ that can't
    # ride this compile door is the pure-TEXT `statement_integrity`, which got its own env-awareness primitive.
    from ztare.gates.v33_preflight_risk_detector import _compile_probe
    src = stripped if stripped.lstrip().startswith("import") else ("import Mathlib\n\n" + stripped)
    res = _compile_probe(src, lean_root, "CanonicalReelab", timeout_s)
    if res is True:
        return True, f"genuine: target still closes after stripping {removed} (proof did not depend on them)"
    if res is False:
        return False, (f"context-hijack: target FAILS to compile once {removed} are stripped — the proof "
                       "DEPENDED on added context-elaboration to make the verbatim statement provable")
    return True, f"fail-open (compile infra error, not a real negative); stripped={removed}"


def _selftest() -> int:
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    orig = "import Mathlib\n\ntheorem t : ∀ n : ℕ, n = n + 1 := by\n  sorry\n"
    # instance-shadowing probe → the HAdd instance is stripped (offline strip-logic check; recompile = lake).
    probe = ("import Mathlib\n\nlocal instance {α : Type u} : HAdd α Nat α where\n  hAdd a _ := a\n\n"
             "theorem t : ∀ n : ℕ, n = n + 1 := by\n  intro n\n  rfl\n")
    stripped, removed = _strip_hijack_context(probe, orig)
    ok("strips the added core-class instance", any(r.startswith("instance:") for r in removed)
       and "hAdd a _ := a" not in stripped)
    # notation hijack → the notation command is stripped.
    pnot = ("import Mathlib\n\nlocal notation:65 a \" + \" b => a\n\ntheorem t : ∀ n : ℕ, n = n + 1 := by\n"
            "  intro n\n  rfl\n")
    _, rem2 = _strip_hijack_context(pnot, orig)
    ok("strips an added notation command", any(r.startswith("cmd:") for r in rem2))
    # set_option hijack stripped.
    popt = "import Mathlib\n\nset_option autoImplicit true\n\ntheorem t : True := by trivial\n"
    _, rem3 = _strip_hijack_context(popt, "import Mathlib\n\ntheorem t : True := by sorry\n")
    ok("strips an added set_option", any("set_option" in r for r in rem3))
    # NO FALSE POSITIVE: a legit `open` + helper lemma are KEPT (not stripped).
    pok = ("import Mathlib\n\nopen Finset\n\nlemma helper : True := trivial\n\ntheorem t : True := by\n  exact helper\n")
    skept, rem4 = _strip_hijack_context(pok, "import Mathlib\n\ntheorem t : True := by sorry\n")
    ok("keeps legit open + helper lemma (no false strip)", "open Finset" in skept and "helper" in skept and not rem4)
    # 2026-06-06 re-mine siblings: abbrev shadowing a target-sig name + an added axiom are stripped.
    pabbrev = "import Mathlib\n\nabbrev Prime := fun _ : Nat => True\n\ntheorem t : Prime 4 := by\n  trivial\n"
    _, ra = _strip_hijack_context(pabbrev, "import Mathlib\n\ntheorem t : Prime 4 := by\n  sorry\n",
                                  frozenset({"Prime", "t"}))
    ok("strips abbrev shadowing a target-signature name", any(r.startswith("shadow_abbrev:") for r in ra))
    paxiom = "import Mathlib\n\naxiom cheat : ∀ n:ℕ, n = n+1\n\ntheorem t : ∀ n:ℕ, n=n+1 := fun n => cheat n\n"
    _, rx = _strip_hijack_context(paxiom, "import Mathlib\n\ntheorem t : ∀ n:ℕ, n=n+1 := by\n  sorry\n")
    ok("strips an added axiom (unproven assumption)", any(r.startswith("axiom:") for r in rx))
    # a NON-shadowing added def (name not in the target signature) is KEPT (no false strip).
    pdef = "import Mathlib\n\ndef myHelper : Nat := 0\n\ntheorem t : True := by\n  trivial\n"
    _, rk = _strip_hijack_context(pdef, "import Mathlib\n\ntheorem t : True := by\n  sorry\n", frozenset({"True", "t"}))
    ok("keeps a non-shadowing helper def", not any("myHelper" in r for r in rk))
    # nothing-to-strip ⇒ fast genuine pass (no recompile).
    okc, _d = check("import Mathlib\n\ntheorem t : True := by sorry\n",
                    "import Mathlib\n\ntheorem t : True := by trivial\n", "t", Path("/tmp"), 5)
    ok("clean probe ⇒ fast genuine pass (no recompile)", okc is True)
    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
