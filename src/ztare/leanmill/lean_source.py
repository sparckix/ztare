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
from bisect import bisect_right
from dataclasses import dataclass
import re


def ensure_import_header(
    text: str, *, header: str = "import Mathlib"
) -> str:
    """Make a standalone Lean source import-complete, idempotently.

    This is a source-normalization primitive, independent of any proof-search
    carrier.  Keeping it beside the canonical Lean text utilities prevents
    audit and ratification code from importing the agentic solver merely to
    prepare a file for compilation.
    """

    if re.search(r"(?m)^\s*import\s+\w", text or ""):
        return text
    return f"{header}\n\n{text}"

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
# The decl MODIFIER prefix (repeatable). `partial`/`unsafe`/`nonrec` (2026-07-05 OOD-axis-2): a `partial def` /
# `unsafe def` / `nonrec def` line otherwise matches NO decl-start (the modifier isn't consumed, so the kind
# keyword isn't at the anchor) ⇒ the decl is span-INVISIBLE ⇒ swallowed into the neighbour and DELETED on splice
# — the reverted_noncompile class, in the recursive-engine domain (a matching loop / fixpoint / traversal is where
# `partial def` first appears). ONE modifier list so `_TOPLEVEL_DECL`, `DECL_START`, and the def-body audits agree.
_DECL_MODS = r"(?:noncomputable\s+|private\s+|protected\s+|scoped\s+|partial\s+|unsafe\s+|nonrec\s+|@\[[^\]]*\]\s*)*"
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
    r"^(end\b|#|namespace\b|section\b|noncomputable\s+section\b|open\b|variable\b|set_option\b|import\b|mutual\b"
    r"|include\b|omit\b|universe(?:s)?\b|export\b|local\b"
    r"|notation\b|notation3\b|macro\b|macro_rules\b|syntax\b|declare_syntax_cat\b|elab\b|elab_rules\b"
    r"|infix\b|infixl\b|infixr\b|prefix\b|postfix\b|attribute\b)")
# `mutual\b` (2026-07-05 OOD-axis-2): a `mutual … end` block is idiomatic in category-theory / recursive-engine
# substrates. `mutual` is neither a named decl nor (previously) a terminator, so the keyword line was swallowed
# into the PRECEDING decl's span and DELETED with it on splice ⇒ an unbalanced `mutual`/`end` (the #51 span-swallow
# class). As a terminator it stands alone (like `section`/`namespace`): it BOUNDS the previous span, is never part
# of a decl block, and so survives every splice. The block's inner `def`s remain their own spans (their `end` is
# already a terminator), which is correct — they are not independently bankable rungs.


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


def preamble_before_target(text: str, target_name: str) -> str:
    """Return source before a named target declaration via the canonical span parser.

    This is the environment a child theorem inherits: imports, namespaces,
    notation, definitions, and prior lemmas.  It deliberately does not parse
    Lean with a local regex; callers that reconstruct or verify a target must
    share this boundary with the rest of ``lean_source``.
    """
    requested = (target_name or "").strip()
    if not requested:
        return (text or "").rstrip()
    # Resolve spelling/identity once. The fallback retains the historical last-
    # basename rule only for an ambiguous stale supersession shelf.
    identity = resolve_theorem_target(text, requested)
    if identity is not None:
        return (text or "")[:identity.decl_start].rstrip()
    target = requested.rsplit(".", 1)[-1]
    lines = (text or "").splitlines(keepends=True)
    matches = [(start, end) for name, start, end in decl_spans(blank_comments(text or "")) if name == target]
    if not matches:
        return (text or "").rstrip()
    # Assemblers append their target last; choosing the last matching span
    # agrees with `dedup_decl_keep_last` when a stale shelf has a name collision.
    start, _ = matches[-1]
    return "".join(lines[:start]).rstrip()


def source_through_target(text: str, target_name: str) -> str:
    """Return the target's formal work item: inherited source through that declaration.

    Later declarations are not premises of the target and therefore do not
    belong in its leaf-edit or statement-integrity contract.  If identity
    resolution fails, retain the complete source so callers fail visibly at
    their normal target gate instead of silently dropping context.
    """
    identity = resolve_theorem_target(text, target_name)
    return (
        (text or "")[:identity.decl_end].rstrip()
        if identity is not None
        else (text or "").rstrip()
    )


def close_open_scopes(text: str) -> str:
    """Close namespaces/sections opened by a source prefix.

    A target audit should compile the declaration context that existed when
    the target was elaborated, without compiling unrelated later declarations.
    ``source_through_target`` provides that prefix; this helper makes the
    prefix a standalone module through the same comment-aware scope index used
    for theorem identity.  Already-balanced sources are returned unchanged.
    """

    source = text or ""
    closers = _unclosed_scope_closers(source)
    if not closers:
        return source
    return source.rstrip() + "\n\n" + "\n".join(closers) + "\n"


def decl_kind(block: str) -> str:
    """Return the canonical top-level declaration kind for a block, or ``."""
    m = DECL_START.match((block or "").lstrip())
    return m.group(1) if m else ""


def identifier_token_mentions(text: str, name: str) -> bool:
    """Token-boundary identifier mention check for declaration names."""
    if not text or not name:
        return False
    return re.search(rf"(?<![A-Za-z0-9_'.]){re.escape(name)}(?![A-Za-z0-9_'])", text) is not None


def _conclusion_lhs(block: str) -> str:
    """The LHS of a decl's conclusion equation, or "" — bracket-depth aware so binder colons/equals don't fool it.
    `theorem t {a:T} (b:U) : f (C x) = y := rfl` → "f (C x)". Returns "" if no top-level `:` or `=`."""
    sig = block.split(":=", 1)[0]        # drop the proof body
    depth, colon = 0, -1
    for i, c in enumerate(sig):
        if c in "([{⟨": depth += 1
        elif c in ")]}⟩": depth -= 1
        elif c == ":" and depth == 0:    # the conclusion colon (binder colons are inside brackets)
            colon = i; break
    if colon < 0:
        return ""
    concl, depth = sig[colon + 1:], 0
    for i, c in enumerate(concl):
        if c in "([{⟨": depth += 1
        elif c in ")]}⟩": depth -= 1
        elif c == "=" and depth == 0 and concl[i:i + 2] != "=>":
            return concl[:i].strip()
    return ""


def simp_tag_computational_anchors(text: str) -> str:
    """DURABLE fix for the iatrogenic 'correct leaf proof retracts because the substrate's reduction lemma isn't
    @[simp]' class (RCA 2026-07-04, RBAC iso_lemma3: `simp [grants,…]` reduced in the self-contained probe but NOT
    against the substrate, because theory-consolidation emitted `anchor_grants_assignRole := rfl` WITHOUT `@[simp]`
    → a correct simp-proof left an unsolved goal → reverted_noncompile → env-parity retract). Theory-consolidation
    generates the reduction anchors but never tags them; this tags the COMPUTATION rules so any leaf's standard
    simp-proof PORTS to the substrate. SOUND + conservative: tags an `anchor_*` ONLY when it is proved by pure `rfl`
    (a definitional equality — always a safe simp lemma) AND its conclusion LHS is an APPLICATION (contains `(` — a
    `f (Ctor …) = …` or `(app).proj = …` computation rule); a bare `X = Y` (type/def synonym, e.g. `Permission =
    Type`) is NOT tagged (avoids over-rewriting). Idempotent (skips an anchor already `@[simp]`). Single door: call
    at theory finalization so EVERY campaign substrate is simp-friendly, not per-substrate hand-patched."""
    out = []
    for name, block in decl_blocks(text):
        lhs = _conclusion_lhs(block)
        # A COMPUTATION rule is `f (Ctor …) = rhs`: LHS is a single application term (has `(`) with NO logical
        # connective. Reject `↔`/`∃`/`∀`/`∧`/`∨`/`→` in the LHS — a biconditional/quantified definitional unfold
        # (e.g. `Reachable … ↔ ∃ ops, … = target := rfl`, whose nested `=` the depth-scanner would else mistake for
        # the top-level relation) must NOT be @[simp] (it would over-unfold everywhere — iatrogenic over-eagerness).
        tag = (name.startswith("anchor_")
               and re.search(r":=\s*(by\s+)?rfl\s*$", block) is not None
               and "@[simp]" not in block.split("\n", 1)[0]
               and "(" in lhs
               and not any(op in lhs for op in ("↔", "∃", "∀", "∧", "∨", "→", "<->", "\\/", "/\\")))
        out.append("@[simp]\n" + block if tag else block)
    # decl_blocks rstrips each block + drops inter-decl blank lines; re-join with the blank-line separation Lean
    # style uses. Non-decl preamble (imports/namespace opener) precedes the first decl — preserve it.
    first = decl_spans(text)
    if not first:
        return text
    preamble = "".join((text or "").splitlines(keepends=True)[:first[0][1]])
    return (preamble + "\n\n".join(out) + "\n") if any(o.startswith("@[simp]\n") for o in out) else text


def dedup_decl_keep_last(source: str, name: str) -> str:
    """Remove all but the LAST top-level decl named `name`, keeping every OTHER decl in place. THE unique-target
    enforcer (2026-07-02 RCA — the Basel `iso_lemma1` in-file collision that blocked kernel ratification): an
    assembled probe can carry a proven SHELF rung sharing the target's GENERIC decomposition name (`iso_lemmaN`)
    AND the target itself, so `theorem iso_lemma1` appears twice — and every name-based extractor
    (statement_integrity's original-vs-probe diff, the closing-probe readback, `_decl_body` find-first vs
    `decl_blocks` last-wins) then resolves a DIFFERENT decl ⇒ false `target_signature_altered`. Every assembler
    appends the TARGET last, so the LAST occurrence IS the target; drop the earlier same-named shelf copies (which
    can never be correctly cited anyway — a same-named decl is shadowed by the target). Line-based on the canonical
    comment/scope-aware `decl_spans`. Byte-parity when `name` occurs ≤ 1× (idempotent, no-op for every unique name)."""
    spans = [(n, i, e) for (n, i, e) in decl_spans(source or "") if n == name]
    if len(spans) <= 1:
        return source
    lines = (source or "").splitlines(keepends=True)
    drop: set = set()
    for (_, i, e) in spans[:-1]:          # every occurrence EXCEPT the last (the target)
        drop.update(range(i, e))
    return "".join(l for k, l in enumerate(lines) if k not in drop)


_DEFINITION_KINDS = frozenset(k for k in _DECL_KINDS if k not in ("theorem", "lemma", "example"))


