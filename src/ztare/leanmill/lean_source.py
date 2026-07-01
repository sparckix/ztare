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
# ONE canonical top-level decl kind-list drives BOTH `_TOPLEVEL_DECL` (keyword-boundary, for `_decl_body`
# fencing + `.search` over whole text) AND `DECL_START` (name-capturing, per-line, for `decl_blocks` /
# supersession span-bounding). A kind missing from this list silently MIS-BOUNDS a span: a decl of the
# missing kind sitting between two others gets swallowed into the neighbour's block and DELETED on splice —
# the reverted_noncompile bank corruption (RCA 2026-07-01, VCG multi-unit witness). Keep it exhaustive.
_DECL_KINDS = ("theorem", "lemma", "def", "abbrev", "instance", "example",
               "structure", "inductive", "class", "opaque", "axiom")
DECL_KINDS = _DECL_KINDS   # public: the FULL kind-list (incl anonymous `example`) — banking span-bounding uses it
# NAMED kinds only (drops anonymous `example`). The firewall parser (statement_integrity) sources THIS: it
# names anonymous decls `instance@<line>`, and comparing that line-derived name across original-vs-probe would
# FALSE-flag a shifted/dropped `example` as `deleted` (iatrogenic). Banking WANTS `example` as a span boundary
# (an `example` between decls must not be swallowed + deleted on supersession — the #51 class); the firewall
# does not. So the lists legitimately differ by exactly `example`; the parity guard checks the NAMED kinds.
NAMED_DECL_KINDS = tuple(k for k in _DECL_KINDS if k != "example")
_DECL_MODS = r"(?:noncomputable\s+|private\s+|protected\s+|scoped\s+|@\[[^\]]*\]\s*)*"
_TOPLEVEL_DECL = re.compile(r"(?m)^" + _DECL_MODS + r"(?:" + "|".join(_DECL_KINDS) + r")\b")
# Per-line, name-capturing: group(1)=kind, group(2)=name ('' for anonymous `example`). `\b` after the kind
# so `defeq` / `classy` / `structured` do not false-match the keyword.
DECL_START = re.compile(r"^" + _DECL_MODS + r"(" + "|".join(_DECL_KINDS) + r")\b(?:\s+([A-Za-z_][\w.']*))?")
# Non-decl top-level lines that END a decl block (a namespace/section/open/notation/... after the decl closes
# its span early). The notation/macro/syntax/fixity/attribute family is included so a theory-building campaign
# that ANCHORS bespoke `def`s with custom notation does not get that command SWALLOWED into a neighbouring
# decl's span and deleted on bank-splice — the same span-swallow class as the missing-`structure` bug (#51),
# closed preventively (no substrate declares notation yet, but a vocabulary-building campaign is exactly where
# it would appear). These are COMMANDS, not named decls, so they bound a span but are never themselves banked.
DECL_TERMINATORS = re.compile(
    r"^(end\b|#|namespace\b|section\b|open\b|variable\b|set_option\b|import\b"
    r"|notation\b|notation3\b|macro\b|macro_rules\b|syntax\b|declare_syntax_cat\b|elab\b|elab_rules\b"
    r"|infix\b|infixl\b|infixr\b|prefix\b|postfix\b|attribute\b)")


def decl_spans(text: str) -> "list[tuple[str, int, int]]":
    """THE canonical line-span index: `(name, start_line, end_line)` per top-level decl (name '' for anonymous
    `example`), end-exclusive. A span runs from its decl-start line to the next decl-start / terminator / EOF.
    ONE span computation feeds `decl_blocks` (text) and the substrate-mutating hygiene passes (span deletion),
    so the block splitter and any span editor can never disagree on where a decl ends. Line-based (keepends)."""
    lines = (text or "").splitlines(keepends=True)
    starts = [(i, (m.group(2) or "")) for i, ln in enumerate(lines) if (m := DECL_START.match(ln))]
    spans: "list[tuple[str, int, int]]" = []
    for k, (i, name) in enumerate(starts):
        end = starts[k + 1][0] if k + 1 < len(starts) else len(lines)
        for j in range(i + 1, end):
            if DECL_TERMINATORS.match(lines[j]):
                end = j
                break
        spans.append((name, i, end))
    return spans


