"""v33_consequence_exposure_gate.py — Tier-0 closure-governance organ.

Sibling of the v33 anti-laundering organs (vacuity / gold-name /
single-lemma-exact / indirect-leakage). Object is DISTINCT from all of
them: those inspect the proof TERM / goal shape; this parses the claimed
proof_closure theorem's SIGNATURE BINDERS and flags a closure that
smuggles the hard target in as an assumed hypothesis
(`theorem cert (h : HardTarget …) … : Goal`) — "consequence: assumed"
mislabeled as proof_closure.

GP-188 Q3 v3.1. Verified-open class: `ns_governance_gate.py:90-107`
routes proof_closure purely on `_run_v33`; no organ parses binders vs a
hard-target set, so this case is unhandled. Pure-parse (no Lean
elaborator) — kernel `isDefEq` would only be needed for the explicitly
PARKED Fork-A library-chain residual (a hard target reached via a
pre-existing *library* definitional chain not present in the submitted
file); that is out of scope here and NOT claimed.

Must-fixes from the v3 balanced review, all applied:
  MF1  step-2 head extraction descends a fixed transparent-wrapper
       allowlist (Fact/Subtype/{//}/Nonempty/PLift/ULift/id/Squash/
       Trunc/instance-binder/∀→strict-positive-tail) AFTER file-local
       delta/structure closure, BEFORE the hard-target-head test.
  MF2  locus is lean_proof_gate (only runs for
       substrate_class==lean_proof); an unparseable / theorem-less
       lean_proof submission ⇒ confirmed LAUNDERED (fail-closed), never
       skipped. NOT_APPLICABLE cannot arise at this locus by
       construction.
  MF3  the strictly-weaker-wrapper exclusion uses a witness-
       non-triviality test (`∃ _:Unit, X` / `PLift X` ≡ X, NOT weaker;
       `Nonempty X` / `Trunc X` ARE weaker). `hard_target_heads` is
       substrate-supplied (sidecar, see _load_hard_target_heads) and
       NARROW; default empty ⇒ the BLOCKING rule is inert (advisory
       only) — the correct staged-blocking posture (never false-FAIL).

Return contract mirrors the sibling organs:
  detect_shape(src) -> {
    "consequence_exposure_suspect": bool,   # any signal at all
    "blocking": bool,                       # in hard_target_heads
    "smuggled_heads": [...], "advisory_goalhead": bool,
    "binders": [...], "reason": str,
  }
The aggregator adds `consequence_exposure_confirmed` (blocking) or
`consequence_exposure_shape_suspect_advisory`.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

ORGAN_ID = "v33-consequence-exposure"

# Transparent wrappers whose head is NOT the semantic content — descend
# through them before head extraction (MF1). These preserve logical
# content (`Fact X`, `Subtype`/`{x // p x}`, `PLift/ULift X`, `id X`,
# `Squash X` for proofs) OR are the binder spine (`∀ … → T`).
_TRANSPARENT_HEADS = {
    "Fact", "PLift", "ULift", "id", "Squash", "Subtype",
}
# Strictly-WEAKER wrappers: assuming `W X` is weaker than assuming `X`,
# so it is NOT smuggling the hard target (MF3). Witness-non-triviality:
# a wrapper is weaker only if it genuinely drops content.
_WEAKER_HEADS = {"Nonempty", "Trunc", "Truncated"}

_TRIVIAL_WITNESS_TYPES = {"Unit", "True", "PUnit", "Empty.{0}"}

_IDENT = r"[A-Za-z_][A-Za-z0-9_'.]*"


def _load_hard_target_heads() -> list[str]:
    """Substrate-supplied, NARROW (MF3). One head name per line in a
    sidecar; absent ⇒ [] ⇒ blocking rule inert (advisory-only, the
    correct staged-blocking default — never false-FAIL)."""
    side = Path(__file__).with_name("v33_hard_target_heads.txt")
    if not side.exists():
        return []
    out = []
    for ln in side.read_text(encoding="utf-8", errors="ignore").splitlines():
        ln = ln.split("#", 1)[0].strip()
        if ln:
            out.append(ln)
    return out


def _strip_comments(src: str) -> str:
    src = re.sub(r"/-.*?-/", " ", src, flags=re.S)
    src = re.sub(r"--[^\n]*", " ", src)
    return src


def _file_local_delta_map(src: str) -> dict[str, set[str]]:
    """name -> set of constant heads it expands to, transitive fixpoint
    over the submitted file's OWN abbrev/def/structure (MF1, finite
    pure-parse — no elaborator). For `structure S … where f : T …`
    every field type head is an expansion of S (projecting a field
    yields the hard target)."""
    raw: dict[str, set[str]] = {}
    # abbrev / def / notation : RHS captured DOTALL up to the next
    # top-level decl (FIX 2026-05-16 gap#3: the old single-line `(.+)`
    # missed `def Reg (u) :=\n  HardTarget u` ⇒ rename-evasion).
    for m in re.finditer(
        rf"\b(?:abbrev|def|notation)\s+({_IDENT})\b(.*?)"
        rf"(?=\n\b(?:theorem|lemma|def|abbrev|structure|notation|instance)\b|\Z)",
        src, flags=re.S,
    ):
        name = m.group(1)
        rhs = m.group(2)[:800]
        raw.setdefault(name, set()).update(re.findall(_IDENT, rhs))
    # structure : every field type head
    for sm in re.finditer(
        rf"\bstructure\s+({_IDENT})\b.*?\bwhere\b(.*?)(?=\n\S|\Z)", src, flags=re.S
    ):
        name = sm.group(1)
        body = sm.group(2)
        heads: set[str] = set()
        for fm in re.finditer(rf":\s*([^\n]+)", body):
            heads.update(re.findall(_IDENT, fm.group(1)))
        raw.setdefault(name, set()).update(heads)
    # transitive closure (bounded — finite decl set)
    for _ in range(len(raw) + 1):
        changed = False
        for k, vs in raw.items():
            add: set[str] = set()
            for v in list(vs):
                if v in raw and v != k:
                    add |= raw[v]
            if not add <= vs:
                vs |= add
                changed = True
        if not changed:
            break
    return raw


def _split_signature(thm: str) -> tuple[list[str], str] | None:
    """(binder_type_strings, conclusion) for a `theorem/lemma name … :
    Goal := …`. Returns None if unparseable (caller treats None on a
    lean_proof submission as fail-closed — MF2)."""
    m = re.search(rf"\b(?:theorem|lemma)\s+{_IDENT}\b", thm)
    if not m:
        return None
    rest = thm[m.end():]
    # MFa FIX (2026-05-16, FLAWED-impl-review): body-cut MUST be
    # depth-aware. Naive rest.find(":=") false-cut on a default-arg
    # binder `(n : ℕ := 0)` ⇒ sig mis-parse ⇒ false-FAIL on a LEGIT
    # theorem. Single depth pass: collect (...){...}[...] binders; at
    # depth-0 ':' the conclusion starts; the conclusion ends at the
    # first depth-0 ':=' OR a depth-0 ' by '/'\nby' (proof body) —
    # default-arg ':=' lives at depth>0 and is correctly ignored.
    binders: list[str] = []
    depth = 0
    cur = ""
    concl = None
    i = 0
    n = len(rest)
    while i < n:
        c = rest[i]
        if c in "([{":
            depth += 1
            cur += c
        elif c in ")]}":
            depth -= 1
            cur += c
            if depth == 0:
                binders.append(cur.strip())
                cur = ""
        elif depth == 0 and c == ":" and rest[i:i+2] != ":=":
            concl = rest[i + 1:]
            break
        elif depth == 0 and rest[i:i+2] == ":=":
            break  # proof body before any conclusion ':' — malformed
        else:
            cur += c
        i += 1
    if concl is None:
        return None
    # trim the proof body off the conclusion at depth-0 ':=' / ' by '
    cdepth = 0
    j = 0
    cn = len(concl)
    while j < cn:
        ch = concl[j]
        if ch in "([{":
            cdepth += 1
        elif ch in ")]}":
            cdepth -= 1
        elif cdepth == 0 and concl[j:j+2] == ":=":
            concl = concl[:j]
            break
        elif cdepth == 0 and (concl[j:j+4] == " by " or concl[j:j+4] == "\nby " or concl[j:j+5] == "\n  by"):
            concl = concl[:j]
            break
        j += 1
    concl = concl.strip()
    if not concl:
        return None
    btypes: list[str] = []
    for b in binders:
        inner = b[1:-1] if b and b[0] in "([{" else b
        # `name … : T`  (instance binders may be anonymous: `[T]`)
        if ":" in inner:
            btypes.append(inner.split(":", 1)[1].strip())
        elif b.startswith("["):
            btypes.append(inner.strip())
    return btypes, concl


def _proof_body(thm: str) -> str:
    """Text AFTER the depth-0 signature terminator (`:=`/` by `) — the
    proof body that _split_signature deliberately discards. Needed for
    the S6 duplication-arm scan (re-review #2): a `sorry`-backed
    have/let/suffices/show of the hard target is invisible to a
    signature-only check."""
    m = re.search(rf"\b(?:theorem|lemma)\s+{_IDENT}\b", thm)
    if not m:
        return ""
    rest = thm[m.end():]
    depth = 0
    i = 0
    n = len(rest)
    seen_concl = False
    while i < n:
        c = rest[i]
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif depth == 0 and c == ":" and rest[i:i+2] != ":=":
            seen_concl = True
        elif depth == 0 and seen_concl and rest[i:i+2] == ":=":
            return rest[i + 2:]
        elif depth == 0 and seen_concl and (rest[i:i+4] == " by "
                or rest[i:i+4] == "\nby " or rest[i:i+5] == "\n  by"):
            return rest[i:]
        i += 1
    return ""


# S6 (re-review #2 + #3): a have/let/suffices/show/obtain/rcases of the
# hard target backed by sorry/admit/stop = the canonical "states AND
# assumes the target" duplication-arm. Gate on an unfinished-proof token
# so a legitimately PROVED `have` is never false-FAILed (preserves 0
# benign false-positive — re-verified each round). Three clause shapes:
#   C1 named colon form  : have/let/suffices/replace/obtain/rcases/show
#                          ⟨..⟩|name(binders) : T   (binder parens tolerated, rr#5)
#   C2 colon-less tactic : show/change/suffices T  (no `name :` — rr#3/#4)
#   C3 term-ascription   : (by sorry : T)  (have h := (..) — re-review #3)
#   C4 type-application  : @id|f (T) (by sorry)   (re-review #4)
#   C5 anon-ctor ascript : (⟨by sorry⟩ : T)        (re-review #5)
#   C6 let rec / where   : let rec|where aux (v) : T := by sorry  (rr#5)
# Over-capture is harmless: every captured type still passes through
# _closed_head + _hits, so only a real hard-target head is ever flagged.
_DUP_CLAUSES = [
    re.compile(
        r"\b(?:have|let|suffices|replace|obtain|rcases|show)\b\s*"
        r"(?:⟨[^⟩]*⟩|\w+(?:\s*\([^)]*\))*)?\s*:\s*(.+?)"
        r"(?:\s*:=|\s+by\b|\s+from\b|\n|$)", flags=re.S),
    re.compile(
        r"\b(?:show|change|suffices)\b\s+(.+?)"
        r"(?:\s+by\b|\s+from\b|\s*:=|\n|$)", flags=re.S),
    re.compile(
        r"\(\s*by\b[^()]*?\b(?:sorry|admit|stop)\b[^():]*:\s*([^()]+?)\)",
        flags=re.S),
    re.compile(
        r"\(\s*([^()]+?)\s*\)\s*\(\s*by\b[^()]*?"
        r"\b(?:sorry|admit|stop)\b[^()]*\)", flags=re.S),
    re.compile(
        r"\(\s*⟨[^⟩]*\b(?:sorry|admit|stop)\b[^⟩]*⟩\s*:\s*([^()]+?)\)",
        flags=re.S),
    re.compile(
        r"\b(?:let\s+rec|where)\b\s+\w+[^:=\n]*?:\s*(.+?)"
        r"(?:\s*:=|\s+by\b|\n|$)", flags=re.S),
    # C7 (rr#5 Fix B): generic `name (binders)* : T := by … sorry`
    # clause — catches EVERY aux in a multi-aux where/let-rec block
    # (C6 only bound the first). Over-capture vs C1 is harmless
    # (gated on _UNFINISHED + every capture re-checked by _closed_head).
    re.compile(
        r"\b\w+\s*(?:\([^)]*\))*\s*:\s*([^:=\n]+?)\s*:=\s*"
        r"by\b[^\n]*?\b(?:sorry|admit|stop)\b", flags=re.S),
]
_UNFINISHED = re.compile(r"\b(?:sorry|admit|stop)\b")

# Fix C2 (rr#5): a top-level `instance … : <target> … := by sorry` or
# `instance … : <target> where … sorry` ASSUMES a hard target via an
# unfinished body; an automated/adversarial prover could `inferInstance`
# it into a claimed theorem row. group(1)=instance type, group(2)=body
# region up to the next top-level decl.
_INSTANCE_DECL = re.compile(
    r"\binstance\b\s*(?:[^:({\[\n]|\([^)]*\)|\{[^}]*\}|\[[^\]]*\])*?"
    r":\s*([^:=\n]+?)\s*(?::=|\bwhere\b|\bby\b)(.*?)"
    r"(?=\n\b(?:instance|theorem|lemma|def|abbrev|structure)\b|\Z)",
    flags=re.S)

# FN2 (re-review #6): a `def foo : <target> := by sorry` promoted to an
# instance via a SEPARATE `attribute [instance] foo` (or `@[instance]
# def foo …`) is inferInstance-reachable and laundered, yet bears no
# `instance` keyword. Collect promoted names, then check their def.
# Hole 1 (re-review #7): `attribute [instance] bar foo` promotes a
# WHOLE list — capture the rest of the line; the caller splits idents.
_ATTR_INSTANCE = re.compile(
    r"attribute\s*\[\s*[^\]]*\binstance\b[^\]]*\]\s*([^\n]+)")
_IDENT_LIST = re.compile(r"[A-Za-z_][\w.]*")
_AT_INSTANCE_DEF = re.compile(
    r"@\[\s*[^\]]*\binstance\b[^\]]*\]\s*(?:noncomputable\s+|private\s+|"
    r"protected\s+)*def\s+([A-Za-z_][\w.]*)")


def _peel(t: str) -> str:
    """Descend transparent wrappers + ∀→ spine to the semantic head
    (MF1). Returns '' if the type is a strictly-weaker wrapper of a
    non-trivial witness (MF3) — i.e. NOT smuggling."""
    t = t.strip()
    for _ in range(12):
        t = t.strip()
        # whole-wrapper paren strip only (unbalanced lstrip/rstrip was
        # unsound) — strip outer () iff they wrap the entire term.
        if t[:1] == "(" and t[-1:] == ")":
            d = 0
            whole = True
            for k, ch in enumerate(t):
                d += (ch in "([{") - (ch in ")]}")
                if d == 0 and k != len(t) - 1:
                    whole = False
                    break
            if whole:
                t = t[1:-1].strip()
                continue
        # ∀ x …, : recurse into the strict-positive tail
        ma = re.match(r"∀[^,]*,(.*)$", t, flags=re.S)
        if ma:
            t = ma.group(1).strip()
            continue
        # FIX (2026-05-16 retrospective-audit, C03): logical-arrow split
        # MUST be depth-aware AND must NOT fire on bundled-hom notation
        # (`→L[`, `→+`, `→ₗ[`, `→*`, `→ₐ`, `≃L`, …). The old
        # `re.search("->|→")` grabbed the FIRST `→` anywhere — incl. the
        # one inside `E →L[ℝ] E` and inside argument parens — mis-peeling
        # a continuous-linear-map TYPE to a spurious head ⇒ false
        # advisory_goalhead. A logical arrow = depth-0 `→`/`->` whose
        # next non-space char is a space/`(`/`∀`/`¬`/`{`/identifier-LETTER
        # but NOT a hom decorator glued to it (L,+,ₗ,*,ₐ,o,C,ᵇ,₊,₀ …).
        d = 0
        cut = None
        alen = 0
        i2 = 0
        is_hom = False
        while i2 < len(t):
            c = t[i2]
            if c in "([{":
                d += 1
            elif c in ")]}":
                d -= 1
            elif d == 0 and c == "≃":
                # rr#10 FP fix: a STANDALONE bundled-equiv infix
                # (`≃`, `≃L`, `≃ₗ`, `≃ₐ`, `≃+*`, `≃o`, `≃*`, `≃+`)
                # with NO preceding `→` is a map/iso TYPE, not an
                # assumption of the target proposition — same as the
                # post-arrow hom decorator. Top connective ⇒ is_hom.
                is_hom = True
                i2 += 1
                continue
            elif d == 0 and (c == "→" or t[i2:i2+2] == "->"):
                aln = 1 if c == "→" else 2
                nxt = t[i2+aln:i2+aln+1]
                # bundled-hom: `→` glued to a morphism decorator/bracket
                if nxt and (nxt in "L+*oC[ₗₐᵇ₊₀ₓ" or nxt == "≃"):
                    is_hom = True
                    i2 += aln
                    continue
                cut, alen = i2, aln
                break
            i2 += 1
        if cut is not None:
            t = t[cut + alen:].strip()
            continue
        # rr#8 FP fix (symmetric half of rr#7 Hole3): if the TOP
        # connective is a bundled hom (a depth-0 decorator was skipped
        # and NO logical arrow follows), this is a MAP type involving
        # the target, NOT an assumption of the target proposition —
        # in ANY position (binder / antecedent / conclusion). Yield no
        # smuggle head. (A nested hom at depth>0 leaves is_hom False so
        # the real outer head is still extracted.)
        if is_hom:
            return ""
        # FIX (2026-05-16 re-review #2, S15): anonymous subtype / set-
        # builder has NO leading identifier (`{x // p x}`, `{x | p x}`)
        # so the _IDENT early-return below let a Subtype-wrapped hard
        # target escape. Recurse into the predicate body BEFORE that.
        if t[:1] == "{":
            mb = (re.match(r"\{[^/|]*//\s*(.+)\}\s*$", t, flags=re.S)
                  or re.match(r"\{[^|/]*\|\s*(.+)\}\s*$", t, flags=re.S))
            if mb:
                t = mb.group(1).strip()
                continue
            return t
        hm = re.match(rf"({_IDENT})", t)
        if not hm:
            return t
        head = hm.group(1)
        # MFc FIX (2026-05-16): wrapper-membership on the LAST dotted
        # component so `Mathlib.X.Fact` / `_root_.Fact` / `Nonempty`
        # qualified forms still descend/exclude correctly.
        simple = head.split(".")[-1]
        args = t[hm.end():].strip()
        if simple in _WEAKER_HEADS:
            return ""  # strictly weaker ⇒ not the hard target (MF3)
        if simple == "Exists" or head == "Exists":  # `∃ w : W, body`
            wm = re.search(r":\s*([^,]+),", t)
            wt = wm.group(1).strip() if wm else ""
            if wt and wt not in _TRIVIAL_WITNESS_TYPES:
                return ""   # non-trivial witness ⇒ genuinely weaker (MF3)
            bm = re.search(r",\s*(.+)$", t)
            t = bm.group(1) if bm else t
            continue
        if simple in _TRANSPARENT_HEADS or simple == "Subtype":
            inner = re.search(r"\{[^/]*//\s*([^}]+)\}", t)  # {x // p x}
            if inner:
                t = inner.group(1).strip()
                continue
            if simple == "Subtype" and args:
                # FIX (2026-05-16 re-review #2, S15): `Subtype (fun x =>
                # P x)` / `Subtype (· … )` keyword form — peel the
                # lambda body, not the `fun` head.
                a = args.strip()
                if a[:1] == "(" and a[-1:] == ")":
                    a = a[1:-1].strip()
                lm = re.match(r"fun\s+[^=]*=>\s*(.+)$", a, flags=re.S)
                if lm:
                    t = lm.group(1).strip()
                    continue
                t = a
                continue
            if args:
                t = args.strip()
                continue
            return head
        return head
    return t


def _hits(name: str, targets: set[str]) -> bool:
    """Namespace-tolerant target match (MFc): full + last dotted
    component, both directions."""
    if not name:
        return False
    s = name.split(".")[-1]
    if name in targets or s in targets:
        return True
    return any(t.split(".")[-1] == s for t in targets)


def _closed_head(t: str, delta: dict[str, set[str]],
                  targets: set[str]) -> tuple[str, bool]:
    """Peeled head + whether file-local delta closure of it hits a
    hard-target head (namespace-tolerant)."""
    h = _peel(t)
    if not h:
        return "", False
    if _hits(h, targets):
        return h, True
    if h in delta and any(_hits(x, targets) for x in delta[h]):
        return h, True
    return h, False


def _ant_type(raw: str) -> str:
    """FN1 (re-review #6): a conclusion antecedent may be a NAMED binder
    `(hyp : T) → Goal` — semantically identical to the plain `T → Goal`
    smuggle but `_peel` would stop at the binder name `hyp`. Strip
    whole-wrapper parens, then return the post-(depth-0)-colon type so a
    named-arrow antecedent is matched exactly like a plain one. A
    paren-free or colon-free antecedent is returned unchanged (prior
    behavior; non-target / weaker forms stay non-blocking)."""
    s = raw.strip()
    while s[:1] == "(" and s[-1:] == ")":
        d = 0
        whole = True
        for k, ch in enumerate(s):
            d += (ch in "([{") - (ch in ")]}")
            if d == 0 and k != len(s) - 1:
                whole = False
                break
        if whole:
            s = s[1:-1].strip()
        else:
            break
    d = 0
    for i, ch in enumerate(s):
        if ch in "([{":
            d += 1
        elif ch in ")]}":
            d -= 1
        elif d == 0 and ch == ":" and s[i:i+2] != ":=":
            return s[i + 1:].strip()
    return s


def _concl_parts(concl: str) -> tuple[list[str], str]:
    """gap#1 FIX: a conclusion `A → B → … → Goal` / `∀ (h:T), Rest`
    smuggles via its ANTECEDENTS exactly as a binder `(h:A)` does.
    Returns (antecedent_type_strings, final_goal). Depth-aware."""
    ants: list[str] = []
    t = (concl or "").strip()
    for _ in range(24):
        t = t.strip()
        if t[:1] == "(" and t[-1:] == ")":
            d = 0
            whole = True
            for k, ch in enumerate(t):
                d += (ch in "([{") - (ch in ")]}")
                if d == 0 and k != len(t) - 1:
                    whole = False
                    break
            if whole:
                t = t[1:-1].strip()
                continue
        mall = re.match(r"∀\s*(.+?),\s*(.+)$", t, flags=re.S)
        if mall:
            b = mall.group(1).strip()
            if ":" in b:
                ants.append(b.split(":", 1)[1].strip().strip("()[]{}"))
            t = mall.group(2).strip()
            continue
        d = 0
        cut = -1
        alen = 0
        k = 0
        while k < len(t):
            ch = t[k]
            if ch in "([{":
                d += 1
            elif ch in ")]}":
                d -= 1
            elif d == 0 and (ch == "→" or t[k:k+2] == "->"):
                # Hole 3 (re-review #7): mirror the _peel bundled-hom
                # guard — a `→` glued to a morphism decorator (`→L[`,
                # `→+`, `→ₗ`, `→*`, `→ₐ`, `≃`) is NOT a logical arrow;
                # splitting it false-FAILs a genuinely-proved theorem
                # whose CONCLUSION is a bundled hom (`target →L[ℝ] F`).
                aln = 1 if ch == "→" else 2
                nxt = t[k + aln:k + aln + 1]
                if nxt and (nxt in "L+*oC[ₗₐᵇ₊₀ₓ" or nxt == "≃"):
                    k += aln
                    continue
                cut, alen = k, aln
                break
            k += 1
        if cut != -1:
            ants.append(_ant_type(t[:cut]))   # FN1: named-arrow binder type
            t = t[cut + alen:].strip()
            continue
        break
    return ants, t


def detect_shape(lean_source: str,
                  hard_target_heads: list[str] | None = None) -> dict[str, Any]:
    targets = set(hard_target_heads if hard_target_heads is not None
                  else _load_hard_target_heads())
    src = _strip_comments(lean_source or "")
    out: dict[str, Any] = {
        "consequence_exposure_suspect": False, "blocking": False,
        "smuggled_heads": [], "advisory_goalhead": False,
        "binders": [], "reason": "", "organ": ORGAN_ID,
    }
    # MFb FIX (2026-05-16, FLAWED-impl-review): blocking MUST be gated on
    # a non-empty hard-target set. With no sidecar (targets==∅) the organ
    # is advisory-ONLY by design — the fail-closed branches must NOT
    # block the live loop (a no-theorem / unparseable legit file would
    # else false-FAIL every inert-mode tick). `_blk = bool(targets)`:
    # fail-closed is enforced only when an operator opted into a
    # hard-target enforcement set; otherwise surfaced advisory.
    _blk = bool(targets)
    thms = list(re.finditer(
        rf"\b(?:theorem|lemma)\s+{_IDENT}\b.*?(?=\n\b(?:theorem|lemma|def|abbrev|structure)\b|\Z)",
        src, flags=re.S))
    if not thms:
        out.update(consequence_exposure_suspect=True, blocking=_blk,
                   reason="no theorem/lemma declaration in a lean_proof "
                          "submission (fail-closed, MF2; blocking only "
                          "when a hard-target set is supplied)")
        return out
    delta = _file_local_delta_map(src)
    # gap#2 FIX: scan EVERY top-level theorem, not just the last —
    # appending a trivial clean theorem after a shim must NOT mask it.
    smuggled: list[str] = []
    goalhead = False
    all_binders: list[str] = []
    unparseable = False
    for tm in thms:
        sig = _split_signature(tm.group(0))
        if sig is None:
            unparseable = True
            continue
        btypes, concl = sig
        all_binders.extend(btypes)
        ants, goal = _concl_parts(concl)        # gap#1: conclusion ∀/→ antecedents
        concl_head = _peel(goal)
        for bt in list(btypes) + ants:          # binders AND conclusion antecedents
            h, hit = _closed_head(bt, delta, targets)
            if hit:
                smuggled.append(h)
            if h and concl_head and h == concl_head:
                goalhead = True
        # S6 duplication-arm: scan the proof BODY for a hard-target
        # assumption backed by sorry/admit/stop across all clause shapes
        # C1/C2/C3 (re-review #2 + #3).
        body = _proof_body(tm.group(0))
        if body and _UNFINISHED.search(body):
            # Fix A (re-review #5, CRITICAL): bare claim-and-sorry — the
            # conclusion head IS a supplied hard target and the proof is
            # unfinished. The most basic laundering shape; previously the
            # conclusion head only fed advisory_goalhead, never blocking.
            # Cannot false-FAIL: a real proof has no sorry/admit/stop in
            # body so _UNFINISHED is False.
            gh, ghit = _closed_head(goal, delta, targets)
            if ghit:
                smuggled.append(gh)
            for _pat in _DUP_CLAUSES:
                for dm in _pat.finditer(body):
                    cap = dm.group(1).strip()
                    dh, dhit = _closed_head(cap, delta, targets)
                    if dhit:
                        smuggled.append(dh)
                    # Fix C1 (re-review #5): a sorry-backed
                    # `have h : Target → Goal` smuggles via the
                    # captured type's antecedent, not its head.
                    c_ants, _c_goal = _concl_parts(cap)
                    for _a in c_ants:
                        ah, ahit = _closed_head(_a, delta, targets)
                        if ahit:
                            smuggled.append(ah)
    # FN2 (rr#6) + Hole1/2 (rr#7) + rr#8: defs promoted to instances via
    # attribute / @[instance] / a bare or wrapped `instance … := <expr>`
    # alias, including TYPELESS alias chains terminating in sorry.
    def _def_body(nm: str):
        m = re.search(
            rf"\bdef\s+{re.escape(nm)}\b[^:\n]*?:\s*([^:=\n]+?)\s*:=(.*?)"
            rf"(?=\n\b(?:instance|theorem|lemma|def|abbrev|structure|"
            rf"attribute)\b|\Z)", src, flags=re.S)
        if m:
            return m.group(1).strip(), m.group(2) or ""
        m2 = re.search(
            rf"\bdef\s+{re.escape(nm)}\b[^:=\n]*?:=(.*?)"
            rf"(?=\n\b(?:instance|theorem|lemma|def|abbrev|structure|"
            rf"attribute)\b|\Z)", src, flags=re.S)
        if m2:
            return None, m2.group(1) or ""           # typeless alias
        return None, None

    def _alias_ident(expr: str):
        # rr#9 fix: prefix-strip / outer-paren-unwrap / trailing depth-0
        # `: T` ascription-strip must iterate together to a FIXPOINT —
        # running the `by exact` strip ONCE before the paren loop leaked
        # `(by exact foo : T)` / `((by exact foo))` (head grabbed `by`).
        b = (expr or "").strip()
        for _ in range(12):
            prev = b
            b = re.sub(r"^@?by\s+exact\s+", "", b)
            b = re.sub(r"^@?by\s+", "", b)
            # rr#10 FN fix: transparent term wrappers — `show T from x`
            # ⇒ x ; a leading `id`/`@id` application head ⇒ its arg.
            b = re.sub(r"^show\b.*?\bfrom\b\s*", "", b, flags=re.S)
            b = re.sub(r"^@?id\s+", "", b)
            if b[:1] == "(" and b[-1:] == ")":
                d = 0
                whole = True
                for k, ch in enumerate(b):
                    d += (ch in "([{") - (ch in ")]}")
                    if d == 0 and k != len(b) - 1:
                        whole = False
                        break
                if whole:
                    b = b[1:-1].strip()
            d = 0
            for i, ch in enumerate(b):
                d += (ch in "([{") - (ch in ")]}")
                if d == 0 and ch == ":" and b[i:i+2] != ":=":
                    b = b[:i].strip()
                    break
            if b == prev:
                break
        # HEAD identifier of a (possibly applied) alias body: `bar u`
        # aliases to `bar`. Only LOCAL defs are followed downstream and
        # the chain only flags on a terminal sorry, so taking the head
        # never over-promotes a benign chain.
        m = re.match(r"@?([A-Za-z_][\w.]*)", b)
        return m.group(1) if m else None

    def _chain_unfinished(nm: str, seen=None, depth=0) -> bool:
        if seen is None:
            seen = set()
        if nm in seen or depth > 8:
            return False
        seen.add(nm)
        _ty, body = _def_body(nm)
        if body is None:
            return False
        if _UNFINISHED.search(body):
            return True
        nxt = _alias_ident(body)
        return bool(nxt and nxt != nm
                    and _chain_unfinished(nxt, seen, depth + 1))

    def _chain_head(nm: str, seen=None, depth=0):
        """First hard-target head along an alias chain — from a node's
        declared type OR an inline `(… : T)` ascription. Lets a TYPELESS
        promoted def (`@[instance] def g := (by exact foo : T)`) still
        bind to the target via the chain (rr#9 attribute-path)."""
        if seen is None:
            seen = set()
        if nm in seen or depth > 8:
            return None
        seen.add(nm)
        ty, body = _def_body(nm)
        if body is None:
            return None
        if ty:
            h, hit = _closed_head(ty, delta, targets)
            if hit:
                return h
        masc = re.search(r":\s*([^():=\n]+?)\s*\)", body)   # inline ascription
        if masc:
            h, hit = _closed_head(masc.group(1).strip(), delta, targets)
            if hit:
                return h
        nxt = _alias_ident(body)
        if nxt and nxt != nm:
            return _chain_head(nxt, seen, depth + 1)
        return None

    promoted: set[str] = set(_AT_INSTANCE_DEF.findall(src))
    for g in _ATTR_INSTANCE.findall(src):           # Hole1: whole name list
        promoted.update(_IDENT_LIST.findall(g))
    for im in _INSTANCE_DECL.finditer(src):
        ity, ibody = im.group(1).strip(), (im.group(2) or "")
        ih, ihit = _closed_head(ity, delta, targets)
        if not ihit:
            continue
        if _UNFINISHED.search(ibody):               # Fix C2 (rr#5)
            smuggled.append(ih)
            continue
        # rr#8: instance type hits target and its body aliases (bare,
        # `(foo)`, `by exact foo`, or a typeless chain) to an
        # unfinished def ⇒ laundered regardless of that def's own type.
        al = _alias_ident(ibody)
        if al and _chain_unfinished(al):
            smuggled.append(ih)
    for nm in promoted:                              # FN2: attr/@[instance]
        if _chain_unfinished(nm):                    # incl. typeless chains
            hd = _chain_head(nm)                      # type via chain/ascription
            if hd:
                smuggled.append(hd)
    out["binders"] = all_binders
    if unparseable and not smuggled:
        out.update(consequence_exposure_suspect=True, blocking=_blk,
                   reason="a claimed-closure signature is unparseable in "
                          "a lean_proof submission (fail-closed, MF2; "
                          "blocking only when a hard-target set is supplied)")
        return out
    if smuggled:
        out.update(consequence_exposure_suspect=True, blocking=_blk,
                   smuggled_heads=sorted(set(smuggled)),
                   reason=f"a claimed proof_closure assumes hard-target "
                          f"head(s) {sorted(set(smuggled))} as a hypothesis "
                          f"binder OR conclusion antecedent (after "
                          f"file-local delta closure) — consequence:assumed "
                          f"mislabeled as closure"
                          + ("" if _blk else " [advisory: no hard-target "
                             "set supplied — surfaced, not blocking]"))
    elif goalhead:
        # Advisory-FOREVER (never blocking): induction / well-founded /
        # mutual / strictly-weaker-instance make a blocking rule here
        # unsound. Surface only.
        out.update(consequence_exposure_suspect=True,
                   advisory_goalhead=True,
                   reason="a conclusion head also appears as a hypothesis "
                          "head — advisory only (induction/well-founded/"
                          "mutual/weaker-instance are legitimate; never "
                          "blocking)")
    return out


if __name__ == "__main__":  # self-smoke incl. FLAWED-impl-review controls
    import json, sys
    T = ["GlobalRegularity"]
    # (name, src, hard_target_heads, expect_blocking, expect_suspect)
    cases = [
        # --- should BLOCK (smuggle, targets supplied) ---
        ("smuggle_direct", "theorem c (h : GlobalRegularity u) : Goal := by exact f h", T, True, True),
        ("smuggle_abbrev", "abbrev Reg (u) := GlobalRegularity u\ntheorem c (h : Reg u) : Goal := by exact f h", T, True, True),
        ("smuggle_def_multiline", "def Reg (u) :=\n  GlobalRegularity u\ntheorem c (h : Reg u) : Goal := by exact f h", T, True, True),  # gap#3
        ("smuggle_struct", "structure RS (u) where reg : GlobalRegularity u\ntheorem c (h : RS u) : Goal := h.reg", T, True, True),
        ("smuggle_fact_ns", "theorem c [hf : _root_.Fact (GlobalRegularity u)] : Goal := by exact g hf.out", T, True, True),  # MFc
        ("smuggle_concl_arrow", "theorem c : GlobalRegularity u → Goal := by exact f", T, True, True),  # gap#1
        ("smuggle_then_clean", "theorem shim (h : GlobalRegularity u) : Goal := h\ntheorem clean (x:Nat) : x = x := rfl", T, True, True),  # gap#2
        # --- re-review #2 (must-fix S6 duplication-arm: body scan) ---
        ("dup_arm_have_sorry", "theorem mine (u) : GlobalRegularity u := by have h : GlobalRegularity u := by sorry; exact h", T, True, True),
        ("dup_arm_let_sorry", "theorem mine (u) : Goal := by let h : GlobalRegularity u := sorry; exact h", T, True, True),
        ("dup_arm_suffices_sorry", "theorem mine (u) : Goal := by suffices h : GlobalRegularity u by exact h\n  sorry", T, True, True),
        # --- re-review #3 (colon-less / alternate sorry-backed forms) ---
        ("dup_arm_show_sorry", "theorem mine (u) : Goal := by show GlobalRegularity u\n  sorry", T, True, True),
        ("dup_arm_show_from_sorry", "theorem mine (u) : Goal := by show GlobalRegularity u from by sorry", T, True, True),
        ("dup_arm_change_sorry", "theorem mine (u) : Goal := by change GlobalRegularity u\n  sorry", T, True, True),
        ("dup_arm_term_ascription", "theorem mine (u) : Goal := by have h := (by sorry : GlobalRegularity u); exact h", T, True, True),
        ("dup_arm_obtain_sorry", "theorem mine (u) : Goal := by obtain ⟨h⟩ : GlobalRegularity u := by sorry\n  exact h", T, True, True),
        ("benign_show_nontarget_sorry", "theorem c (u) : Goal := by show Foo u\n  have z : Bar := by sorry\n  exact z", T, False, False),
        # --- re-review #4 (replace / colon-less suffices / type-application) ---
        ("dup_arm_replace_sorry", "theorem mine (u) : Goal := by replace h : GlobalRegularity u := by sorry\n  exact h", T, True, True),
        ("dup_arm_suffices_from_sorry", "theorem mine (u) : Goal := by suffices GlobalRegularity u from foo\n  sorry", T, True, True),
        ("dup_arm_suffices_by_sorry", "theorem mine (u) : Goal := by suffices GlobalRegularity u by exact foo\n  sorry", T, True, True),
        ("dup_arm_id_app_sorry", "theorem mine (u) : Goal := by have := @id (GlobalRegularity u) (by sorry); exact this", T, True, True),
        # --- re-review #5 (anon-ctor ascription / let rec / where) ---
        ("dup_arm_anonctor_sorry", "theorem mine (u) : Goal := by have h := (⟨by sorry⟩ : GlobalRegularity u); exact h", T, True, True),
        ("dup_arm_let_rec_sorry", "theorem mine (u) : Goal := by\n  let rec aux (v) : GlobalRegularity v := by sorry\n  exact aux u", T, True, True),
        ("dup_arm_where_sorry", "theorem mine (u) : Goal := by exact aux u\nwhere aux (v) : GlobalRegularity v := by sorry", T, True, True),
        ("benign_where_proved", "theorem c (u) : Goal := by exact aux u\nwhere aux (v) : Nat := 0", T, False, False),
        # --- re-review #5b (bare claim-and-sorry / multi-aux / arrow-ant / instance) ---
        ("bare_claim_by_sorry", "theorem mine (u) : GlobalRegularity u := by sorry", T, True, True),
        ("bare_claim_term_sorry", "theorem mine (u) : GlobalRegularity u := sorry", T, True, True),
        ("bare_claim_admit", "theorem mine (u) : GlobalRegularity u := by admit", T, True, True),
        ("where_multi_aux_sorry", "theorem mine (u) : Goal := by exact b u\nwhere\n  a (v) : Nat := 0\n  b (v) : GlobalRegularity v := by sorry", T, True, True),
        ("have_arrow_antecedent_sorry", "theorem mine (u) : Goal := by have h : GlobalRegularity u → Goal := by sorry\n  exact h (by sorry)", T, True, True),
        ("instance_target_sorry", "instance inst (u) : GlobalRegularity u := by sorry\ntheorem mine (u) : Goal := by exact f inferInstance", T, True, True),
        ("instance_where_sorry", "instance (u) : GlobalRegularity u where proof := by sorry\ntheorem mine (u) : Goal := f inferInstance", T, True, True),
        # --- re-review #6 (FN1 named-arrow antecedent / FN2 attribute-instance) ---
        ("named_arrow_antecedent", "theorem t (u) : (hyp : GlobalRegularity u) → Goal := fun h => f h", T, True, True),
        ("named_arrow_nontarget", "theorem t (u) : (hyp : Foo u) → Goal := fun h => f h", T, False, False),
        ("named_arrow_weaker", "theorem t (u) : (h : Nonempty (GlobalRegularity u)) → Goal := fun h => k h", T, False, False),
        ("attr_instance_sorry", "def foo (u) : GlobalRegularity u := by sorry\nattribute [instance] foo\ntheorem mine (u) : Goal := f inferInstance", T, True, True),
        ("at_instance_def_sorry", "@[instance] def foo (u) : GlobalRegularity u := by sorry\ntheorem mine (u) : Goal := f inferInstance", T, True, True),
        ("attr_instance_proved", "def foo (u) : GlobalRegularity u := real_proof u\nattribute [instance] foo\ntheorem mine (u) : Goal := f inferInstance", T, False, False),
        # --- re-review #7 (Hole1 multiname attr / Hole2 instance-alias / Hole3 concl bundled-hom FP) ---
        ("attr_instance_multiname", "def bar (u) : Q := by trivial\ndef foo (u) : GlobalRegularity u := by sorry\nattribute [instance] bar foo\ntheorem mine (u) : Goal := f inferInstance", T, True, True),
        ("instance_alias_sorry_def", "def foo (u) : GlobalRegularity u := by sorry\ninstance : GlobalRegularity u := foo\ntheorem mine (u) : Goal := f inferInstance", T, True, True),
        ("instance_alias_proved", "def foo (u) : GlobalRegularity u := real_proof u\ninstance : GlobalRegularity u := foo\ntheorem mine (u) : Goal := f inferInstance", T, False, False),
        # --- re-review #8 (hom-in-hyp/ant FP symmetric ; instance-alias-chain FN) ---
        ("hyp_bundled_hom_proved", "theorem t (u) (g : GlobalRegularity u →L[ℝ] F) : Goal := by exact h g", T, False, False),
        ("ant_bundled_hom_proved", "theorem t (u) : (GlobalRegularity u →L[ℝ] F) → Goal := by exact fun g => h g", T, False, False),
        ("inst_alias_paren_sorry", "def foo (u) : GlobalRegularity u := by sorry\ninstance : GlobalRegularity u := (foo)\ntheorem mine (u) : Goal := f inferInstance", T, True, True),
        ("inst_alias_byexact_sorry", "def foo (u) : GlobalRegularity u := by sorry\ninstance : GlobalRegularity u := by exact foo\ntheorem mine (u) : Goal := f inferInstance", T, True, True),
        ("inst_alias_typeless_chain_sorry", "def bar (u) := by sorry\ndef foo (u) := bar u\ninstance : GlobalRegularity u := foo\ntheorem mine (u) : Goal := f inferInstance", T, True, True),
        ("inst_alias_typeless_chain_proved", "def bar (u) := real u\ndef foo (u) := bar u\ninstance : GlobalRegularity u := foo\ntheorem mine (u) : Goal := f inferInstance", T, False, False),
        # --- re-review #9 (parenthesized by-exact alias family + attr typeless chain) ---
        ("inst_paren_byexact_asc_sorry", "def foo (u) : GlobalRegularity u := by sorry\ninstance : GlobalRegularity u := (by exact foo : GlobalRegularity u)\ntheorem mine (u) : Goal := f inferInstance", T, True, True),
        ("inst_paren_byexact_sorry", "def foo (u) : GlobalRegularity u := by sorry\ninstance : GlobalRegularity u := (by exact foo)\ntheorem mine (u) : Goal := f inferInstance", T, True, True),
        ("inst_dbl_paren_byexact_sorry", "def foo (u) : GlobalRegularity u := by sorry\ninstance : GlobalRegularity u := ((by exact foo))\ntheorem mine (u) : Goal := f inferInstance", T, True, True),
        ("inst_byexact_inner_paren_sorry", "def foo (u) : GlobalRegularity u := by sorry\ninstance : GlobalRegularity u := (by exact (foo))\ntheorem mine (u) : Goal := f inferInstance", T, True, True),
        ("at_instance_typeless_byexact_sorry", "def foo (u) : GlobalRegularity u := by sorry\n@[instance] def g (u) := (by exact foo : GlobalRegularity u)\ntheorem mine (u) : Goal := f inferInstance", T, True, True),
        ("attr_instance_typeless_chain_sorry", "def foo (u) : GlobalRegularity u := by sorry\ndef g (u) := (by exact foo)\nattribute [instance] g\ntheorem mine (u) : Goal := f inferInstance", T, True, True),
        ("inst_paren_byexact_proved", "def foo (u) : GlobalRegularity u := real u\ninstance : GlobalRegularity u := (by exact foo : GlobalRegularity u)\ntheorem mine (u) : Goal := f inferInstance", T, False, False),
        # --- re-review #10 (standalone ≃-family FP ; show-from / id FN) ---
        ("hyp_equiv_proved", "theorem t (u) (g : GlobalRegularity u ≃ F) : Goal := by exact h g", T, False, False),
        ("hyp_equivL_proved", "theorem t (u) (g : GlobalRegularity u ≃L[ℝ] F) : Goal := by exact h g", T, False, False),
        ("ant_equiv_proved", "theorem t (u) : (GlobalRegularity u ≃ F) → Goal := fun g => h g", T, False, False),
        ("concl_equiv_proved", "theorem t (u) : GlobalRegularity u ≃ F := by exact e", T, False, False),
        ("inst_show_from_sorry", "def foo (u) : GlobalRegularity u := by sorry\ninstance : GlobalRegularity u := show GlobalRegularity u from foo\ntheorem mine (u) : Goal := f inferInstance", T, True, True),
        ("inst_byexact_id_sorry", "def foo (u) : GlobalRegularity u := by sorry\ninstance : GlobalRegularity u := by exact id foo\ntheorem mine (u) : Goal := f inferInstance", T, True, True),
        ("inst_show_from_proved", "def foo (u) : GlobalRegularity u := real u\ninstance : GlobalRegularity u := show GlobalRegularity u from foo\ntheorem mine (u) : Goal := f inferInstance", T, False, False),
        ("concl_bundled_hom_proved", "theorem t (u) : GlobalRegularity u →L[ℝ] F := by exact lin", T, False, False),
        ("concl_bundled_hom_plus_proved", "theorem t (u) : GlobalRegularity u →+ F := by exact m", T, False, False),
        ("benign_prove_target_real", "theorem t (u) : GlobalRegularity u := real_proof u", T, False, False),
        ("benign_instance_proved", "instance inst (u) : GlobalRegularity u := real_proof u\ntheorem t (u) : Goal := f inferInstance", T, False, False),
        # --- re-review #2 (must-fix S15 anonymous-subtype peel) ---
        ("subtype_brace_smuggle", "theorem c (h : {x // GlobalRegularity x}) : Goal := by sorry", T, True, True),
        ("subtype_fun_smuggle", "theorem c (h : Subtype (fun x => GlobalRegularity x)) : Goal := by sorry", T, True, True),
        # --- re-review #2 benign body-scan controls (must NOT block) ---
        ("legit_have_proved", "theorem c (u) : Goal := by have h : GlobalRegularity u := real_proof u\n  exact f h", T, False, False),
        ("sorry_nontarget_noblock", "theorem c (u) : Goal := by have h : Foo u := by sorry\n  exact h", T, False, False),
        # --- must NOT block (false-FAIL regression controls) ---
        ("default_arg_legit_emptyT", "theorem c (n : Nat := 0) (h : 0 < n) : n ≤ n := le_refl n", [], False, False),  # MFa+MFb
        ("default_arg_legit_withT", "theorem c (n : Nat := 0) (h : 0 < n) : n ≤ n := le_refl n", T, False, False),  # MFa
        ("no_theorem_emptyT", "def foo := 1  -- no theorem", [], False, True),  # MFb: advisory, NOT block
        ("no_theorem_withT", "def foo := 1  -- no theorem", T, True, True),  # MF2 still enforces when targets set
        ("weaker_nonempty", "theorem c (h : Nonempty (GlobalRegularity u)) : Goal := by exact k h", T, False, False),  # MF3
        ("legit_induction", "theorem c (ih : ∀ k, k < n → P k) : P n := by exact step ih", T, False, True),  # advisory_goalhead only
        ("clean", "theorem c (hx : 0 < x) : x ≤ x*x ∨ True := by simp", T, False, False),
    ]
    fails = 0
    for nm, s, th, eb, es in cases:
        r = detect_shape(s, hard_target_heads=th)
        ok = (r["blocking"] == eb) and (r["consequence_exposure_suspect"] == es)
        if not ok:
            fails += 1
        print(("OK  " if ok else "FAIL") + f" {nm:26s} block={r['blocking']}"
              f"(exp {eb}) suspect={r['consequence_exposure_suspect']}(exp {es})"
              f" smug={r['smuggled_heads']}")
    print(f"\n{len(cases)-fails}/{len(cases)} self-smoke pass")
    sys.exit(1 if fails else 0)