def strip_env_declared_decls(probe_txt: str, env_text: str, keep: str = "") -> str:
    """SINGLE-DOOR campaign-verify dedup (chronic 'already been declared' fix, 2026-07-01). A self-contained probe
    verified against a warm campaign ENV that already holds the theory's decls errors `X has already been declared`
    ⇒ a VALID proof never ratifies (chronic thrash since 2026-06-08; native-only proofs escaped, masking it). Drop
    from `probe_txt` every decl the env already declares — DEFINITIONS always (canonical, never sorried) + PROVEN
    theorems (their env block has no `sorry`, so citing the env copy is safe) — EXCEPT `keep` (the target being
    proved) and genuinely-NEW decls (not in the env). A SORRIED env theorem is NOT stripped: dropping the probe's
    proven copy would bind the target's cite to the env `sorry` ⇒ `sorryAx` (the sorried-sibling trap). SOUND: env
    decls are canonical; an inlined DIFFERENT (cheat) def is dropped and the proof then compiles against the REAL
    env def — if it relied on the cheat it FAILS (correct rejection), never a false pass. THE one door for every
    warm-verify caller (leaf, conjecture/refute, solver_core) so the fix cannot rot into siblings. `open`/`variable`/
    imports are untouched (only decl BLOCKS removed). Fail-open (unchanged on any parse error); byte-parity when the
    probe re-declares nothing the env already has."""
    try:
        strippable: "set[str]" = set()
        for (n, b) in decl_blocks(env_text):
            if not n:
                continue
            m = DECL_START.match((b or "").lstrip())
            kind = m.group(1) if m else ""
            if kind in _DEFINITION_KINDS or "sorry" not in (b or ""):
                strippable.add(n)
        if not strippable:
            return probe_txt
        out = probe_txt
        for (n, block) in decl_blocks(probe_txt):
            if n and n != keep and n in strippable and (block or "").strip():
                out = out.replace(block, "", 1)   # env supplies this decl; re-declaring it clashes
        return out
    except Exception:  # noqa: BLE001 — dedup is best-effort; the cold path is the sound fallback
        return probe_txt


def section_variable_lines(text: str) -> "list[str]":
    """The `variable …` command lines a substrate declares, first-seen order, de-duplicated (2026-07-02 RCA).
    A campaign theory in idiomatic Lean section style (`section … variable [LinearOrder A] [Fintype V] … end`)
    exposes its decls' TYPE/INSTANCE binders through those section variables; when the sections CLOSE (`end`)
    the binders leave scope, and the pre-elaborated campaign env has them gone. A probe compiled by RE-ENTERING
    the namespace resolves sibling def NAMES but NOT those binders — so a target whose signature needs a section
    instance (`Fintype.card V` ⇒ `[Fintype V]`) fails `synthInstanceFailed` and can never ratify (median-voter
    was the first section-style campaign, so this bit only there). Re-declaring these lines after namespace
    re-entry restores the exact authoring context. Token split on the comment-stripped source (a `variable`
    inside a comment is not a command), mirroring family_lemma_library._open_namespaces. `[]` for a flat theory
    (byte-parity — no re-declaration, no behaviour change for every prior campaign shape)."""
    seen: "list[str]" = []
    for raw in strip_comments(text or "").splitlines():
        s = " ".join(raw.split())
        if s.split()[:1] == ["variable"] and s not in seen:
            seen.append(s)   # ponytail: single-line `variable` (the substrate norm); a rare multi-line binder would drop its continuation
    # MERGE BY BINDER (2026-07-05, the CLOB `failed to synthesize LT T` substrate-corruption RCA). A section-style
    # substrate declares the SAME type binder `{K T : Type*}` across MULTIPLE sections with DIFFERENT instance sets
    # — `section Core` has `[Zero K] [LinearOrder K]` (no order on the time type T) while `section Ordered` adds
    # `[LT T]`. Emitting BOTH raw lines re-declares the same `{K T}` binder TWICE with conflicting instances inside a
    # banked family `section`; when that section ends, Lean does NOT restore the enclosing section's stronger
    # instance context, so a later authored decl loses `[LT T]` and the WHOLE substrate silently stops compiling
    # (the reuse path then can't fetch/verify anything). The banked rungs are ∀-fronted (self-binding) so they never
    # even used these lines — pure poison. Cure: ONE line per binder = the UNION of its instance brackets in
    # first-seen order, so the re-declaration is consistent and carries the FULL context. A single-instance-set
    # substrate yields one line in → one line out (byte-parity for every flat/consistent theory).
    by_binder: "dict[str, list[str]]" = {}
    order: "list[str]" = []
    for s in seen:
        rest = s[len("variable"):].lstrip()
        cut = rest.find("[")
        binder = re.sub(r"\s+", " ", (rest[:cut] if cut >= 0 else rest)).strip()   # the `{…}`/`(…)` part, ws-normed
        insts = re.findall(r"\[[^\[\]]*\]", rest)                                   # instance brackets (non-nested)
        if binder not in by_binder:
            by_binder[binder] = []
            order.append(binder)
        for it in insts:
            if it not in by_binder[binder]:
                by_binder[binder].append(it)                                       # union, first-seen order
    merged: "list[str]" = []
    for binder in order:
        insts = by_binder[binder]
        merged.append(" ".join(part for part in ("variable", binder, *insts) if part))
    return merged


def strip_scope_commands(text: str) -> str:
    """Drop top-level `namespace`/`section`/`end` COMMAND lines so a caller that re-wraps the body in its OWN
    `namespace … end` owns the scoping. THE single door for every assembler that wraps a probe/proof body (warm
    verify, conjecture-probe, statement-integrity, iso-decompose) — a body shown a theory with `namespace X` + a
    NAMED `section Y` copies those markers and mis-nests the `end`s (`end X` while `section Y` is still open) → an
    `end`-mismatch that REJECTS a VALID proof (the EF1 round-robin RCA, 2026-07-03; third section-scope instance).
    Detected on the OFFSET-PRESERVING `blank_comments` view (a scope word inside a comment is not a command),
    line-aligned 1:1 with the original, mirroring `section_variable_lines`. `variable`/`open`/decls are untouched
    (that's the harness's re-declared context / the proof itself). Byte-parity when the body has no top-level scope
    command — so applying it at a site that never receives one is a safe no-op."""
    orig = (text or "").splitlines()
    clean = blank_comments(text or "").splitlines()
    out = []
    for i, ln in enumerate(orig):
        tokens = (clean[i] if i < len(clean) else ln).split()
        if (
            tokens[:1] and tokens[0] in ("namespace", "section", "end")
        ) or tokens[:2] == ["noncomputable", "section"]:
            continue
        out.append(ln)
    return "\n".join(out)


def supersede_sorried_twins(theory_text: str) -> "tuple[str, list[tuple[str, str]]]":
    """SUPERSESSION dedup for the sorried-sibling class (2026-07-01). The theory_consolidation APPEND-ONLY gate
    forbids the agent editing `X := sorry` → `X := proof`, so when it proves a shelf lemma it appends a proven
    TWIN (`X_banked`) and the canonical `X` stays `sorry` — sorried-canonical / proven-twin pairs accumulate
    (inflating the shelf, blocking a clean filing). This folds each proven twin back into its sorried canonical:
    for every theorem/lemma group sharing one α-normalized SIGNATURE that has BOTH a sorried member and a proven
    member, rewrite each sorried member's body to `:= by exact <proven twin>` (the twin proves the identical
    statement, so this is kernel-sound; the twin is applied to the canonical's context by `exact`). The HARNESS
    doing this is not agent laundering — it only replaces a `sorry` with a kernel-checkable cite of an existing
    proof. Returns (new_text, [(canonical, twin), …]); MUST be kernel-reverified by the caller (compile +
    `#print axioms`). Defs are never touched (never sorried). Idempotent (a canonical already `:= by exact` has
    no `sorry` ⇒ not a member of the sorried set)."""
    from collections import defaultdict
    try:
        from ztare.leanmill.solver.proof_cache import normalize_statement_equiv
    except Exception:  # noqa: BLE001 — degrade to whitespace-normalized signature match
        normalize_statement_equiv = lambda s: " ".join((s or "").split())  # noqa: E731

    def _sigkey(b: str) -> str:
        s = signature_before_proof(b) or b
        try:
            return normalize_statement_equiv(s)
        except Exception:  # noqa: BLE001
            return " ".join((s or "").split())

    groups: "dict[str, list[tuple[str, str]]]" = defaultdict(list)
    for (n, b) in decl_blocks(theory_text):
        if not n:
            continue
        m = DECL_START.match((b or "").lstrip())
        if m and m.group(1) in ("theorem", "lemma"):
            groups[_sigkey(b)].append((n, b))

    out = theory_text
    report: "list[tuple[str, str]]" = []
    for members in groups.values():
        proven = [(n, b) for (n, b) in members if "sorry" not in (b or "")]
        sorried = [(n, b) for (n, b) in members if "sorry" in (b or "")]
        if not (proven and sorried):
            continue
        twin = proven[0][0]
        for (n, b) in sorried:
            if n == twin:
                continue
            sig = (signature_before_proof(b) or "").rstrip()
            if not sig or b not in out:
                continue
            out = out.replace(b, f"{sig} := by exact {twin}", 1)
            report.append((n, twin))
    return out, report


def rename_decl(text: str, old: str, new: str) -> str:
    """Rename the DECLARATION named `old` to `new` (its `<kind> old` head only — a theorem/lemma never cites
    itself, so the head is the whole rename). Canonical (decl_spans + DECL_START); renames the FIRST top-level
    decl named `old`. Used by the campaign warm-verify to give a proof of a decl the env holds SORRIED a FRESH
    name so it doesn't clash with its own env copy (the documented 'fresh decl name' contract; mirrors
    solver_core's `_zwv`/`_zax`). Returns text unchanged if `old` is empty, `old == new`, or no such decl."""
    if not old or old == new:
        return text
    lines = (text or "").splitlines(keepends=True)
    for (name, i, _e) in decl_spans(text):
        if name == old:
            m = DECL_START.match(lines[i])
            if m and (m.group(2) or "") == old:
                lines[i] = lines[i].replace(f"{m.group(1)} {old}", f"{m.group(1)} {new}", 1)
                return "".join(lines)
    return text


_BRACKET_OPEN = "([{⟨⦃"
_BRACKET_CLOSE = ")]}⟩⦄"


def top_level_split(s: str, sep_chars: "set[str]") -> "list[str]":
    """THE canonical splitter of `s` on single-char separators at bracket-depth 0 (Unicode-safe); strips + drops
    empties. Moved here 2026-07-01 so every decomposer shares ONE connective splitter — no drifting sibling."""
    parts, buf, depth = [], [], 0
    for c in s:
        if c in _BRACKET_OPEN:
            depth += 1; buf.append(c)
        elif c in _BRACKET_CLOSE:
            depth = max(0, depth - 1); buf.append(c)
        elif depth == 0 and c in sep_chars:
            parts.append("".join(buf)); buf = []
        else:
            buf.append(c)
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


def leading_binder_comma(s: str) -> int:
    """Index of the FIRST `,` at bracket-depth 0 — where a leading `∀/∃/Π <binders>,` prefix ends; -1 if none."""
    depth = 0
    for i, c in enumerate(s):
        if c in _BRACKET_OPEN:
            depth += 1
        elif c in _BRACKET_CLOSE:
            depth = max(0, depth - 1)
        elif depth == 0 and c == ",":
            return i
    return -1