def decl_blocks(text: str) -> "list[tuple[str, str]]":
    """THE canonical top-level (name, block) splitter (moved here from family_lemma_library 2026-07-01 so the
    banking span parser and the firewall parsers share ONE decl-kind list — no sibling that can drift). A block
    runs from its decl-start line to the next decl-start / terminator / EOF. Anonymous `example` yields name ''."""
    lines = (text or "").splitlines(keepends=True)
    return [(name, "".join(lines[i:end]).rstrip()) for name, i, end in decl_spans(text)]


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


_DEFKIND_PREFIX = r"(?:noncomputable\s+|private\s+|protected\s+|scoped\s+)*(?:def|abbrev|structure)\s+"


def def_names(source: str) -> list[str]:
    """Every def/abbrev/structure name declared in the source, in order — the canonical counterpart to
    `theorem_names` (the def-faithfulness / denotation legs key on the OBJECTS the agent introduced, not
    the lemmas). Comments are stripped first so a commented-out `def` can't surface a phantom name."""
    return re.findall(r"(?m)^\s*" + _DEFKIND_PREFIX + r"([A-Za-z_][\w'.]*)", strip_comments(source or ""))


def def_body(source: str, name: str) -> "str | None":
    """The named def/abbrev/structure's text from just AFTER `def <name>` to the next top-level decl (or EOF) —
    the def-keyword counterpart to `_decl_body` (which is `theorem`/`lemma`-only). `None` if not declared. The
    vacuity-faithfulness leg reads a def's BODY through this to see the vacuous-on-empty `∀`-over-membership
    that hides inside a `def` (`_decl_body` returned `None` for defs, so vacuity-prone detection saw nothing)."""
    m = re.compile(_DEFKIND_PREFIX + re.escape(name) + r"\b").search(source or "")
    if not m:
        return None
    rest = source[m.end():]
    nxt = _TOPLEVEL_DECL.search(rest)
    return rest[:nxt.start()] if nxt else rest


def def_is_prop_valued(source: str, name: str) -> bool:
    """True iff `def <name>`'s RETURN type is `Prop` — a CONCEPT / predicate definition (`StrongSetLE`,
    `IncreasingDifferences`), vs a TERM / instance definition (`const : OrdinalTopkisObjective`). The
    governed-revision gate uses this: a CONCEPT def is the laundering surface (must stay byte-identical unless
    it IS the def being strengthened); a term/instance def's body is effectively a PROOF (a structure's fields)
    and MAY adapt to a strengthened def. Binder-safe (the return-type `:` is the depth-0 colon, never a binder's)."""
    body = def_body(source, name)
    if not body:
        return False
    sig = signature_before_proof(body)            # ` <binders> : <rettype>` (def_body drops the `def <name>`)
    c = top_level_colon(sig)
    return c >= 0 and "Prop" in sig[c + 1:]


def prop_quantifies_over_membership(value: str) -> bool:
    """True iff `value` (a Prop — e.g. a def's body after `:=`) UNIVERSALLY quantifies over SET MEMBERSHIP with
    no explicit non-emptiness guard — the shape `∀ ⦃x⦄, x ∈ s → …` / `∀ x ∈ s, …` that is VACUOUSLY TRUE on the
    empty set. The canonical home for the vacuity leg's candidate detector (kept here, not hand-rolled at the
    call site): comment-stripped, and a `Nonempty` conjunct disqualifies it. It is only a CANDIDATE signal —
    `def_denotation.certify_nonvacuity` backstops it with a kernel-verified non-emptiness witness, so a false
    positive merely asks the agent for a witness that the kernel then checks (no soundness surface)."""
    v = strip_comments(value or "")
    if not v.strip():
        return False
    has_universal = ("∀" in v) or ("⦃" in v)
    has_membership = "∈" in v
    guarded_nonempty = "Nonempty" in v       # an explicit `s.Nonempty`/`Set.Nonempty` conjunct guards the ∀-over-∈
    return has_universal and has_membership and not guarded_nonempty


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


