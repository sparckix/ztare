"""leanmill — the SINGLE canonical home for parsing structure out of a `.lean` source.

Why this exists: every leanmill component used to roll its own regex to pull a goal / signature / proof
out of Lean text, and they diverged. The divergence is what let native_hammer, cold_shot, and
external_frontier ship malformed probes (a `:=` inside a hypothesis truncated the extracted goal; the
goal was never wrapped into a theorem), so those moves were silently dead for months.

RULE: no leanmill module may regex Lean structure on its own — Lean's grammar is NOT regular (nested
`/- /- -/ -/`, `:=` in binders, unicode, string literals), so an ad-hoc `re.sub`/`split` is a strictly-
weaker proxy that a comment/string/identifier fools. Use these primitives. They take the REAL source
text (never reconstruct a statement) and carry positive/negative controls. The canonical answers:
  • strip a comment to substring-scan a hint  → `strip_comments` (remove) / `blank_comments` (offset-
                                                 preserving), both off the ONE `_comment_mask` scan.
  • cut a decl at its proof `:=`              → `split_at_proof` / `signature_before_proof` (binder-safe,
                                                 NOT `text.split(":=")` which truncates a `let k := 5` hyp).
  • IS A DECL OPEN? / which axioms?           → ask the KERNEL, not text: `solver/kernel_structure.py`
                                                 (`#print axioms` → `sorryAx`) / REPL `sorries`. The
                                                 elaborator cannot be fooled; the lexical `has_sorry` is
                                                 only the fallback when no live REPL exists.
  • a strategy/order/decompose JUDGMENT       → the AGENT, never a lexical pattern (Goldilocks).
    python -m ztare.leanmill.lean_source --selftest
"""
from __future__ import annotations
import re

_DECL_PREFIX = r"(?:noncomputable\s+|private\s+|protected\s+)*(?:theorem|lemma)\s+"

# Any top-level declaration keyword at COLUMN 0 — the boundary of a decl's span. Anchored to col 0
# (not `^\s*`) so an indented `have`/`let`/nested decl inside the target's proof can't be mistaken for
# the next top-level decl. Used to bound a named decl to its OWN text in multi-decl files, so a later
# decl's `:=` / trailing `sorry` cannot bleed into this decl's signature or proof extraction.
_TOPLEVEL_DECL = re.compile(
    r"(?m)^(?:noncomputable\s+|private\s+|protected\s+|scoped\s+|@\[[^\]]*\]\s*)*"
    r"(?:theorem|lemma|def|abbrev|instance|example|structure|inductive|class|opaque|axiom)\b")


def _decl_re(name: str) -> re.Pattern:
    return re.compile(_DECL_PREFIX + re.escape(name) + r"\b")


def _decl_body(source: str, name: str) -> str | None:
    """The named decl's text from just AFTER `theorem <name>` up to the NEXT top-level decl (or EOF). In a
    multi-decl file this fences the decl so a following lemma's `:=`/`sorry` cannot truncate this one's
    signature or be mistaken for its proof. None if the name isn't declared."""
    m = _decl_re(name).search(source or "")
    if not m:
        return None
    rest = source[m.end():]
    nxt = _TOPLEVEL_DECL.search(rest)
    return rest[:nxt.start()] if nxt else rest


def theorem_names(source: str) -> list[str]:
    """Every theorem/lemma name declared in the source, in order."""
    return re.findall(r"(?m)^\s*" + _DECL_PREFIX + r"([A-Za-z_][\w'.]*)", source or "")


def _comment_mask(t: str) -> "list[bool]":
    """The ONE canonical Lean-comment scan (single pass, correct precedence): returns a per-char mask
    where `mask[i]` is True iff char `i` is part of a comment. Block comments are NESTED-AWARE
    (`/- a /- b -/ c -/` masks the WHOLE region); a `--` line comment SUPPRESSES `/-` until the newline
    (so a `/-` inside a line comment can't open a phantom block that swallows a REAL `sorry` on a later
    line); inside a block comment `--` is inert. The newline that ENDS a line comment is NOT masked (it
    is layout, not comment). `strip_comments` (remove) and `blank_comments` (offset-preserving) both
    derive from this single scan — no module rolls its own `re.sub(r'/-.*?-/')`, which is non-nested
    and produces phantom decls (2026-06-13 audit: that divergence was the recurring bug)."""
    n = len(t)
    mask = [False] * n
    i, depth, in_line = 0, 0, False
    while i < n:
        c = t[i]
        if in_line:                       # in a `--` line comment: everything inert until newline
            if c == "\n":
                in_line = False           # the newline itself is layout, left unmasked
            else:
                mask[i] = True
            i += 1
            continue
        if depth == 0 and t[i:i + 2] == "--":   # line comment only opens at block-depth 0
            mask[i] = mask[i + 1] = True; in_line = True; i += 2; continue
        if t[i:i + 2] == "/-":
            mask[i] = mask[i + 1] = True; depth += 1; i += 2; continue
        if t[i:i + 2] == "-/" and depth > 0:
            mask[i] = mask[i + 1] = True; depth -= 1; i += 2; continue
        if depth > 0:
            mask[i] = True
        i += 1
    return mask