def strip_forall_prefix_or_defer(conclusion: str) -> "tuple[str, str] | None":
    """THE ONE quantifier guard every deterministic structural split routes through, so the soundness rule can
    never drift into a hand-copied sibling again (2026-07-01 NS-hunt RCA: `∃ w, A w ∧ B w` and `∃ w, A w ↔ B w`
    were split as if closed, orphaning the shared witness `w` as a free variable in the tail — the audit rejected
    the ill-typed result, so it failed SAFE, but the guard was missing from a twin decomposer).

    Strip a leading `∀`/`Π` prefix (which DISTRIBUTES over both `∧` and `↔`, so the pieces stay well-typed once the
    prefix is re-prepended) and return (qprefix, body). Return None when the body LEADS with `∃` — an existential
    binds a shared witness, does NOT distribute over `∧`/`↔`, and must be left to the planner / witness_transport.
    A `∃` INSIDE one operand — `(∃ w, A w) ∧ B` — leads with `(`, not `∃`, and is correctly splittable."""
    body = (conclusion or "").strip()
    if not body:
        return None
    qprefix = ""
    while body[:1] in ("∀", "Π") or body.startswith("\\forall"):
        cc = leading_binder_comma(body)
        if cc < 0:
            break
        qprefix = (qprefix + " " + body[:cc + 1]).strip()   # keep the binder-terminating comma
        body = body[cc + 1:].strip()
        if not body:
            return None
    if body[:1] == "∃" or body.startswith("Exists") or body.startswith("\\exists"):
        return None
    return qprefix, body


def safe_conjunction_split(conclusion: str) -> "tuple[str, list[str]] | None":
    """SINGLE DOOR for splitting `[∀-prefix] C₁ ∧ … ∧ Cₙ` into WELL-TYPED conjuncts (shared by every conjunction
    decomposer). Returns (qprefix, [C₁…Cₙ]) to PREPEND the ∀-prefix to each conjunct, or None when unsafe/absent:
    ∃-led (shared witness — deferred by `strip_forall_prefix_or_defer`), a top-level `↔` (a different composite),
    or fewer than two conjuncts (atomic)."""
    got = strip_forall_prefix_or_defer(conclusion)
    if got is None:
        return None
    qprefix, body = got
    if len(top_level_split(body, {"↔"})) == 2:
        return None
    conjuncts = top_level_split(body, {"∧"})
    if len(conjuncts) < 2:
        return None
    # BINDER SCOPING (2026-07-02 RCA — the DeFi 3-way `A ∧ B ∧ ∃ w, P ∧ Q` target false-gapped a PROVABLE result).
    # `top_level_split` on `∧` does not know that an ∃/∀/Σ binder OPENING a conjunct scopes to the END of the
    # expression (binders bind loosest), so it kept splitting the binder's OWN body — orphaning `Q` from its witness
    # `w` (`… ∃ w, P` | `Q`, an ill-typed UNSOUND conjunct). The decomposition audit then rejected the whole split,
    # the composite fell to the agentic planner, which regrouped the conjuncts and assembled `(A∧B) ∧ C` — the WRONG
    # associativity for the right-associative `A ∧ (B ∧ C)` target — so a target provable by `⟨A,B,C⟩` false-gapped.
    # Once a conjunct BEGINS with an unscoped binder, that binder absorbs every FOLLOWING conjunct: merge them back
    # into ONE well-typed conjunct. A binder in BRACKETS (`(∃ w, P)`) starts with `(`, so it stays a standalone
    # conjunct — only the loose, end-scoping binder triggers the merge.
    for _i, _c in enumerate(conjuncts):
        if re.match(r"\s*(?:∃|∀|Σ|Exists\b)", _c):
            conjuncts = conjuncts[:_i] + [" ∧ ".join(c.strip() for c in conjuncts[_i:])]
            break
    if len(conjuncts) < 2:
        return None
    return qprefix, conjuncts


def safe_iff_split(conclusion: str) -> "tuple[str, tuple[str, str]] | None":
    """SINGLE DOOR for a top-level `[∀-prefix] A ↔ B` (the SIBLING permutation of the conjunction bug — the `↔`
    path had the same missing quantifier guard). Returns (qprefix, (A, B)) with the ∀-prefix to prepend to each
    direction, or None when the body is ∃-led (shared witness — defer) or not a top-level 2-way `↔`."""
    got = strip_forall_prefix_or_defer(conclusion)
    if got is None:
        return None
    qprefix, body = got
    parts = top_level_split(body, {"↔"})
    if len(parts) != 2:
        return None
    return qprefix, (parts[0], parts[1])


def _decl_re(name: str) -> re.Pattern:
    return re.compile(_DECL_PREFIX + re.escape(name) + r"\b")


def _written_theorem_span(source: str, name: str) -> "tuple[str, int, int, int] | None":
    """Historical source-spelling lookup used by the legacy extraction API."""
    src = source or ""
    requested = (name or "").strip()
    if not src or not requested:
        return None
    scan = blank_comments(src)
    exact = _decl_re(requested).search(scan)
    if exact is None:
        return None
    next_decl = _TOPLEVEL_DECL.search(scan, exact.end())
    return (
        requested,
        scan.rfind("\n", 0, exact.start()) + 1,
        exact.end(),
        next_decl.start() if next_decl is not None else len(src),
    )


_STANDALONE_ATTRIBUTE = re.compile(r"^@\[[^\]]*\]\s*$")


def _line_indent(line: str) -> int:
    prefix = line[: len(line) - len(line.lstrip(" \t"))]
    return len(prefix.expandtabs(8))


def _is_command_boundary(visible: str) -> bool:
    return bool(
        DECL_START.match(visible)
        or DECL_TERMINATORS.match(visible)
        or _STANDALONE_ATTRIBUTE.match(visible)
    )


def _declaration_end_offset(
    lines: "list[str]",
    offsets: "list[int]",
    *,
    declaration_line: int,
    scan_from_line: int,
    total_length: int,
) -> int:
    """Find the next sibling command using Lean's offside boundary."""
    declaration_indent = _line_indent(lines[declaration_line])
    for index in range(scan_from_line, len(lines)):
        line = lines[index]
        visible = line.lstrip(" \t")
        if (
            visible.strip()
            and _line_indent(line) <= declaration_indent
            and _is_command_boundary(visible)
        ):
            # A doc comment belongs to the following command, and separator
            # whitespace belongs to neither declaration.  ``lines`` comes
            # from ``blank_comments``, so walking over blank visible lines
            # preserves both without another comment parser or offset drift.
            boundary = index
            while (
                boundary > declaration_line + 1
                and not lines[boundary - 1].strip()
            ):
                boundary -= 1
            return offsets[boundary]
    return total_length


def _scope_index(
    scan_lines: "list[str]",
) -> "tuple[list[tuple[str, ...]], list[tuple[str, str, tuple[str, ...]]]]":
    """Index namespace identity per line and return the final open scopes."""
    scopes: "list[tuple[str, str, tuple[str, ...]]]" = []
    namespace_at_line: "list[tuple[str, ...]]" = []
    active_declaration_indent: "int | None" = None
    namespace_re = re.compile(r"^namespace\s+([A-Za-z_][\w'.]*)\s*$")
    section_re = re.compile(
        r"^(?:noncomputable\s+)?section(?:\s+([A-Za-z_][\w']*))?\s*$"
    )
    end_re = re.compile(r"^end(?:\s+[A-Za-z_][\w'.]*)?\s*$")
    for line in scan_lines:
        namespace_at_line.append(tuple(
            part for kind, _name, parts in scopes
            if kind == "namespace" for part in parts
        ))
        visible = line.lstrip(" \t")
        indent = _line_indent(line)
        if active_declaration_indent is not None:
            if not (
                visible.strip()
                and indent <= active_declaration_indent
                and _is_command_boundary(visible)
            ):
                continue
            active_declaration_indent = None
        if DECL_START.match(visible):
            active_declaration_indent = indent
            continue
        command = visible.strip()
        if match := namespace_re.match(command):
            name = match.group(1)
            scopes.append(("namespace", name, tuple(name.split("."))))
        elif match := section_re.match(command):
            scopes.append(("section", match.group(1) or "", ()))
        elif command == "mutual":
            scopes.append(("mutual", "", ()))
        elif end_re.match(command) and scopes:
            scopes.pop()
    return namespace_at_line, scopes


@dataclass(frozen=True)
class ResolvedTheoremIdentity:
    """One declaration's source spelling, Lean identity, and byte boundary."""

    written_name: str
    qualified_name: str
    decl_start: int
    name_end: int
    decl_end: int

    @property
    def span(self) -> "tuple[str, int, int, int]":
        return (self.written_name, self.decl_start, self.name_end, self.decl_end)


def _theorem_identities(source: str) -> "tuple[ResolvedTheoremIdentity, ...]":
    """Enumerate declarations once, keeping spelling distinct from identity."""
    src = source or ""
    if not src:
        return ()
    scan = blank_comments(src)
    scan_lines = scan.splitlines(keepends=True)
    offsets: list[int] = []
    cursor = 0
    for line in scan_lines:
        offsets.append(cursor)
        cursor += len(line)

    # Track scopes only at command indentation. A proof-local `set_option` or
    # term-level `end` is not a namespace command. `mutual` owns its own `end`.
    namespace_at_line, _ = _scope_index(scan_lines)

    candidates: "list[ResolvedTheoremIdentity]" = []
    theorem_command = re.compile(
        r"(?m)^(?P<indent>[ \t]*)"
        + _DECL_MODS
        + r"(?P<kind>theorem|lemma)\b\s+(?P<name>[A-Za-z_][\w'.]*)"
    )
    for match in theorem_command.finditer(scan):
        written = match.group("name")
        start_line = bisect_right(offsets, match.start()) - 1
        parts = namespace_at_line[start_line]
        if written.startswith("_root_."):
            qualified = written[len("_root_."):]
        else:
            qualified = ".".join((*parts, *written.split(".")))
        name_line = bisect_right(offsets, match.end("name") - 1) - 1
        end = _declaration_end_offset(
            scan_lines,
            offsets,
            declaration_line=start_line,
            scan_from_line=name_line + 1,
            total_length=len(src),
        )
        candidates.append(ResolvedTheoremIdentity(
            written_name=written,
            qualified_name=qualified,
            decl_start=offsets[start_line],
            name_end=match.end("name"),
            decl_end=end,
        ))
    return tuple(candidates)


def resolve_theorem_target(
    source: str, selector: str
) -> "ResolvedTheoremIdentity | None":
    """Resolve one target selector without conflating spelling and identity.

    A selector may be the exact spelling returned by :func:`theorem_names` or
    the fully-qualified Lean name carried by a campaign.  If those meanings
    name different declarations, resolution fails instead of guessing.
    """
    raw = (selector or "").strip()
    if not raw:
        return None
    qualified_selector = (
        raw[len("_root_."):] if raw.startswith("_root_.") else raw
    )
    matches = {
        (row.decl_start, row.name_end, row.decl_end): row
        for row in _theorem_identities(source)
        if row.qualified_name == qualified_selector
        or (not raw.startswith("_root_.") and row.written_name == raw)
    }
    return next(iter(matches.values())) if len(matches) == 1 else None


def resolved_theorem_span(
    source: str, name: str
) -> "tuple[str, int, int, int] | None":
    """Compatibility projection: written spelling first, then unique identity."""
    legacy = _written_theorem_span(source, name)
    if legacy is not None:
        return legacy
    resolved = resolve_theorem_target(source, name)
    return resolved.span if resolved is not None else None