def attach_proof(head: str, proof_body: str) -> str:
    """Splice `proof_body` onto a decl `head` ending `:=` or `:= by` → a compilable `theorem … := <proof>`.
    THE canonical proof-splicer — callers MUST NOT hand-roll `head + body`.

    RCA 2026-06-18 (the mathd_algebra_302 silent-drop): a local splice that stripped only `"by "` (with a
    SPACE) produced `:= by\\n  by\\n  tac` for a multiline `by\\n` body — a DOUBLE `by` that silently
    elaborates to `sorry`, so the axiom audit flags `sorryAx` and a VALID proof is rejected as a banned axiom
    (the closure is dropped). This helper is `by`-TOKEN-aware (never mistakes `by_cases`/`by_contra` for a
    `by` block), preserves the body's internal indentation VERBATIM, and never doubles `by`."""
    h = (head or "").rstrip()
    body = (proof_body or "").strip()
    body_is_by_block = bool(re.match(r"by(?:\s|\Z)", body))   # `by` + whitespace/EOS, NOT `by_cases`
    if h.endswith(":= by"):
        # stub already opened the block: bare tactics go UNDER it; a body that carries its OWN `by` block
        # REPLACES the stub's `by` (drop it) so the two never double.
        return (h[:-2].rstrip() + "\n" + body + "\n") if body_is_by_block else (h + "\n  " + body + "\n")
    if h.endswith(":="):
        return (h + " " + body + "\n") if body_is_by_block else (h + " by\n  " + body + "\n")
    return h + "\n" + body + "\n"


def swap_sorry(source: str, proof_body: str) -> str:
    """The real source with the target's trailing `sorry` replaced by the proof. Delegates the splice to the
    canonical `attach_proof` (binder/`by`-token-aware) — no local `by` handling re-rolled here."""
    if not source:
        return ""
    i = source.rstrip().rfind("sorry")
    if i < 0:
        return ""
    return attach_proof(source[:i].rstrip(), proof_body)


def first_theorem_name(text: str) -> str:
    """The first theorem/lemma name anywhere in `text` (not line-anchored), or ""."""
    m = re.search(_DECL_PREFIX + r"([A-Za-z_][\w'.]*)", text or "")
    return m.group(1) if m else ""


_OPEN_BRACKETS = "([{⟨⦃"
_CLOSE_BRACKETS = ")]}⟩⦄"


def top_level_colon(sig: str) -> int:
    """Index of the binder/type-separating `:` at bracket depth 0 (binder colons inside (…)/[…]/{…}/⟨…⟩/⦃…⦄
    are nested → ignored). `sig` is a signature WITHOUT the `:=` body. -1 if none. THE canonical home for this
    primitive (2026-06-22 de-duplication): `conjecture._top_level_colon` and `statement_integrity._top_colon`
    were byte-identical copies — the forgotten-sibling shape — and now both re-export this one."""
    depth = 0
    pairs = {"(": ")", "[": "]", "{": "}", "⟨": "⟩", "⦃": "⦄"}
    closes = set(pairs.values())
    for i, c in enumerate(sig):
        if c in pairs:
            depth += 1
        elif c in closes:
            depth = max(0, depth - 1)
        elif depth == 0 and c == ":":
            return i
    return -1