def strip_comments(text: str) -> str:
    """The canonical comment-stripper: REMOVE every Lean comment (nested block + line aware), via the
    one `_comment_mask` scan. Use when you only need comment-free text to substring/regex-scan."""
    t = text or ""
    m = _comment_mask(t)
    return "".join(c for c, x in zip(t, m) if not x)


def blank_comments(text: str) -> str:
    """The OFFSET-PRESERVING canonical strip: replace each comment char with a space (newlines kept),
    so character offsets / line numbers are preserved exactly. Use when a downstream parser needs span
    offsets into the ORIGINAL text (decl-block extraction, header split) but must not see comment text.
    Same `_comment_mask` scan as `strip_comments` — nested-aware (unlike a bare `re.sub`)."""
    t = text or ""
    m = _comment_mask(t)
    return "".join(("\n" if c == "\n" else " ") if x else c for c, x in zip(t, m))


def has_sorry(text: str) -> bool:
    """True if `sorry`/`admit` appears as code (line + NESTED block comments stripped first, so a
    `sorry` mentioned in a comment — even inside a nested comment — does not false-positive)."""
    return re.search(r"\b(?:sorry|admit)\b", strip_comments(text)) is not None


def _after_name(source: str, name: str) -> str | None:
    if not source or not name:
        return None
    m = _decl_re(name).search(source)
    return source[m.end():] if m else None


def extract_signature(source: str, name: str) -> str:
    """`<binders> : <conclusion>` VERBATIM — everything between `theorem <name>` and the PROOF `:=`
    (the last `:=` before the trailing `sorry`), so a `:=` inside a hypothesis/binder cannot truncate
    it. Used to build the matched-negative-control stub and any `theorem X <sig> := by` wrapper.
    Falls back to the first-`:=` capture only when there is no trailing `sorry`.
    """
    after = _decl_body(source, name)   # fenced to THIS decl (multi-decl safe)
    if after is None:
        return ""
    si = after.rstrip().rfind("sorry")
    if si >= 0:
        head = after[:si].rstrip()
        if head.endswith(":="):
            sig = head[:-2].rstrip()
            if sig:
                return sig
    # no trailing `sorry` (a proof-carrying decl): cut at the PROOF `:=`, binder-safe (NOT first `:=`,
    # which truncates a `let k := 5` hypothesis binder — the recurring `:=`-in-binder bug class).
    return split_at_proof(after)[0].strip()


def compile_stub(source: str, name: str) -> str:
    """A COMPILE-valid `... theorem <name> <sig> := by` taken VERBATIM from source (prelude + the
    target statement, proof swapped to `:= by`), with a single leading `import Mathlib` dropped (the
    verifier re-adds it). For native_hammer / any deterministic tactic probe. Statement is never
    reconstructed — Lean parses the original text. Assumes the target's proof is the trailing `sorry`
    (the adhoc / PutnamBench shape); returns "" if there is none.
    """
    if not source or not name or name not in source:
        return ""
    text = re.sub(r"\A\s*import\s+Mathlib\s*\n+", "", source, count=1)
    m = _decl_re(name).search(text)
    if not m:
        return ""
    body = _decl_body(text, name)   # the TARGET decl only — a later lemma's sorry can't be mis-picked
    if body is None:
        return ""
    si = body.rstrip().rfind("sorry")
    if si < 0:
        return ""
    # preamble (defs/aux lemmas BEFORE the target, kept verbatim) + the target statement up to its proof
    head = (text[:m.end()] + body[:si]).rstrip()
    if head.endswith(":="):
        return head + " by"
    if head.endswith(":= by"):
        return head
    return ""


def wrapped_goal_stub(source: str, name: str, fallback_signature: str = "") -> str:
    """A compile-valid `theorem <name> <sig> := by` for the enriched-context goal piece: prefer the
    real statement from source (via `extract_signature`), else wrap `fallback_signature` (a bare
    signature) or normalize a full decl. Always ends in `:= by`."""
    sig = extract_signature(source, name)
    if sig:
        return f"theorem {name} {sig} := by"
    bg = (fallback_signature or "").strip()
    if not bg:
        return ""
    if bg.lstrip().startswith(("theorem", "lemma", "example")):
        bg = bg.rstrip()
        if bg.endswith(":= by"):
            return bg
        bg = re.sub(r"\bsorry\s*$", "", bg).rstrip()
        return bg + " by" if bg.endswith(":=") else bg + " := by"
    return f"theorem {name or 'adhoc_probe'} {bg} := by"