def _source_api_theorem_span(
    source: str, name: str
) -> "tuple[str, int, int, int] | None":
    """Preserve written-name APIs, adding qualified identity as a fallback."""
    return _written_theorem_span(source, name) or (
        resolved.span if (resolved := resolve_theorem_target(source, name)) else None
    )


def _decl_body(source: str, name: str) -> str | None:
    """The named decl's text from just AFTER `theorem <name>` up to the NEXT top-level decl (or EOF). In a
    multi-decl file this fences the decl so a following lemma's `:=`/`sorry` cannot truncate this one's
    signature or be mistaken for its proof. None if the name isn't declared. COMMENT-SAFE (2026-07-02 RCA —
    the agent's self-edited probes carry a COMMENTED echo of the substrate; the raw search matched
    `-- theorem <name>` and returned a garbage all-comment body): search + fence on the comment-BLANKED copy
    (`blank_comments` preserves offsets, so a commented decl becomes spaces and can never match) and slice the
    VERBATIM body from the original — same canonical comment door `def_names`/`section_variable_lines` use."""
    src = source or ""
    resolved = _source_api_theorem_span(src, name)
    if resolved is None:
        return None
    _, _, name_end, decl_end = resolved
    return src[name_end:decl_end]


def theorem_names(source: str) -> list[str]:
    """Every theorem/lemma name declared in the source, in order. Comments STRIPPED first (2026-07-02 audit #2 —
    mirrors `def_names`, which already did) so a commented `theorem` (even inside a `/- … -/` block) can't surface
    a phantom name; `names[-1]` is the canonical target selector + a fingerprint/cache key, so a phantom misroutes."""
    return re.findall(r"(?m)^\s*" + _DECL_PREFIX + r"([A-Za-z_][\w'.]*)", strip_comments(source or ""))


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
    src = source or ""
    scan = blank_comments(src)   # COMMENT-SAFE (mirrors _decl_body): a commented `-- def <name>` echo can't match
    m = re.compile(_DEFKIND_PREFIX + re.escape(name) + r"\b").search(scan)
    if not m:
        return None
    nxt = _TOPLEVEL_DECL.search(scan, m.end())
    return src[m.end():(nxt.start() if nxt else len(src))]


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


def strip_print_axioms_commands(text: str) -> str:
    """Remove top-level ``#print axioms`` commands, comment-safely.

    This is used when a robust positive-proof probe instead contains a named
    refutation: the positive target does not exist, and the negative theorem is
    audited separately. All other source bytes are preserved.
    """

    source_lines = (text or "").splitlines(keepends=True)
    visible_lines = blank_comments(text or "").splitlines(keepends=True)
    return "".join(
        source
        for source, visible in zip(source_lines, visible_lines, strict=True)
        if not re.match(r"^\s*#print\s+axioms\b", visible)
    )


def has_sorry(text: str) -> bool:
    """True if `sorry`/`admit` appears as code (line + NESTED block comments stripped first, so a
    `sorry` mentioned in a comment — even inside a nested comment — does not false-positive)."""
    return re.search(r"\b(?:sorry|admit)\b", strip_comments(text)) is not None


def _after_name(source: str, name: str) -> str | None:
    if not source or not name:
        return None
    resolved = _source_api_theorem_span(source, name)
    return source[resolved[2]:] if resolved else None


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


def strip_unreferenced_sorried_decls(
    text: str, *, keep: "set[str] | frozenset[str]" = frozenset()
) -> "tuple[str, list[str]]":
    """Drop open declarations that cannot contribute to this probe.

    A later work item inherits earlier declarations from its source file.  An
    unrelated earlier ``sorry`` must not poison the native probe, while a
    referenced open declaration must remain and make the probe fail closed.
    Reference reachability is conservative and comment-insensitive.
    """
    blocks = decl_blocks(text or "")
    visible = [(name, blank_comments(block)) for name, block in blocks]
    dead = [
        name
        for name, block in blocks
        if name
        and name not in keep
        and has_sorry(block)
        and not any(
            other != name and identifier_token_mentions(body, name)
            for other, body in visible
        )
    ]
    if not dead:
        return text, []
    lines = (text or "").splitlines(keepends=True)
    spans = {name: (start, end) for name, start, end in decl_spans(text or "")}
    for name in sorted(dead, key=lambda item: spans[item][0], reverse=True):
        start, end = spans[name]
        del lines[start:end]
    return "".join(lines), dead


def compile_stub(source: str, name: str) -> str:
    """A COMPILE-valid `... theorem <name> <sig> := by` taken VERBATIM from source (prelude + the
    target statement, proof swapped to `:= by`), with a single leading `import Mathlib` dropped (the
    verifier re-adds it). For native_hammer / any deterministic tactic probe. Statement is never
    reconstructed — Lean parses the original text. Assumes the target's proof is the trailing `sorry`
    (the adhoc / PutnamBench shape); returns "" if there is none.
    """
    if not source or not name:
        return ""
    text = re.sub(r"\A\s*import\s+Mathlib\s*\n+", "", source, count=1)
    resolved = _source_api_theorem_span(text, name)
    if resolved is None:
        return ""
    _, _, name_end, _ = resolved
    body = _decl_body(text, name)   # the TARGET decl only — a later lemma's sorry can't be mis-picked
    if body is None:
        return ""
    si = body.rstrip().rfind("sorry")
    if si >= 0:
        # preamble (defs/aux lemmas BEFORE the target, kept verbatim) + the target statement up to its proof
        head = (text[:name_end] + body[:si]).rstrip()
    else:
        # No trailing `sorry`: a SELF-CONTAINED probe whose agent wrote a REAL/partial proof (a namespace-wrapped
        # gale-Shapley induction, 2026-07-06). Swap that proof for `:= by` so the deterministic cascade retries ON
        # the probe's OWN theory — keeping the preamble defs (e.g. an inline `inductive ProposalRun`) that a
        # bare-goal fallback drops, stranding native_hammer with `unknown identifier` against the warm-only
        # substrate. `top_level_assign` splits sig from proof (theorem binders carry no top-level `:=`).
        ai = top_level_assign(body)
        if ai < 0:
            return ""
        head = (text[:name_end] + body[:ai]).rstrip() + " :="
    if head.endswith(":="):
        head += " by"
    elif not head.endswith(":= by"):
        return ""
    # Earlier unfinished siblings are not premises unless the surviving
    # prefix names them. Keeping an unrelated `sorry` makes the no-sorry
    # checker reject every tactic before it reaches this exact target.
    head, _ = strip_unreferenced_sorried_decls(head, keep={resolved[0]})
    if head.rstrip().endswith(":= by"):
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


def attach_proof(
    head: str,
    proof_body: str,
    *,
    proof_is_term: bool = False,
) -> str:
    """Splice `proof_body` onto a decl `head` ending `:=` or `:= by` → a compilable `theorem … := <proof>`.
    THE canonical proof-splicer — callers MUST NOT hand-roll `head + body`.

    RCA 2026-06-18 (the mathd_algebra_302 silent-drop): a local splice that stripped only `"by "` (with a
    SPACE) produced `:= by\\n  by\\n  tac` for a multiline `by\\n` body — a DOUBLE `by` that silently
    elaborates to `sorry`, so the axiom audit flags `sorryAx` and a VALID proof is rejected as a banned axiom
    (the closure is dropped). This helper is `by`-TOKEN-aware (never mistakes `by_cases`/`by_contra` for a
    `by` block), preserves the body's internal indentation VERBATIM, and never doubles `by`."""
    h = (head or "").rstrip()
    body = (proof_body or "").strip()
    if proof_is_term:
        # A carried declaration whose original body did not begin with `by`
        # already supplied a Lean term after `:=`. Preserve that declaration
        # category. Wrapping it under `by` turns constructors such as
        # `⟨leftProof, rightProof⟩` into invalid tactic syntax.
        if h.endswith(":= by"):
            h = h[:-2].rstrip()
        return (h + " " + body + "\n") if h.endswith(":=") else (h + "\n" + body + "\n")
    body_is_by_block = bool(re.match(r"by(?:\s|\Z)", body))   # `by` + whitespace/EOS, NOT `by_cases`
    if h.endswith(":= by"):
        # stub already opened the block: bare tactics go UNDER it; a body that carries its OWN `by` block
        # REPLACES the stub's `by` (drop it) so the two never double.
        return (h[:-2].rstrip() + "\n" + body + "\n") if body_is_by_block else (h + "\n  " + body + "\n")
    if h.endswith(":="):
        return (h + " " + body + "\n") if body_is_by_block else (h + " by\n  " + body + "\n")
    return h + "\n" + body + "\n"


def assemble_tactic_probe(head: str, proof_body: str) -> str:
    """Assemble one cold tactic probe without importing the whole Mathlib barrel.

    ``Mathlib.Tactic`` owns the native cascade's dependency.  The previous
    assembler injected the all-modules ``import Mathlib`` barrel; one absent,
    unrelated olean therefore made every native tactic look dead.  Exact barrel
    imports are narrowed to the tactic prelude, while every explicit source
    import is preserved.  A source that needs an additional module keeps naming
    that module; it does not acquire the entire library as hidden probe state.

    ``compile_stub`` intentionally ends at the selected declaration.  When the
    declaration lives in a namespace/section, append the corresponding closing
    commands after the proof so the exact-declaration boundary remains a valid
    Lean file rather than an unterminated prefix.
    """
    stub = (head or "").strip()
    proof = (proof_body or "").strip()
    if not stub or not proof:
        return ""
    source = attach_proof(stub, proof).rstrip()
    source = re.sub(
        r"(?m)^(?P<indent>[ \t]*)import[ \t]+Mathlib[ \t]*$",
        r"\g<indent>import Mathlib.Tactic",
        source,
    )
    imports_tactics = re.search(
        r"(?m)^\s*import\s+Mathlib\.Tactic\s*$", blank_comments(source)
    ) is not None
    if not imports_tactics:
        source = "import Mathlib.Tactic\n\n" + source
    closers = _unclosed_scope_closers(stub)
    if closers:
        source += "\n" + "\n".join(closers)
    return source + "\n"


def _unclosed_scope_closers(text: str) -> "tuple[str, ...]":
    """Return Lean ``end`` commands owed by a declaration-prefix probe."""
    _, scopes = _scope_index(blank_comments(text or "").splitlines())
    return tuple(
        f"end {name}" if name else "end"
        for _kind, name, _parts in reversed(scopes)
    )


def replace_decl_proof(
    source: str,
    target_name: str,
    proof_body: str,
    *,
    proof_is_term: bool = False,
) -> str:
    """Replace exactly one named theorem's proof, preserving every sibling.

    The target is resolved by :func:`resolve_theorem_target`, including its
    namespace identity.  This is the named counterpart to ``swap_sorry`` for
    theory files with several open declarations.  It deliberately fails
    closed when the target is absent/ambiguous or has no proof assignment.
    """
    src = source or ""
    identity = resolve_theorem_target(src, target_name)
    if identity is None or not (proof_body or "").strip():
        return ""
    decl_start, decl_end = identity.decl_start, identity.decl_end
    declaration = src[decl_start:decl_end]
    assign = top_level_assign(blank_comments(declaration))
    if assign < 0:
        return ""
    replacement = attach_proof(
        declaration[:assign].rstrip() + " :=",
        proof_body,
        proof_is_term=proof_is_term,
    ).rstrip()
    # Keep a declaration separator when the original span had one.  The
    # following bytes (next declaration / namespace terminator) remain exact.
    if declaration.endswith("\n"):
        replacement += "\n"
    return (
        src[:decl_start]
        + replacement
        + src[decl_end:]
    )