def top_level_comma(sig: str) -> int:
    """Index of the FIRST comma at bracket depth 0 (commas inside (…)/[…]/{…}/⟨…⟩/⦃…⦄ are nested → ignored).
    -1 if none. Used to find the `∀ <binders>, <body>` binder/body separator (the binder list itself carries
    no top-level comma). Canonical sibling of `top_level_colon`."""
    depth = 0
    pairs = {"(": ")", "[": "]", "{": "}", "⟨": "⟩", "⦃": "⦄"}
    closes = set(pairs.values())
    for i, c in enumerate(sig):
        if c in pairs:
            depth += 1
        elif c in closes:
            depth = max(0, depth - 1)
        elif depth == 0 and c == ",":
            return i
    return -1


def pi_normalized_signature(sig: str) -> str:
    """Canonicalize a theorem signature to its ∀-FRONTED form so a binders-after-colon statement
    `(a:A) (b:B) : C` and its ∀-fronted reformulation `: ∀ a:A, ∀ b:B, C` — the SAME Pi type (NOT a weakening),
    differing only in BINDER PLACEMENT — normalize to the SAME string, ENV-INDEPENDENTLY (no kernel, no campaign
    env). `sig` is the signature WITHOUT the `:=` body (as `extract_signature` returns). Canonical primitives
    only (`top_level_colon`/`top_level_comma`) — NO regex.

    SOUNDNESS (this is an UPGRADE-only accept-helper for the faithfulness gate): it accepts ONLY when the binder
    LISTS and the final CONCLUSION are textually identical after moving leading `∀` binders into the binder slot.
    A real weakening — dropped/added/reordered hypothesis, altered conclusion — yields a DIFFERENT normalized
    string ⇒ NOT accepted here ⇒ it still falls through to the kernel type-equiv oracle (unchanged). So this can
    only ever turn a brittle TEXT false-reject of a ∀-fronting reformulation into an accept; it can never admit a
    genuinely different type."""
    s = " ".join((sig or "").split())
    ci = top_level_colon(s)
    if ci < 0:
        return s
    binders = s[:ci].strip()
    rest = s[ci + 1:].strip()
    # Peel leading `∀ <bs>, <body>` groups from the type into the binder list (idempotent; bounded by length).
    guard = 0
    while guard < 64 and (rest.startswith("∀") or rest.startswith("forall ")):
        guard += 1
        after = (rest[1:] if rest.startswith("∀") else rest[len("forall"):]).lstrip()
        comma = top_level_comma(after)
        if comma < 0:
            break
        bs = after[:comma].strip()
        rest = after[comma + 1:].strip()
        binders = (binders + " " + bs).strip() if binders else bs
    return f"∀ {binders}, {rest}" if binders else rest


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