def swap_sorry(source: str, proof_body: str) -> str:
    """The real source with the target's trailing `sorry` replaced by `by <proof_body>`."""
    if not source:
        return ""
    i = source.rstrip().rfind("sorry")
    if i < 0:
        return ""
    head = source[:i].rstrip()
    body = (proof_body or "").strip()
    if body.startswith("by "):
        body = body[3:].strip()
    if head.endswith(":="):
        return head + " by\n  " + body + "\n"
    if head.endswith(":= by"):
        return head + "\n  " + body + "\n"
    return ""


def first_theorem_name(text: str) -> str:
    """The first theorem/lemma name anywhere in `text` (not line-anchored), or ""."""
    m = re.search(_DECL_PREFIX + r"([A-Za-z_][\w'.]*)", text or "")
    return m.group(1) if m else ""


_OPEN_BRACKETS = "([{⟨⦃"
_CLOSE_BRACKETS = ")]}⟩⦄"


def split_at_proof(text: str) -> "tuple[str, str]":
    """Split a decl at the PROOF `:=` — the canonical binder-safe replacement for `text.split(":=", 1)`
    / `re.split(r":=", text, 1)`, which truncate at a `:=` INSIDE a binder (a `let k := 5` in a
    hypothesis type, a `(n := 3)` default arg, a `{ x := 1 }` structure literal). Returns
    `(signature, proof_incl_assign)` cut at the FIRST `:=` at bracket-depth 0 (outside `()[]{}⟨⟩⦃⦄`).
    Comments are stripped first (a `:=` in a comment can't be the proof). `(text, "")` if none."""
    t = strip_comments(text or "")
    depth, i, n = 0, 0, len(t)
    while i < n:
        c = t[i]
        if c in _OPEN_BRACKETS:
            depth += 1
        elif c in _CLOSE_BRACKETS:
            depth = max(0, depth - 1)
        elif depth == 0 and t[i:i + 2] == ":=":
            return t[:i].rstrip(), t[i:]
        i += 1
    return t, ""


def signature_before_proof(text: str) -> str:
    """The decl text up to (not including) the proof `:=`, binder-safe (see `split_at_proof`). Keeps any
    `theorem <name>` prefix — for callers that tokenize/normalize the signature and tolerate the prefix."""
    return split_at_proof(text)[0]


def strip_decl_prefix(head: str) -> str:
    """Strip a leading `theorem|lemma|example <name>` from a decl head, leaving the binder telescope
    (for callers that already split off the conclusion and need just `(a) (b) …`)."""
    m = re.match(r"\s*(?:theorem|lemma|example)\s+[\w'.]*\s*(.*)$", head or "", re.S)
    return (m.group(1).strip() if m else (head or "").strip())


