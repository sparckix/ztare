"""Kernel-backed STRUCTURAL queries — the elaborator is ground truth, regex is not (2026-06-13).

WHY THIS MODULE EXISTS (the operator's "fix once and for all"): the harness kept deciding consequential
things about Lean source — *is this decl still OPEN?* (→ it is a work item) — with a lexical
`"sorry" in text` grep. Lean's grammar is **not regular** (nested comments, `:=` in binders, unicode,
string literals), so a regex/substring is a strictly-weaker PROXY that a comment / string / identifier
fools — that is the costly 2026-06-13 work-item bug (a section-comment `sorry` queued an already-proven
lemma) and its whole class. Only the elaborator knows the truth, and we already run it.

THE INVARIANT (enforced across leanmill):
  • structural TRUTH (is it open? which axioms? does it compile?) → ask the KERNEL (here / repl_compile /
    lean_axiom_audit). A decl is OPEN iff `#print axioms` shows `sorryAx` — the SAME F1/F2 channel that
    gates every closure, so a work-item decision and a soundness decision use one source of truth.
  • unavoidable lexical bits (strip a comment to substring-scan an advisory hint) → the ONE canonical
    scanner `lean_source.strip_comments` / `blank_comments` (nested-aware), never an ad-hoc `re.sub`.
  • JUDGMENT (decompose? attack order? which move?) → the agent. Regex decides nothing consequential.

`sorried_names` is the kernel-truth primitive; callers use it KERNEL-FIRST and fall back to the now-
correct (nested-comment-aware) `lean_source.has_sorry` only when no live REPL/compiler exists here — so
the lexical check is a safety net, never load-bearing.

    python -m ztare.leanmill.solver.kernel_structure --selftest
"""
from __future__ import annotations

import re
from pathlib import Path

# Decode the STABLE `#print axioms` PRODUCER output — `'<name>' depends on axioms: [a, b]` /
# `'<name>' does not depend on any axioms`. Decoding a tool's own output is legitimate (it is not
# parsing Lean SOURCE); the format is producer-controlled and asserted in the selftest.
_AX_BLOCK = re.compile(r"'(?P<name>[^']+)' depends on axioms:\s*\[(?P<ax>[^\]]*)\]")
_AX_NONE = re.compile(r"'(?P<name>[^']+)' does not depend on any axioms")


def axioms_by_decl(output: str) -> "dict[str, set[str]]":
    """`{decl_name: {axiom, …}}` decoded from `#print axioms` output (a decl with none → empty set)."""
    out: "dict[str, set[str]]" = {}
    for m in _AX_NONE.finditer(output or ""):
        out[m.group("name")] = set()
    for m in _AX_BLOCK.finditer(output or ""):
        out[m.group("name")] = {a.strip() for a in m.group("ax").split(",") if a.strip()}
    return out


def _is_sorry_axiom(ax: str) -> bool:
    # `sorryAx` (possibly namespaced, e.g. `Lean.sorryAx` / `sorryAx`); compare the leaf.
    return ax.split(".")[-1] == "sorryAx"