def redundant_subsumed_instances(source: str, name: "str | None" = None) -> "list[str]":
    """Detect a BARE order-instance binder that a RICHER binder on the SAME type ALREADY provides — the classic
    `[LE α]` (or `[LT α]`) declared ALONGSIDE `[Preorder α]`/`[PartialOrder α]`/`[LinearOrder α]`/any `*Order…`.

    This is NOT harmless redundancy: the bare class adds a SECOND, axiom-free `≤`/`<` instance on the type, so
    Lean may resolve the goal's `≤` to it while the order lemmas use the Order's `≤` — an instance DIAMOND that
    makes the statement UNPROVABLE (sometimes false). RCA 2026-06-23: the planner formalized `iso_lemma1` with
    `[Add α] [LE α] [Preorder α] …`; the same statement WITHOUT the `[LE α]` proves cleanly, WITH it fails with a
    type mismatch — and the agent (correctly) flagged it STATEMENT-FALSE. A pure detector (the canonical parser's
    job): returns the offending bare classes (e.g. `"LE α (subsumed by Preorder α)"`), or `[]` when clean. It
    only flags ORDER subsumption (LE/LT ⊂ an Order class) — unambiguous; `[Add α]` next to `[Preorder α]` is NOT
    flagged (Preorder does not provide Add)."""
    body = (_decl_body(source, name) if name else None) or source
    head = signature_before_proof(body)
    # instance-implicit binders only: `[ClassName <type-args>]` (skip `()`/`{}`/`⦃⦄` value/implicit binders)
    binders = re.findall(r"\[\s*([A-Za-z_][\w'.]*)\s+([^\]\[]+?)\s*\]", head)
    by_typevar: "dict[str, set[str]]" = {}
    for cls, args in binders:
        by_typevar.setdefault(args.strip(), set()).add(cls)
    offenders: "list[str]" = []
    for tv, classes in by_typevar.items():
        order_cls = sorted(c for c in classes if "order" in c.lower())   # Preorder/PartialOrder/LinearOrder/*Order
        if not order_cls:
            continue
        for bare in ("LE", "LT"):
            if bare in classes:
                offenders.append(f"{bare} {tv} (subsumed by {order_cls[0]} {tv})")
    return offenders


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
    # attach_proof: NEVER double `by` (RCA 2026-06-18, the mathd_algebra_302 silent-`sorry` drop).
    _stub = "theorem t : (Complex.I / 2) ^ 2 = -(1 / 4) := by"   # stub ends `:= by`
    # (a) single-line `by ` body → drop stub's `by`, no double
    assert attach_proof(_stub, "by rw [x]; norm_num").count("by") == 1, attach_proof(_stub, "by rw [x]; norm_num")
    # (b) MULTILINE `by\n` body — the exact shape that produced `:= by\n  by\n tac` → sorry
    _multi = attach_proof(_stub, "by\n  rw [x]\n  norm_num")
    assert _multi.count("by") == 1 and "by\n  by" not in _multi, _multi
    # (c) bare tactics (no `by`) → run UNDER the stub's `by`
    assert attach_proof(_stub, "rw [x]").count("by") == 1
    # (d) `by_cases` is a TACTIC, not a `by` block → must go under the stub's `by` (not be mistaken for one)
    assert "by\n  by_cases" in attach_proof(_stub, "by_cases h : p")
    # (e) head ending bare `:=` wraps bare tactics in a fresh `by`
    assert attach_proof("theorem t : P :=", "exact h").rstrip().endswith(":= by\n  exact h".rstrip()) or \
           "by" in attach_proof("theorem t : P :=", "exact h")
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
    # redundant_subsumed_instances: the 2026-06-23 iso_lemma1 diamond ([LE α] under [Preorder α])
    _diamond = ("theorem iso_lemma1 {α : Type*} [Add α] [LE α] [Preorder α] [AddLeftMono α] "
                "[AddRightReflectLE α] {a b c d : α} (h : a + b ≤ c + d) (hd : d ≤ b) : a ≤ c := by sorry")
    _off = redundant_subsumed_instances(_diamond, "iso_lemma1")
    assert any(o.startswith("LE α") for o in _off), _off          # flags the redundant [LE α]
    _clean = ("theorem ok {α : Type*} [Add α] [Preorder α] [AddLeftMono α] "
              "[AddRightReflectLE α] {a b : α} (h : a ≤ b) : a ≤ b := by sorry")
    assert redundant_subsumed_instances(_clean, "ok") == [], redundant_subsumed_instances(_clean, "ok")  # clean
    # [Add α] next to [Preorder α] is NOT a subsumption (Preorder doesn't provide Add) → no false positive
    assert redundant_subsumed_instances(_clean, "ok") == []
    # prop_quantifies_over_membership: the vacuity-leg candidate detector (Gemini empty-set critique)
    assert prop_quantifies_over_membership("∀ ⦃x y : X⦄, x ∈ s → y ∈ u → x ⊓ y ∈ s ∧ x ⊔ y ∈ u")  # StrongSetLE shape
    assert not prop_quantifies_over_membership("s.Nonempty ∧ ∀ ⦃x⦄, x ∈ s → True")                 # guarded
    assert not prop_quantifies_over_membership("∀ x y : X, x ⊓ y = y ⊓ x")                          # no membership
    assert not prop_quantifies_over_membership("-- ∀ x ∈ s, foo\n0")                                # comment-only ∀/∈
    print("lean_source selftest OK")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(__doc__)