def open_decl_for_ratification(
    source: str, target_name: str
) -> "tuple[str, str]":
    """Turn one proved declaration into a governed proof candidate.

    Returns ``(source_with_target_sorry, original_proof_body)``.  Every byte
    outside the selected declaration's proof is preserved by
    :func:`replace_decl_proof`; target resolution is namespace-aware and fails
    closed on absence or ambiguity.  This is the canonical bridge from an
    already compiled artifact to the bounded carried-theorem ratifier.
    """

    identity = resolve_theorem_target(source or "", target_name)
    if identity is None:
        raise ValueError("ratification target is absent or ambiguous")
    block = (source or "")[identity.name_end:identity.decl_end]
    _signature, assigned = split_at_proof(block)
    if not assigned.startswith(":="):
        raise ValueError("ratification target has no proof assignment")
    proof_body = assigned[2:].strip()
    if not proof_body:
        raise ValueError("ratification target has an empty proof")
    if has_sorry(proof_body):
        raise ValueError("ratification target proof is already open")
    opened = replace_decl_proof(source, target_name, "by\n  sorry")
    opened_identity = resolve_theorem_target(opened, target_name) if opened else None
    opened_block = (
        opened[opened_identity.name_end:opened_identity.decl_end]
        if opened_identity is not None else None
    )
    if not opened_block or not has_sorry(opened_block):
        raise ValueError("ratification target could not be opened exactly")
    return opened, proof_body


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
    """The first theorem/lemma name anywhere in `text` (not line-anchored), or "". Comments STRIPPED first
    (2026-07-02 audit #3) so a commented `-- theorem foo` / `/- theorem foo -/` echo can't be picked as the first
    (it seeds signature extraction + the kernel-equiv `_osig`/`_asig` comparands)."""
    m = re.search(_DECL_PREFIX + r"([A-Za-z_][\w'.]*)", strip_comments(text or ""))
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


def top_level_assign(text: str) -> int:
    """Index of the `:=` at bracket depth 0 that separates a decl's signature from its proof/value (a binder
    default `(n := 0)` or a `{… := …}` structure literal is nested → ignored). -1 if none. Sibling of
    top_level_colon — used to swap a self-contained probe's REAL proof for `:= by` when there is no trailing
    `sorry` to key on (the 2026-07-06 gale-Shapley native_hammer fix)."""
    depth = 0
    pairs = {"(": ")", "[": "]", "{": "}", "⟨": "⟩", "⦃": "⦄"}
    closes = set(pairs.values())
    for i in range(len(text) - 1):
        c = text[i]
        if c in pairs:
            depth += 1
        elif c in closes:
            depth = max(0, depth - 1)
        elif depth == 0 and c == ":" and text[i + 1] == "=":
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


def _decl_body_after_assign(block: str) -> str:
    """The VALUE expression of a decl block — the text after the first top-level `:=` (a `def`/`abbrev`), or after
    ` where` (a `structure`'s fields) — comments blanked + whitespace collapsed. Comparing BODIES (not full
    signatures) makes the divergence check ignore benign binder-style differences (a substrate `def f (x)` under a
    section `variable [Inst]` vs a probe's explicit `def f {…} [Inst] (x)`) while still catching a real body change
    (`.head?` vs `.max?`). Empty for a bodyless decl (axiom/opaque) ⇒ excluded from the comparison."""
    b = blank_comments(block or "")
    if ":=" in b:
        return re.sub(r"\s+", " ", b.split(":=", 1)[1]).strip()
    if re.search(r"\bwhere\b", b):
        return re.sub(r"\s+", " ", re.split(r"\bwhere\b", b, 1)[1]).strip()
    return ""


def redeclared_defs_diverge(probe_src: str, substrate_src: str) -> "list[str]":
    """GENERAL divergence guard (2026-07-05, the recurring falsify-ghost class ONCE AND FOR ALL). A self-contained
    FALSIFY probe RE-DECLARES the theory so it can be checked in BASE Mathlib (env=None — the cure for the universe
    false-reject a self-contained probe hits against the substrate env; §warm-verify-selfcontained, KEPT INTACT:
    this guard changes NO env). But if the probe re-declares a substrate def with a DIFFERENT BODY — `bestBid=head`
    vs the substrate's `max`, or a `Book` that dropped a field — its counterexample is validated against a
    DIVERGENT theory, so a ghost that does NOT hold under the real substrate gets "confirmed" (the CLOB head-ghost).
    Compares, NAME BY NAME (short name, so a namespaced substrate decl still matches the probe's bare one), the
    BODIES of the def/structure decls the probe re-declares that the substrate ALSO declares; returns those whose
    body DIFFERS. [] when every shared re-declaration MATCHES (or the probe cites the substrate) — an IDENTICAL
    (even universe-poly) re-statement is NEVER flagged ⇒ no regression. Pure text (no env, no kernel) ⇒ can't
    universe-clash. The typeclass/binder dimension ([LT K] vs [LinearOrder K]) is the SIBLING `carrier_order_weakened`."""
    def bodies(src: str) -> "dict[str, str]":
        out: "dict[str, str]" = {}
        for name, block in decl_blocks(src or ""):
            if not name:
                continue
            # VOCABULARY only — def/abbrev/structure (mirrors `def_fingerprint`). A theorem/lemma/example body
            # LEGITIMATELY differs from the substrate's same-named one (the target is being (re)proven or is
            # `sorry`-stubbed), so comparing it would false-flag EVERY theorem the formalize gate checks against the
            # substrate (2026-07-05: the widening of the formalize firewall to `substrate_infidelities` exposed this
            # — the docstring always said "def/structure decls"; the code just never enforced the kind filter).
            low = block.lstrip()
            if not re.match(_DECL_MODS + r"(?:def|abbrev|structure)\b", low):
                continue
            short = name.rsplit(".", 1)[-1]
            if short not in out:
                out[short] = _decl_body_after_assign(block)
        return out
    sub, pro = bodies(substrate_src), bodies(probe_src)
    return [n for n, pb in pro.items() if pb and n in sub and sub[n] and pb != sub[n]]


def def_fingerprint(source: str) -> str:
    """A stable content-hash of a theory's VOCABULARY — the bodies of its `def`/`abbrev`/`structure` decls, name-
    sorted, comments/whitespace-normalized (2026-07-05, the reuse-invalidation single door). Excludes theorems/
    lemmas, so it does NOT change when the campaign banks a rung into the substrate (the cache must survive that);
    it DOES change when a meaning-bearing def is redefined (`Marketable` `∃`→decidable, `bestBid` head→max). Every
    reuse cache prepends this to its key ⇒ a rendering confirmed against one vocabulary is transparently NOT served
    against a different one (the substrate-blind-reuse root: v2's existential `Marketable` reused over v3's
    decidable one). '' for empty input. 12-hex, cheap, pure-text (no env)."""
    parts: "list[str]" = []
    for name, block in decl_blocks(source or ""):
        if not name:
            continue
        low = block.lstrip()
        if re.match(_DECL_MODS + r"(?:def|abbrev|structure)\b", low):
            parts.append(f"{name.rsplit('.', 1)[-1]}={_decl_body_after_assign(block)}")
    if not parts:
        return ""
    import hashlib as _hl
    return _hl.sha1("\n".join(sorted(parts)).encode("utf-8")).hexdigest()[:12]


def enforce_canonical_defs(probe_src: str, substrate_src: str) -> "tuple[str, list[str]]":
    """ENFORCE the substrate's CANONICAL def bodies in a self-contained probe (2026-07-05, the deep root under the
    whole CLOB session — operator "why are the fixes not enough / make the fix at once"). A self-contained probe
    re-declares the theory to be base-Mathlib-checkable, and the formalizer, given the canonical bodies only as an
    ADVISORY "reuse-verbatim" note, sometimes RE-RENDERS a def DIFFERENTLY (`Marketable` as an `∃`-existential vs
    the substrate's decidable `match`; `bestBid=head` vs `max`) — so the substrate is fixed/tractable but the PROBE
    diverges, and the proof stalls or the shelf orphans. This turns the advisory norm into a MECHANICAL guarantee:
    for every def/structure the probe re-declares that the substrate ALSO declares with a DIFFERENT body, REPLACE
    the probe's block with the substrate's CANONICAL block (verbatim). The probe stays self-contained (no env
    change) but now IS the substrate. Only shared-name divergent decls are swapped; the probe's target theorem and
    any NEW helper it introduced are untouched (agency preserved for what the formalizer actually authors). Returns
    (rewritten_src, [names swapped]). Idempotent; [] swaps ⇒ byte-identical. Retires the head/divergence/tractability
    class at the probe level (they were all faces of probe-re-render ≠ substrate)."""
    canon = {}
    for name, block in decl_blocks(substrate_src or ""):
        if name:
            canon.setdefault(name.rsplit(".", 1)[-1], block.rstrip("\n"))
    out, swapped = probe_src or "", []
    for name, block in decl_blocks(probe_src or ""):
        short = name.rsplit(".", 1)[-1] if name else ""
        cblock = canon.get(short)
        if not cblock:
            continue
        # compare BODIES (binder-style differences are benign; a real head-vs-max / ∃-vs-match body diff is not)
        if _decl_body_after_assign(block).strip() and _decl_body_after_assign(block) != _decl_body_after_assign(cblock):
            if block.rstrip("\n") in out:
                out = out.replace(block.rstrip("\n"), cblock, 1)
                swapped.append(short)
    return out, swapped


def non_reducing_defs(source: str) -> "list[str]":
    """TRACTABILITY audit (2026-07-05, CLOB `matchInto` — the `faithful ≠ tractable` DEFINITIONAL-REDUCIBILITY face,
    §arch). Flag a def that is faithful + well-typed but does NOT REDUCE — the kernel can state it, yet
    `unfold`/`simp`/`rfl` cannot open it, so even a TRIVIAL consequence won't close (CLOB v10: a `noncomputable
    matchInto := by classical; exact if …` where the trivial `if`-true lemma stalled 24 dispatches, mimicking "hard
    proof"). Signals, name-by-name: (a) `noncomputable def` (won't reduce); (b) a def body that is a `by … classical
    …` tactic-block (opaque to unfold); (c) a `… : Prop := … ∃ …` existential predicate (non-decidable ⇒ branching
    on it forces a Classical `if`). ADVISORY — sibling of `representation_dependent_defs`: `noncomputable` is
    legitimate over ℝ/measure theory, so this surfaces for the maintainer at consolidation, never gates. Cure: a
    DECIDABLE test on an `Option` + a plain COMPUTABLE `def` with a direct `if`. Returns typed flag strings, or []."""
    out: "list[str]" = []
    for name, block in decl_blocks(source or ""):
        if not name:
            continue
        header = signature_before_proof(block) or block[:400]
        body = _decl_body_after_assign(block)
        if re.search(r"(?m)^\s*(?:@\[[^\]]*\]\s*)*noncomputable\s+def\b", block):
            out.append(f"{name}: `noncomputable def` — will NOT reduce for simp/unfold; if it is an operation, "
                       f"make it a plain computable `def` with a decidable branch")
        elif re.search(r":=\s*by\b", block) and re.search(r"\bclassical\b", body):
            out.append(f"{name}: `:= by classical …` tactic-def — opaque to `unfold`/`simp`; define by a DIRECT `if` "
                       f"on a decidable test so it reduces")
        elif re.search(r":\s*Prop\b", header) and re.search(r"∃|\bExists\b", body):
            out.append(f"{name}: `Prop := … ∃ …` existential predicate — non-decidable; branching on it forces a "
                       f"Classical `if`. Make it a decidable test on an `Option` (e.g. `(opt).any (· ≤ x)`)")
    return out