def sorried_names(source: str, project: "str | Path", *, names: "list[str] | None" = None,
                  compile_fn=None) -> "set[str] | None":
    """KERNEL ground truth: the subset of `names` (default: every decl in `source`) whose proof
    elaborated to an open `sorry` — i.e. whose `#print axioms` transitively contains `sorryAx`. This
    cannot be fooled by a `sorry` in a comment/string/identifier (the elaborator never sees those as
    code). Returns `None` when no live matched compiler is available here ⇒ the caller MUST fall back
    to `lean_source.has_sorry` (now nested-comment-aware, so the fallback is also correct — just not
    load-bearing). Reuses `audit_external`'s proven pattern (decl_blocks → append `#print axioms` →
    decode); `compile_fn(src, project) -> {success, output}` is injectable for hermetic tests.

    Transitive note: a decl proven via a still-sorried helper is reported OPEN too — correct for a
    work-item decision (it is not a finished rung), and exactly what the lexical check MISSES."""
    from ztare.leanmill.solver.statement_integrity import decl_blocks
    decls = list(names) if names is not None else [n for n, _ in decl_blocks(source)]
    # 2026-06-13 bug-hunt: drop synthetic UNADDRESSABLE names (`<ns>.instance@<line>` for an anonymous
    # instance) — `#print axioms instance@1` is invalid Lean, so ONE such decl would fail the whole probe
    # and silently disable the kernel-truth path for EVERY named decl in the round (falling back to lexical
    # for all). Skipping them keeps the kernel check live for the addressable (named) API lemmas that matter.
    decls = [d for d in decls if "@" not in d]
    if not decls:
        return set()
    if compile_fn is None:
        from ztare.leanmill.audit_external import _default_compile as compile_fn
    probe = source + "\n" + "\n".join(f"#print axioms {d}" for d in decls)
    try:
        a = compile_fn(probe, str(project))
    except Exception:  # noqa: BLE001 — no usable compiler here → caller falls back to lexical
        return None
    if not isinstance(a, dict) or not a.get("success"):
        return None
    by_decl = axioms_by_decl(a.get("output") or "")
    if not by_decl:
        return None   # output carried no recognizable axiom markers → don't guess; fall back
    return {d for d in decls if any(_is_sorry_axiom(x) for x in by_decl.get(d, set()))}


def has_open_sorry(source: str, project: "str | Path", *, name: str, compile_fn=None) -> "bool | None":
    """Kernel-truth single-decl variant: True/False if the compiler ran, else None (fall back)."""
    s = sorried_names(source, project, names=[name], compile_fn=compile_fn)
    return None if s is None else (name in s)


def _selftest() -> int:
    fails: "list[str]" = []

    def ok(n, c):
        print(f"  [{'PASS' if c else 'FAIL'}] {n}")
        if not c:
            fails.append(n)

    # producer-output decode (asserts the format we depend on)
    abd = axioms_by_decl("'a' depends on axioms: [propext, sorryAx]\n'b' does not depend on any axioms")
    ok("decode: per-decl axioms", abd == {"a": {"propext", "sorryAx"}, "b": set()})

    SRC = ("import Mathlib\n"
           "theorem proved : 1 = 1 := by rfl\n"
           "theorem open_lemma : 2 = 2 := by sorry\n"
           "-- a comment mentioning sorry must NOT flip `proved`\n"
           "theorem commented : 3 = 3 := by rfl  -- sorry here is inert\n")

    def mock_compile(src, project):
        # emulate the elaborator: only `open_lemma` actually carries sorryAx; the comment is invisible
        if "#print axioms" not in src:
            return {"success": True, "output": ""}
        out = []
        for d in ("proved", "open_lemma", "commented"):
            if f"#print axioms {d}" in src:
                if d == "open_lemma":
                    out.append(f"'{d}' depends on axioms: [propext, sorryAx]")
                else:
                    out.append(f"'{d}' depends on axioms: [propext]")
        return {"success": True, "output": "\n".join(out)}

    s = sorried_names(SRC, "proj", compile_fn=mock_compile)
    ok("kernel truth: only the real sorry is OPEN (comment + inline-comment ignored)", s == {"open_lemma"})
    ok("commented decl NOT flagged (a lexical scan would false-positive on its inline `sorry`)",
       s is not None and "commented" not in s)
    ok("has_open_sorry single-decl", has_open_sorry(SRC, "p", name="open_lemma", compile_fn=mock_compile) is True
       and has_open_sorry(SRC, "p", name="proved", compile_fn=mock_compile) is False)

    # fail-to-fallback contract: compiler unavailable / unparseable ⇒ None (caller goes lexical)
    ok("compile fail ⇒ None (fall back)", sorried_names(SRC, "p", compile_fn=lambda s, p: {"success": False}) is None)
    ok("no markers ⇒ None (fall back)", sorried_names(SRC, "p", compile_fn=lambda s, p: {"success": True, "output": "?"}) is None)
    ok("compile raises ⇒ None (fall back)", sorried_names(SRC, "p", compile_fn=lambda s, p: (_ for _ in ()).throw(RuntimeError())) is None)

    print("kernel_structure selftest", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest() if "--selftest" in sys.argv else (print(__doc__) or 0))