def _selftest() -> None:
    # discriminating case: `:=` inside a hypothesis — the old first-`:=` regex truncated here.
    tricky = "import Mathlib\ntheorem foo (n : Nat) (h : (let k := 5; k) < n) : 0 < n :=\nsorry\n"
    sig = extract_signature(tricky, "foo")
    assert "0 < n" in sig and "let k := 5" in sig, sig
    assert compile_stub(tricky, "foo").rstrip().endswith(":= by"), compile_stub(tricky, "foo")
    assert compile_stub(tricky, "foo").count("import Mathlib") == 0  # leading import dropped
    assert wrapped_goal_stub(tricky, "foo").startswith("theorem foo") and \
        wrapped_goal_stub(tricky, "foo").rstrip().endswith(":= by")
    assert theorem_names(tricky) == ["foo"], theorem_names(tricky)
    assert has_sorry("x := sorry")
    assert not has_sorry("-- sorry here\n/- and sorry -/\nx := by trivial")
    # NESTED block comment: a non-nested `re.sub(/-.*?-/)` stops at the FIRST `-/`, leaking the tail
    # (`sorry -/`) as code → phantom-decl / false-sorry bug. The mask scan removes the WHOLE region.
    assert not has_sorry("/- outer /- inner sorry -/ still comment sorry -/\nx := by trivial"), \
        strip_comments("/- outer /- inner sorry -/ still comment sorry -/\nx := by trivial")
    assert strip_comments("a/- /- n -/ -/b") == "ab"
    # blank_comments is OFFSET-PRESERVING (same length, newlines kept) AND nested-aware. Distinctive
    # sentinels in the comment (so an assertion can't collide with real-code letters like `by`).
    _src = "theorem t :\n  /- Zq1 /- Zq2 -/ Zq3 -/ True := by\n  sorry\n"
    _bl = blank_comments(_src)
    assert len(_bl) == len(_src), (len(_bl), len(_src))
    assert _bl.count("\n") == _src.count("\n")
    assert "Zq1" not in _bl and "Zq2" not in _bl and "Zq3" not in _bl, _bl  # whole nested region blanked
    assert "True := by" in _bl and "sorry" in _bl                          # real code survives, offsets intact
    assert "/-" not in _bl and "-/" not in _bl, _bl                        # no leaked delimiters
    assert _bl.index("True") == _src.index("True"), "offset preserved"     # decl-block span math stays valid
    assert swap_sorry(tricky, "by trivial").rstrip().endswith("trivial")
    assert first_theorem_name("-- preamble\ntheorem bar : True := sorry") == "bar"
    assert strip_decl_prefix("theorem foo (a : Nat) (b : Nat)") == "(a : Nat) (b : Nat)"
    # binder-safe `:=` split: a `let k := 5` inside a hypothesis binder must NOT be read as the proof `:=`
    _bs = "theorem t (h : (let k := 5; k) < n) : 0 < n := by sorry"
    assert split_at_proof(_bs)[0] == "theorem t (h : (let k := 5; k) < n) : 0 < n", split_at_proof(_bs)
    assert split_at_proof(_bs)[1].startswith(":="), split_at_proof(_bs)
    # and on a PROOF-CARRYING (no trailing sorry) decl — the case the old first-`:=` fallback truncated
    _bs2 = "theorem t (h : (let k := 5; k) < n) : 0 < n := by omega"
    assert signature_before_proof(_bs2) == "theorem t (h : (let k := 5; k) < n) : 0 < n", signature_before_proof(_bs2)
    assert extract_signature(_bs2, "t").strip() == "(h : (let k := 5; k) < n) : 0 < n", extract_signature(_bs2, "t")
    assert split_at_proof("theorem t : True")[1] == ""   # no proof `:=` ⇒ ("…", "")
    # multi-binder / no-source fallbacks
    assert wrapped_goal_stub("", "bar", "(a : Nat) : a = a") == "theorem bar (a : Nat) : a = a := by"

    # MULTI-DECL: a preamble def + an aux lemma BEFORE the target, and a trailing lemma AFTER it. The
    # target's signature/stub must be fenced to the TARGET decl — a later/earlier decl's `:=`/`sorry`
    # must not bleed in (the bug class that made the goal-extractors ship malformed probes).
    multi = (
        "import Mathlib\n\n"
        "def helperFn (n : Nat) : Nat := n + 1\n\n"
        "theorem aux_lemma (n : Nat) : helperFn n = n + 1 := rfl\n\n"
        "theorem target_thm (n : Nat) : helperFn n = n + 1 :=\nsorry\n\n"
        "theorem trailing_thm : True := by trivial\n"
    )
    assert theorem_names(multi) == ["aux_lemma", "target_thm", "trailing_thm"], theorem_names(multi)
    # signature is the TARGET's, not aux's or trailing's
    sig_m = extract_signature(multi, "target_thm")
    assert sig_m.strip() == "(n : Nat) : helperFn n = n + 1", repr(sig_m)
    stub_m = compile_stub(multi, "target_thm")
    assert stub_m.rstrip().endswith("helperFn n = n + 1 := by"), repr(stub_m)
    assert "def helperFn" in stub_m and "aux_lemma" in stub_m, "preamble defs/aux must be preserved"
    assert "trailing_thm" not in stub_m, "trailing decl must be dropped (target doesn't depend on it)"
    assert stub_m.count("import Mathlib") == 0
    assert first_theorem_name(multi) == "aux_lemma"
    # the dangerous shape: an aux lemma BEFORE the target is itself `sorry`-proved. The target's stub must
    # still fence to the TARGET's sorry (extract its real signature), not the aux's.
    multi_sorried_aux = (
        "import Mathlib\n\n"
        "theorem aux_open (n : Nat) : n + 0 = n := by sorry\n\n"
        "theorem target2 (n : Nat) : 0 + n = n :=\nsorry\n"
    )
    assert extract_signature(multi_sorried_aux, "target2").strip() == "(n : Nat) : 0 + n = n", \
        extract_signature(multi_sorried_aux, "target2")
    assert compile_stub(multi_sorried_aux, "target2").rstrip().endswith("0 + n = n := by")
    print("lean_source selftest OK")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(__doc__)