def _order_classes_by_typevar(source: str) -> "dict[str, set[str]]":
    """Every instance-implicit `[ClassName typevar]` binder in `source`, grouped {typevar → {classes}}. Reused by
    both the intra-signature `redundant_subsumed_instances` sibling and the cross-file carrier comparator below.
    The class-name regex requires `Name<space>arg`, so `simp [foo]` / list literals don't match (no order/LE/LT
    hit ⇒ harmless even if a stray bracket slips through)."""
    binders = re.findall(r"\[\s*([A-Za-z_][\w'.]*)\s+([^\]\[]+?)\s*\]", source)
    by_typevar: "dict[str, set[str]]" = {}
    for cls, args in binders:
        by_typevar.setdefault(args.strip(), set()).add(cls)
    return by_typevar


def carrier_order_weakened(probe_src: str, substrate_src: str) -> "list[str]":
    """CROSS-FILE carrier-strength guard (RCA 2026-07-04, CLOB): a self-contained FALSIFY probe that RE-DECLARES
    the theory with a STRICTLY WEAKER order typeclass than the substrate commits to — bare `[LT K]`/`[LE K]`
    where the substrate has `[LinearOrder K]` (or any `*Order`). Under the weaker binders the probe can build a
    DEGENERATE `≤` (e.g. always-false) that is IMPOSSIBLE under the substrate's instance (`LinearOrder` is total),
    so its 'counterexample' does NOT refute the substrate statement — a carrier GHOST that drives a bogus
    reformulation forever. Sibling of `redundant_subsumed_instances` (that one is the INTRA-signature diamond;
    this is the probe-WEAKER-than-substrate case). Returns the weakened carriers, or [] when the probe's carriers
    are ≥ the substrate's (a GENUINE counterexample citing the real `[LinearOrder K]` passes clean). Sound &
    fail-safe: only flags a carrier the substrate declares with a rich Order class AND the probe replaced with
    bare LE/LT (never the rich order anywhere) ⇒ can't false-reject a counterexample that keeps the real order."""
    sub = _order_classes_by_typevar(substrate_src)
    pro = _order_classes_by_typevar(probe_src)
    out: "list[str]" = []
    for tv, sclasses in sub.items():
        s_order = sorted(c for c in sclasses if "order" in c.lower())      # LinearOrder / PartialOrder / *Order
        if not s_order:
            continue                                                       # substrate itself bare here — nothing below to weaken to
        pclasses = pro.get(tv, set())
        if any("order" in c.lower() for c in pclasses):
            continue                                                       # probe keeps a rich order on this carrier ⇒ not weakened
        p_bare = sorted(c for c in pclasses if c in ("LE", "LT"))
        if p_bare:                                                         # probe re-declared the carrier with ONLY bare LE/LT
            out.append(f"{tv} (substrate {s_order[0]} → probe {'+'.join(p_bare)})")
    return out


# KNOWN weakening chains (2026-07-06, OOD axis 1+3 — beyond order). STRONGEST → weakest. A probe that RE-DECLARES a
# carrier with a class strictly LOWER in a chain than the substrate's proves a DIFFERENT/weaker theorem than the
# registered one (the campaign target must match the substrate's carrier). Curated to the classes campaigns use.
_WEAKENING_CHAINS = (
    ("LinearOrder", "PartialOrder", "Preorder"),                       # order (the Preorder-bypass hole, axis 3)
    ("Field", "DivisionRing", "CommRing", "Ring", "Semiring"),         # ring / field
    ("Field", "CommRing", "CommMonoid", "Monoid"),                     # multiplicative
    ("CommGroup", "Group", "Monoid", "Semigroup"),                     # group
    ("LinearOrderedField", "LinearOrderedRing", "OrderedRing"),        # ordered algebra
    ("CommRing", "CommSemiring"),
)
def carrier_instance_weakened(probe_src: str, substrate_src: str) -> "list[str]":
    """GENERAL carrier-strength guard (2026-07-06, OOD axis 1+3 — operator "did we do all 4 via the single door?").
    Generalizes `carrier_order_weakened` PAST the order→bare-LE/LT case: a probe that RE-DECLARES a carrier (binds
    some `[Class tv]` on `tv`) with a class STRICTLY WEAKER, in a known algebra/order CHAIN, than the substrate's
    (`[Field]→[CommRing]`, `[Group]→[Monoid]`, `[LinearOrder]→[Preorder]` — the axis-3 Preorder-bypass) proves a
    DIFFERENT/weaker theorem than the registered one. CONSERVATIVE + SOUND: (i) only a RE-DECLARED carrier (probe
    binds `tv`) is checked — a probe that CITES the substrate carrier (no `tv` binder) is NEVER flagged (the
    faithful lane, cannot false-reject); (ii) only a strictly-weaker CLASS in a curated chain is flagged, NEVER a
    dropped instance — DROPPED-structural (`[DecidableEq]`/`[Fintype]`/`[Zero]`) is per-DEF, not per-carrier (a
    genuine probe legitimately omits `[Zero K]` its `cex` def never uses), so a pure-text drop check false-rejects;
    that sub-case needs a kernel "does it compile without it?" probe and stays DEFERRED (see backlog). Returns []."""
    sub = _order_classes_by_typevar(substrate_src)
    pro = _order_classes_by_typevar(probe_src)
    out: "list[str]" = []
    for tv, sclasses in sub.items():
        pclasses = pro.get(tv)
        if not pclasses:
            continue                                                       # probe cites (does not re-declare) ⇒ faithful
        for chain in _WEAKENING_CHAINS:                                    # strict chain weakening ONLY
            s_idx = min((chain.index(c) for c in sclasses if c in chain), default=None)
            if s_idx is None:
                continue
            p_strong = [chain.index(c) for c in pclasses if c in chain]
            # flag ONLY if the probe HAS a class IN THIS chain that is strictly weaker — a probe ABSENT from this
            # chain (its strength lives in a DIFFERENT/overlapping chain, e.g. `[Field]` vs a substrate `[CommRing]`
            # keyed on the CommRing/CommSemiring chain) is NOT a downgrade and must not false-flag.
            if p_strong and min(p_strong) > s_idx:
                p_have = "+".join(sorted(c for c in pclasses if c in chain))
                out.append(f"{tv} ({chain[s_idx]} → {p_have})")
                break
    return out


def substrate_infidelities(probe_src: str, substrate_src: str) -> "list[str]":
    """THE single-door "does this probe drift from the substrate?" predicate (2026-07-05, the CLOB spaghetti
    once-and-for-all). A self-contained probe (a formalized statement, a reuse seed, a falsify counterexample) is
    UNFAITHFUL to the registered substrate iff it re-declares the theory in a way that DIVERGES from the source of
    truth — along either of the two orthogonal dimensions we have found ghosts on: (a) a WEAKER carrier order
    (`[LinearOrder K]` → bare `[LT K][LE K]`, `carrier_order_weakened`); (b) a DIFFERENT def/structure BODY
    (`bestBid=head` vs `max`, a dropped field, `redeclared_defs_diverge`). Returns the union of both, each tagged
    with its dimension; [] ⇒ the probe cites or faithfully re-states the substrate. Pure text (no env, no kernel) ⇒
    cheap + universe-clash-proof. EVERY consumer that asks "is this substrate-faithful?" — the formalize firewall,
    the falsify gate, the reuse-store retrieval — calls THIS, so the three sites can never again check different
    subsets (the split-check spaghetti this replaces). [] when either input is empty/flat (⇒ byte-parity)."""
    if not (probe_src or "").strip() or not (substrate_src or "").strip():
        return []
    out = [f"carrier: {c}" for c in carrier_order_weakened(probe_src, substrate_src)]
    out += [f"carrier: {c}" for c in carrier_instance_weakened(probe_src, substrate_src)]   # OOD axis 1+3 (general)
    out += [f"def-body: {d}" for d in redeclared_defs_diverge(probe_src, substrate_src)]
    out = list(dict.fromkeys(out))   # dedup: order→LE/LT can be flagged by both carrier guards
    return out


_TRIVIAL_BODIES = {"False", "True", "true", "false", "PUnit", "Unit"}


def degenerate_redefinitions(probe_src: str, substrate_src: str) -> "list[tuple[str, str]]":
    """GRACEFUL false-as-stated signal (2026-07-06, gale capstone — operator "find a more graceful way to handle
    such things in the kernel"). The BLATANT end of the def-ghost class: a probe REDEFINES a substrate `def` to a
    TRIVIAL constant body — `BlockingPair := False` collapses `∀ m w, ¬ BlockingPair` to `∀ m w, ¬ False` = trivially
    true. A frontier model games this ONLY when it cannot prove the HONEST statement — i.e. the goal is FALSE-AS-
    STATED (a hypothesis is too weak; the prompt's design is for the leaf to instead mark `-- STATEMENT-FALSE:` with
    the corrected hypothesis, but it gamed). So a caller that catches this should not merely reject-and-grind: it
    should SURFACE 'gamed degenerate def ⇒ the target is false-as-stated ⇒ reformulate (strengthen the too-weak
    hypothesis)'. Returns [(short_name, trivial_body)] for each substrate def the probe collapsed to a bare
    triviality (differing from the substrate's real body). Pure text, SUBSET of `redeclared_defs_diverge` — [] on a
    genuine proof (no false-positive: only a body that IS a bare constant AND differs from the substrate's fires)."""
    sub_bodies: "dict[str, str]" = {}
    for name, block in decl_blocks(substrate_src or ""):
        if name and re.match(_DECL_MODS + r"(?:def|abbrev)\b", block.lstrip()):
            sub_bodies.setdefault(name.rsplit(".", 1)[-1], _decl_body_after_assign(block))
    out: "list[tuple[str, str]]" = []
    for name, block in decl_blocks(probe_src or ""):
        if not name or not re.match(_DECL_MODS + r"(?:def|abbrev)\b", block.lstrip()):
            continue
        short = name.rsplit(".", 1)[-1]
        pb = _decl_body_after_assign(block).strip()
        if pb in _TRIVIAL_BODIES and sub_bodies.get(short) and sub_bodies[short].strip() != pb:
            out.append((short, pb))
    return out


_POSITION_PRIMITIVES = (
    # position/order-DEPENDENT list extractors — a def that reads the "best"/"top"/etc. of a SET-like collection
    # through one of these is representation-dependent: its value CHANGES when the collection is reordered, so it
    # is only correct under a stored-order invariant the type does not carry (the CLOB `bestBid = bids.head?` class).
    ".head?", ".head", ".headI", ".headD", ".getLast?", ".getLast", ".getLastD", ".getLastI",
    ".get?", ".getD", ".getElem", ".take ", ".drop ", ".rotateLeft", ".rotateRight", "[0]",
)


def representation_dependent_defs(source: str) -> "list[str]":
    """FORESIGHT audit (2026-07-05, CLOB `bestBid=head` RCA — generalized). Flag each `def` whose body extracts from
    a collection via a POSITION-dependent primitive (`.head?`/`.getLast`/`.get`/`.take`/`.drop`/`[0]` …). Such a def
    is REPRESENTATION-dependent: its value changes under permutation of the collection, so it only means what the
    blueprint intended ("the highest bid", "the best", "the top") when the collection carries a stored-order
    invariant the type does NOT enforce — a faithful-but-FALSE def the firewall (target-faithfulness only) cannot
    catch. General class: position-extractor-as-"best" over any set-like structure (lists, trees, heaps, queues).
    ADVISORY (a sibling of `typeclass_generality_audit`): a def where order is GENUINELY meant (a `foldl` over an
    operation SEQUENCE, `List.headI` of a provably-sorted structure) is a benign false-positive — surfaced for the
    author to confirm, never a gate. The DETERMINISTIC cure the author reaches for is an order-independent def
    (`List.maximum`/`Finset.max'`/a fold that is provably permutation-invariant) PLUS a characterizing anchor lemma
    (§4.2a). Returns `["<def> uses <primitive> (order-dependent — permutation-variant)", …]`, or [] when clean.
    Excludes `foldl`/`foldr`/`scanl` (order there is usually the intended sequential semantics, e.g. `postOps`)."""
    src = source or ""
    scan = blank_comments(src)   # comment-safe: a commented `.head?` echo can't false-flag
    out: "list[str]" = []
    for m in re.finditer(r"(?m)^\s*(?:noncomputable\s+|private\s+|scoped\s+|@\[[^\]]*\]\s*)*def\s+([A-Za-z_][\w'.]*)",
                         scan):
        name = m.group(1)
        nxt = _TOPLEVEL_DECL.search(scan, m.end())
        decl = src[m.start():(nxt.start() if nxt else len(src))]
        # only the def's VALUE expression (after the FIRST top-level `:=`), not its signature/type — a `List` in
        # the type binder is fine; we care whether the BODY extracts by position.
        rhs = decl.split(":=", 1)[1] if ":=" in decl else decl
        for prim in _POSITION_PRIMITIVES:
            if prim in rhs:
                out.append(f"{name} uses `{prim.strip()}` (order-dependent — permutation-variant; "
                           f"if the collection is a SET, use max/min/Finset + an anchor lemma)")
                break
    return out


def partial_recursion_defs(source: str) -> "list[str]":
    """TRACTABILITY audit — RECURSION/TERMINATION face (2026-07-05 foresight; the first campaign with a genuine
    recursive engine — a matching loop, graph traversal, fixpoint — will hit this, Gemini's false-for-CLOB point
    made real). Flags a def that will NOT reduce for `simp`/`unfold`/`decide`/`rfl`: (a) `partial def` (compiles but
    has NO equation lemmas — the kernel cannot compute it, so even a trivial consequence needs a hand-rolled spec);
    (b) a def carrying `termination_by`/`decreasing_by` (well-founded recursion — total + sound, but `unfold`/`simp`
    cannot open it without its `.eq_def`/equation lemmas, so a proof that expects definitional unfolding stalls).
    ADVISORY (sibling of `non_reducing_defs`): WF recursion is legitimate — surfaced so the author adds the equation
    lemma / a structural form BEFORE the campaign spends. Returns typed flag strings, or []."""
    src = source or ""
    scan = blank_comments(src)   # comment-safe
    out: "list[str]" = []
    # `partial def` — scanned DIRECTLY off the source (its `partial` modifier is not a decl-start keyword, so
    # `decl_blocks` does not open a block for it — the same reason `representation_dependent_defs` scans directly).
    for m in re.finditer(r"(?m)^\s*(?:private\s+|scoped\s+|@\[[^\]]*\]\s*)*partial\s+def\s+([A-Za-z_][\w'.]*)", scan):
        out.append(f"{m.group(1)}: `partial def` — NO equational unfolding; the kernel can't reduce it, so even a "
                   f"trivial consequence needs a manual spec lemma. Prefer a structural/total `def`.")
    # `termination_by`/`decreasing_by` — these clauses sit inside a normal `def`'s block, so attribute via decl_blocks.
    for name, block in decl_blocks(src):
        if name and re.search(r"(?m)^\s*(?:termination_by|decreasing_by)\b", block):
            out.append(f"{name}: well-founded recursion (`termination_by`/`decreasing_by`) — total, but `unfold`/"
                       f"`simp` can't open it without equation lemmas; prove + cite `{name}.eq_def`, or use "
                       f"structural recursion so it reduces by `rfl`.")
    return out


def classical_branch_defs(source: str) -> "list[str]":
    """TRACTABILITY audit — DECIDABILITY face (2026-07-05, CLOB `matchInto`/`Marketable` generalized; foresight for
    finite-combinatorics / boolean-algebra campaigns). A def that branches with `if <P> then …` on a Prop `P` needs
    `Decidable P`; if the THEORY opens `Classical` (or uses `Classical.propDecidable`/`Classical.dec`), every such
    branch resolves via CLASSICAL decidability and is NON-REDUCING — the `if` never computes, so `unfold`/`simp`/
    `decide` cannot open the taken branch (the exact `matchInto` v10 stall). Complements `non_reducing_defs` (which
    catches it from the DEF side: `noncomputable`/`by classical`/`Prop := ∃`); THIS catches the THEORY-side enabler a
    clean-looking `def f := if P then a else b` hides behind. ADVISORY. Cure: declare an explicit `instance :
    Decidable <P>` / `DecidablePred` so the branch computes. Returns a single flag, or []."""
    scan = blank_comments(source or "")
    if (re.search(r"(?m)^\s*open\s+(?:scoped\s+)?Classical\b", scan)
            or re.search(r"\bClassical\.(?:propDecidable|dec)\b", scan)):
        return ["theory opens `Classical` / uses `Classical.propDecidable` — every `if <Prop>` resolves via "
                "classical decidability and will NOT reduce (`unfold`/`simp`/`decide` can't open the taken branch, "
                "the matchInto v10 stall); declare explicit `Decidable`/`DecidablePred` instances so branches compute"]
    return []


# THE registry every meaning-bearing single-source DEF-quality audit routes through — a new audit is ONE entry
# here and every call site (`def_quality_audit` → consolidation, tests, future gates) inherits it, so a check can
# never rot into a hand-copied sibling (the drift class). CROSS-FILE probe-vs-substrate audits
# (`carrier_order_weakened`, `redeclared_defs_diverge`) are NOT here — they take two sources and live on their own
# door; this registry is single-source `(source) -> list[str]` only.
_DEF_AUDITS = (
    ("REPRESENTATION-DEPENDENT DEF", representation_dependent_defs),
    ("NON-REDUCING DEF (faithful≠tractable)", non_reducing_defs),
    ("PARTIAL / WF-RECURSION DEF (won't reduce)", partial_recursion_defs),
    ("CLASSICAL BRANCH (non-reducing `if`)", classical_branch_defs),
)


def def_quality_audit(source: str) -> "list[tuple[str, str]]":
    """THE single door for meaning-bearing DEF-quality audits at theory consolidation. The firewall gates NL↔target
    FAITHFULNESS — not def MEANING or TRACTABILITY — so each new domain opens a new "faithful-but-X" failure surface
    (X = false / non-reducing / partial / classical-branch). Every such check is registered in `_DEF_AUDITS` and run
    HERE, returning [(category, flag), …]; adding one audit is one registry entry inherited by every caller, with no
    sibling that can drift. ADVISORY (each sub-audit is advisory) and fail-open per audit — one broken audit never
    blocks the others or consolidation."""
    out: "list[tuple[str, str]]" = []
    for cat, fn in _DEF_AUDITS:
        try:
            for flag in fn(source or ""):
                out.append((cat, flag))
        except Exception:  # noqa: BLE001 — advisory; a broken audit must not block the rest / consolidation
            continue
    return out


def _def_names_all(source: str) -> "list[str]":
    """Every `def`/`noncomputable def` name in `source` (order-preserving, dedup). Reuses the canonical decl scan."""
    names: "list[str]" = []
    for m in re.finditer(r"(?m)^\s*(?:noncomputable\s+|private\s+|scoped\s+|@\[[^\]]*\]\s*)*def\s+([A-Za-z_][\w'.]*)",
                         source):
        if m.group(1) not in names:
            names.append(m.group(1))
    return names


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
    # QUALIFIED IDENTITY + NAMED SPLICE: a campaign target is stored as `N.first`, while Lean source writes
    # `theorem first` inside `namespace N`.  Resolve that exact identity, never a same-basename sibling, and
    # replace FIRST's proof without touching either later open theorem (the orbit-action false-negative class).
    namespaced = (
        "import Mathlib\nnamespace N\n\n"
        "theorem first : True := by sorry\n\n"
        "theorem second : True := by sorry\n\n"
        "theorem third : True := by sorry\n\n"
        "end N\n"
    )
    assert extract_signature(namespaced, "N.first").strip() == ": True"
    assert compile_stub(namespaced, "N.first").rstrip().endswith("theorem first : True := by")
    assert extract_signature(namespaced, "Wrong.first") == ""       # basename alone cannot launder identity
    _ns_preamble = preamble_before_target(namespaced, "N.first")
    assert "namespace N" in _ns_preamble and "theorem first" not in _ns_preamble
    assert "theorem second" not in _ns_preamble and "theorem third" not in _ns_preamble
    _ns_work_item = source_through_target(namespaced, "N.first")
    assert "theorem first" in _ns_work_item and "theorem second" not in _ns_work_item
    _first_closed = replace_decl_proof(namespaced, "N.first", "by trivial")
    assert _first_closed and "theorem first : True := by trivial" in _first_closed
    assert strip_comments(_first_closed).count("sorry") == 2          # both siblings remain byte-separate/open
    ambiguous = (
        "namespace A\ntheorem same : True := by sorry\nend A\n"
        "namespace B\ntheorem same : True := by sorry\nend B\n"
    )
    assert resolved_theorem_span(ambiguous, "same") is not None       # legacy unqualified lookup keeps first-match
    assert resolved_theorem_span(ambiguous, "A.same") is not None
    assert resolved_theorem_span(ambiguous, "B.same") is not None
    indented = "namespace I\n  theorem spaced : True := by trivial\nend I\n"
    assert extract_signature(indented, "spaced").strip() == ": True"  # legacy indented declaration remains visible
    assert extract_signature(indented, "I.spaced").strip() == ": True"
    _identity_edge = (
        "namespace I\n@[simp]\ntheorem\n  edge : True := by\n"
        "  set_option pp.universes true in\n    trivial\nend I\n"
    )
    _edge = resolve_theorem_target(_identity_edge, "I.edge")
    assert _edge and _edge.written_name == "edge" and _edge.qualified_name == "I.edge"
    _edge_closed = replace_decl_proof(_identity_edge, "I.edge", "by trivial")
    assert _edge_closed and "set_option pp.universes" not in _edge_closed and "end I" in _edge_closed
    _selector_collision = (
        "namespace N\ntheorem A.t : True := by trivial\nend N\n"
        "namespace A\ntheorem t : True := by trivial\nend A\n"
    )
    assert resolve_theorem_target(_selector_collision, "A.t") is None
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
    # carrier_order_weakened: the CLOB carrier-ghost (probe re-declares [LinearOrder K] as bare [LT K][LE K])
    _substrate = ("def betterPrice {K : Type*} [LinearOrder K] : K → Prop := sorry\n"
                  "structure Book (K T : Type*) [Zero K] [LinearOrder K] where bids : List K")
    _ghost = ("def betterPrice {K : Type*} [LT K] : K → Prop := sorry\n"
              "def Marketable {K : Type*} [LT K] [LE K] : Prop := sorry")
    _w = carrier_order_weakened(_ghost, _substrate)
    assert any(x.startswith("K ") for x in _w), _w                    # flags K weakened LinearOrder → LT+LE
    # a GENUINE counterexample citing the real [LinearOrder K] is NOT flagged (no false-reject of a real ¬G)
    _genuine = "def cex {K : Type*} [LinearOrder K] : Prop := sorry\nexample : ¬ P := by sorry"
    assert carrier_order_weakened(_genuine, _substrate) == [], carrier_order_weakened(_genuine, _substrate)
    # a probe that doesn't mention K at all (cites substrate) is not flagged; substrate bare-carrier can't weaken
    assert carrier_order_weakened("example : True := trivial", _substrate) == []
    assert carrier_order_weakened(_ghost, "def f {K} [LT K] : Prop := sorry") == []  # substrate itself bare → nothing below
    # redeclared_defs_diverge: the CLOB head-vs-max ghost (probe re-declares bestBid=head; substrate=max)
    _sub_th = "def bestBid (book : Book) : Option K := (bidPrices book).max?\nstructure Book where\n  bids : List K"
    _ghost_pr = "def bestBid {K} (book : Book) : Option K := book.bids.head?.map (fun o => o.price)\nstructure Book where\n  bids : List K"
    assert "bestBid" in redeclared_defs_diverge(_ghost_pr, _sub_th), redeclared_defs_diverge(_ghost_pr, _sub_th)
    # an IDENTICAL re-declaration (even with a DIFFERENT binder style) is NOT flagged (no regression to the base-env fix)
    _faithful_pr = "def bestBid {K} [LinearOrder K] (book : Book) : Option K := (bidPrices book).max?"
    assert redeclared_defs_diverge(_faithful_pr, _sub_th) == [], redeclared_defs_diverge(_faithful_pr, _sub_th)
    assert redeclared_defs_diverge("def myHelper (x : K) : K := x", _sub_th) == []   # a NEW helper is not a re-declaration
    # a THEOREM target whose body (sorry / candidate proof) differs from the substrate's same-named proof is NOT a
    # def-divergence — only def/abbrev/structure VOCABULARY is compared (the 2026-07-05 formalize-gate false-positive)
    _sub_thm = "theorem restOrder_pres {book : Book} : Uncrossed book := by simp [Uncrossed]; exact absurd h hx"
    _target = "theorem restOrder_pres {book : Book} : Uncrossed book := by sorry"
    assert redeclared_defs_diverge(_target, _sub_thm) == [], redeclared_defs_diverge(_target, _sub_thm)
    assert substrate_infidelities(_target, _sub_thm) == [], substrate_infidelities(_target, _sub_thm)
    # substrate_infidelities: THE single door — unions BOTH dimensions, each site now calls only this
    assert any(x.startswith("carrier:") for x in substrate_infidelities(_ghost, _substrate))   # carrier ghost caught
    assert any(x.startswith("def-body:") for x in substrate_infidelities(_ghost_pr, _sub_th))   # def ghost caught
    assert substrate_infidelities(_genuine, _substrate) == []                          # a faithful probe passes
    assert substrate_infidelities("example : True := trivial", _substrate) == []       # a citing probe passes
    assert substrate_infidelities(_ghost, "") == [] and substrate_infidelities("", _substrate) == []  # empty ⇒ byte-parity
    # representation_dependent_defs: the CLOB bestBid=head class (order-dependent extractor over a set-like collection)
    _rep = ("def bestBid (book : Book) : Option K := book.bids.head?.map (fun o => o.price)\n"
            "def bestAsk (book : Book) : Option K := book.asks.head?.map (fun o => o.price)\n"
            "def postOps (init : Book) (ops : List Op) : Book := ops.foldl applyOp init")
    _flag = representation_dependent_defs(_rep)
    assert any(f.startswith("bestBid ") for f in _flag), _flag        # flags bestBid (head?)
    assert any(f.startswith("bestAsk ") for f in _flag), _flag        # flags bestAsk (head?)
    assert not any(f.startswith("postOps ") for f in _flag), _flag    # foldl over a SEQUENCE is NOT flagged
    # an order-INDEPENDENT max-based def is clean (no false positive)
    assert representation_dependent_defs("def bestBid (b : Book) : Option K := b.bids.map (·.price) |>.maximum?") == []
    # partial_recursion_defs: partial (no equation lemmas) + WF-recursion; clean structural def not flagged
    assert partial_recursion_defs("partial def loop (n:Nat):Nat := loop (n+1)")                     # partial → flag
    assert partial_recursion_defs("def f (n:Nat):Nat := f (n-1)\n  termination_by n")               # WF recursion → flag
    assert partial_recursion_defs("def g (n:Nat):Nat := n+1") == []                                 # structural → clean
    # classical_branch_defs: a Classical opener makes every `if <Prop>` non-reducing; a Bool `if` is clean
    assert classical_branch_defs("open Classical\ndef f (P:Prop):Nat := if P then 0 else 1")        # opener → flag
    assert classical_branch_defs("def f (b:Bool):Nat := if b then 0 else 1") == []                  # Bool if → clean
    # def_quality_audit SINGLE DOOR: one call surfaces all four faithful-but-X classes (drift guard for _DEF_AUDITS)
    _dq = def_quality_audit("open Classical\nnoncomputable def m:Nat:=0\npartial def l:Nat:=l\n"
                            "def bb (xs:List Nat):Option Nat := xs.head?")
    assert len({c for c, _ in _dq}) == 4, _dq                                                       # all 4 categories
    assert len(_DEF_AUDITS) == len({c for c, _ in _DEF_AUDITS}), "duplicate audit category in _DEF_AUDITS"
    # prop_quantifies_over_membership: the vacuity-leg candidate detector (Gemini empty-set critique)
    assert prop_quantifies_over_membership("∀ ⦃x y : X⦄, x ∈ s → y ∈ u → x ⊓ y ∈ s ∧ x ⊔ y ∈ u")  # StrongSetLE shape
    assert not prop_quantifies_over_membership("s.Nonempty ∧ ∀ ⦃x⦄, x ∈ s → True")                 # guarded
    assert not prop_quantifies_over_membership("∀ x y : X, x ⊓ y = y ⊓ x")                          # no membership
    assert not prop_quantifies_over_membership("-- ∀ x ∈ s, foo\n0")                                # comment-only ∀/∈
    _audit_probe = (
        "theorem not_target : ¬ False := by simp\n"
        "-- #print axioms keep_in_comment\n#print axioms target\n"
    )
    _audit_stripped = strip_print_axioms_commands(_audit_probe)
    assert "#print axioms target" not in _audit_stripped
    assert "-- #print axioms keep_in_comment" in _audit_stripped
    assert strip_print_axioms_commands(_audit_stripped) == _audit_stripped
    # SINGLE-DOOR conjunction/iff split guard (2026-07-01 NS-hunt RCA). Metamorphic: OLD shapes must still SPLIT
    # (no regression to filed ∀-fronted / independent conjunctions), NS existential-shared-witness shapes must
    # DEFER (None), and the ∃-INSIDE-a-conjunct case must still split (scoped witness, sound).
    assert safe_conjunction_split("A ∧ B") == ("", ["A", "B"])                                       # plain
    assert safe_conjunction_split("∀ x, A x ∧ B x ∧ C x") == ("∀ x,", ["A x", "B x", "C x"])         # ∀-fronted (distributes)
    assert safe_conjunction_split("∀ [Field F] {t : ℕ}, R t ∧ S t") == ("∀ [Field F] {t : ℕ},", ["R t", "S t"])  # instance-fronted (Shamir/BFT shape)
    assert safe_conjunction_split("(∃ w, A w) ∧ B") == ("", ["(∃ w, A w)", "B"])                     # ∃ SCOPED in a conjunct → SPLIT (sound)
    assert safe_conjunction_split("A ∧ B ∧ ∃ w, P w ∧ Q w") == ("", ["A", "B", "∃ w, P w ∧ Q w"])    # 2026-07-02 DeFi: LOOSE ∃ conjunct absorbs the rest (never orphan `Q` from its witness)
    assert safe_conjunction_split("A ∧ ∀ x, P x ∧ Q x") == ("", ["A", "∀ x, P x ∧ Q x"])             # loose ∀ conjunct WHOLE too
    assert safe_conjunction_split("∃ w, A w ∧ B w") is None                                          # NS: shared witness → DEFER
    assert safe_conjunction_split("∀ x, ∃ w, A ∧ B") is None                                         # ∀ then ∃ → DEFER
    assert safe_conjunction_split("Exists w, A w ∧ B w") is None                                     # Exists keyword → DEFER
    assert safe_conjunction_split("A ↔ B") is None and safe_conjunction_split("P x") is None         # ↔ / atomic → not a conj
    assert safe_iff_split("A ↔ B") == ("", ("A", "B"))                                               # plain iff
    assert safe_iff_split("∀ x, A x ↔ B x") == ("∀ x,", ("A x", "B x"))                              # ∀-fronted iff (distributes)
    assert safe_iff_split("∃ w, A w ↔ B w") is None                                                  # NS sibling: ∃-shared iff → DEFER
    # section_variable_lines MERGE (2026-07-05 CLOB `failed to synthesize LT T` substrate-corruption root):
    assert section_variable_lines("variable {K : Type*} [Field K]") == ["variable {K : Type*} [Field K]"]  # single ⇒ byte-parity
    _clob = section_variable_lines("variable {K T : Type*} [Zero K] [LinearOrder K]\n"
                                   "variable {K T : Type*} [Zero K] [LinearOrder K] [LT T]")
    assert _clob == ["variable {K T : Type*} [Zero K] [LinearOrder K] [LT T]"], _clob   # conflicting double ⇒ ONE union line
    _basel = section_variable_lines("section A\nvariable {K : Type*} [Field K]\nend\n"
                                    "section B\nvariable {K : Type*} [CommRing K]\nend")
    assert len(_basel) == 1 and "[Field K]" in _basel[0] and "[CommRing K]" in _basel[0], _basel   # Basel: union, Field kept
    assert len(section_variable_lines("variable {K : Type*} [Field K]\n"
                                      "variable {V : Type*} [Fintype V]")) == 2   # distinct binders NOT over-merged
    print("lean_source selftest OK")


if __name__ == "__main__":
    import sys
    if "--selftest" in sys.argv:
        _selftest()
    else:
        print(__doc__)
