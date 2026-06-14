"""Statement-integrity gate (governance, 2026-06-04).

THE GAP THIS CLOSES (found by the "any size" run): a workspace-write agent can "close" a hard target
by EDITING a definition the target depends on — e.g. adding a field `l2_approx_tendsto` to the
`MollifierFamily` structure that asserts the very conclusion, then discharging the theorem by
projecting it. The probe then compiles with ZERO sorries and ZERO extra axioms, so the kernel gate
and the matched-negative-control (which only re-checks under bare `import Mathlib`) BOTH pass — yet the
theorem is vacuously true and is NOT the theorem that was posed. This is a statement-integrity failure,
arguably worse than a `sorry` because `#print axioms` looks pristine.

THE INVARIANT: a closure is only credited if the agent's probe PRESERVED every pre-existing
declaration the target depends on — structures, defs, the other lemmas, AND the target's own SIGNATURE
(everything up to `:=`). The agent may ONLY (a) ADD new declarations (helper lemmas — that's the
legitimate compounding move) and (b) replace the target theorem's PROOF BODY (after `:=`). Modifying
or deleting any original declaration (or the target's signature) ⇒ REJECT (`statement_altered`).

Pure + dependency-light (string/decl analysis); comment- and whitespace-insensitive so benign
reformatting/comment edits don't trip it, while a changed structure field / weakened hypothesis does.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# A declaration start: optional attributes/modifiers, a decl keyword, optional name (instances may be
# anonymous). Allows LEADING WHITESPACE so namespaced/indented decls are seen (review false-closure).
_DECL_START = re.compile(
    r"^\s*(?:@\[[^\]]*\]\s*)?(?:private\s+|protected\s+|noncomputable\s+|scoped\s+|partial\s+|local\s+|unsafe\s+)*"
    r"(structure|inductive|class|def|abbrev|instance|theorem|lemma|opaque|axiom)\b\s*([A-Za-z_][\w.']*)?")
_NS_OPEN = re.compile(r"^\s*namespace\s+([A-Za-z_][\w.']*)")
_NS_END = re.compile(r"^\s*end\s+([A-Za-z_][\w.']*)\s*$")

# Instance-shadowing detection (anti-laundering). An ADDED instance providing one of these CORE
# operation/notation classes can hijack the meaning of a verbatim statement (the `+`/numeral/coercion the
# statement uses), so the proof closes a semantically-different goal while the signature text is unchanged.
_INSTANCE_HEAD = re.compile(
    r"^\s*(?:@\[[^\]]*\]\s*)?(?:private\s+|protected\s+|noncomputable\s+|scoped\s+|partial\s+|local\s+|unsafe\s+)*"
    r"instance\b")
_CORE_CLASS = re.compile(
    r"\b(HAdd|HMul|HSub|HDiv|HPow|HMod|HSMul|HShiftLeft|HShiftRight|Add|Mul|Sub|Neg|Div|Mod|Pow|SMul|"
    r"LE|LT|GE|GT|Min|Max|OfNat|OfScientific|NatCast|IntCast|RatCast|Coe|CoeTC|CoeHead|CoeTail|Membership|"
    # 2026-06-06 re-mine: decide/cardinality/proof-irrelevance + algebraic-structure hijack classes the
    # arithmetic-only set missed (an added `instance : Decidable P := isTrue …` hijacks a decide-closed
    # statement; `Subsingleton`/`Unique`/`IsEmpty` collapse via proof-irrelevance; `Zero`/`One`/… shadow
    # structure). canonical_reelaboration reuses this regex, so widening it extends the recompile backstop too.
    r"Decidable|DecidableEq|DecidablePred|Fintype|Subsingleton|Unique|IsEmpty|Nonempty|"
    r"Zero|One|Inv|Bot|Top|Preorder|PartialOrder|Lattice|CompleteLattice)\b")
# Degenerate-signature detection (statement_integrity_drift / parse-degeneracy). A `sorry`/`admit` in the
# SIGNATURE (not the body) is a sorry-TYPED non-statement; a Sort/Type-valued conclusion (binders-after-colon
# `{x:Sort}→…` parse trick) is a non-Prop. Both compile + `#print axioms` reads GREEN on nothing.
_DEGEN_SIG = re.compile(r"\b(?:sorry|admit)\b")
_SORT_CONCL = re.compile(r"^\(?\s*(?:Sort|Type)\b")


def _top_colon(sig: str) -> int:
    """Index of the binder/type-separating top-level `:` (bracket-depth 0; binder colons are nested →
    ignored). Local copy (statement_integrity must not import conjecture — that would cycle)."""
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


def _strip_comments(text: str) -> str:
    # Delegate to the ONE canonical comment scanner (nested-block + line aware). A bare
    # `re.sub(r"/-.*?-/")` is non-nested → it stops at the first `-/` and leaks the tail, producing
    # phantom decls (2026-06-13 audit). `blank_comments` space-replaces (callers `_norm`-collapse or
    # substring-check, so space-vs-remove is immaterial — and spacing keeps `a/- -/b` two tokens).
    from ztare.leanmill.lean_source import blank_comments as _bc
    return _bc(text)


def _norm(text: str) -> str:
    """Whitespace- and comment-insensitive normal form for structural comparison."""
    return re.sub(r"\s+", " ", _strip_comments(text)).strip()


def _blank_comments(text: str) -> str:
    """Replace comment regions with spaces, PRESERVING newlines/length — so decl-start detection
    never fires inside a docstring (e.g. a `/-! … the lemma that … -/` line). Nested-aware via the
    canonical `lean_source.blank_comments` (a non-nested `re.sub` registered phantom decls)."""
    from ztare.leanmill.lean_source import blank_comments as _bc
    return _bc(text)


def decl_blocks(text: str) -> "list[tuple[str, str]]":
    """NAMESPACE-QUALIFIED (name, block) pairs for every decl. Decl starts are detected on a
    comment-blanked copy (docstrings never register), with namespace nesting tracked so `A.foo` and
    `B.foo` are DISTINCT (review false-closure: dup unqualified names collapsed). Indented decls are
    seen; anonymous instances get a synthetic `<ns>.instance@<line>` name."""
    lines = text.splitlines(keepends=True)
    blines = _blank_comments(text).splitlines(keepends=True)
    ns: list[str] = []
    starts: list[tuple[int, str]] = []
    for i, ln in enumerate(blines):
        mo = _NS_OPEN.match(ln)
        if mo:
            ns.append(mo.group(1))
            continue
        me = _NS_END.match(ln)
        if me:
            if ns and ns[-1] == me.group(1):   # close a namespace (vs a named section) by match
                ns.pop()
            continue
        md = _DECL_START.match(ln)
        if md:
            nm = md.group(2) or f"instance@{i}"
            prefix = ".".join(ns)
            starts.append((i, f"{prefix}.{nm}" if prefix else nm))
    out = []
    for k, (i, name) in enumerate(starts):
        end = starts[k + 1][0] if k + 1 < len(starts) else len(lines)
        out.append((name, "".join(lines[i:end]).rstrip()))
    return out


def _signature(block: str) -> str:
    """The decl header up to the top-level `:=` (the STATEMENT); body excluded. Bracket-depth aware
    so a `:=` inside binders/terms is not mistaken for the body separator."""
    depth = 0
    pairs = {"(": ")", "[": "]", "{": "}", "⟨": "⟩", "⦃": "⦄"}
    closes = set(pairs.values())
    i = 0
    while i < len(block) - 1:
        c = block[i]
        if c in pairs:
            depth += 1
        elif c in closes:
            depth = max(0, depth - 1)
        elif depth == 0 and block[i:i + 2] == ":=":
            return block[:i]
        i += 1
    return block


@dataclass
class IntegrityVerdict:
    ok: bool
    violations: "list[str]"

    def to_dict(self) -> dict:
        return {"ok": self.ok, "violations": self.violations,
                "kind": "statement_integrity",
                "invariant": "agent may only ADD helper decls + replace the TARGET proof body; "
                             "every other original decl + the target signature must be preserved"}


def check(original_source: str, probe_source: str, target_name: str) -> IntegrityVerdict:
    """Verify the probe preserved every original declaration the target depends on. The agent may
    add new decls and replace `target_name`'s proof body; anything else is a violation."""
    orig = dict(decl_blocks(original_source))
    probe = dict(decl_blocks(probe_source))
    # the target may be namespace-qualified (e.g. `AlmostPeriodic.leaf_X`); match by exact OR suffix.
    _tgt = {n for n in orig if n == target_name or n.endswith("." + target_name)} or {target_name}
    violations: list[str] = []
    for name, oblock in orig.items():
        if name not in probe:
            violations.append(f"deleted: original decl `{name}` is missing from the probe")
            continue
        if name in _tgt:
            # only the proof BODY may change — the SIGNATURE (statement) must be preserved
            if _norm(_signature(oblock)) != _norm(_signature(probe[name])):
                violations.append(f"target_signature_altered: `{name}`'s statement was changed")
        else:
            # every OTHER original decl (structures/defs/lemmas) must be byte-identical (mod ws/comments)
            if _norm(oblock) != _norm(probe[name]):
                violations.append(f"definition_altered: original decl `{name}` was modified "
                                  "(e.g. a hypothesis/field added that weakens the target)")
    # DEGENERATE-SIGNATURE (statement_integrity_drift, MEMORY 2026-06-05 binders-after-colon): the POSED
    # target is a NON-statement — `sorry`/`admit` in the SIGNATURE (a sorry-typed type) or a Sort/Type-valued
    # conclusion (the binders-after-colon parse trick). It compiles + `#print axioms` reads GREEN on nothing.
    for _tn in _tgt:
        _blk = probe.get(_tn) or next((probe[n] for n in probe if n == _tn or n.endswith("." + _tn)), "")
        if not _blk:
            continue
        _sig = _signature(_blk)
        if _DEGEN_SIG.search(_sig):
            violations.append(f"degenerate_signature_confirmed: target `{_tn}`'s SIGNATURE contains "
                              "sorry/admit — a sorry-typed non-statement (#print axioms reads clean on nothing)")
        else:
            _j = _top_colon(_sig)
            if _j >= 0 and _SORT_CONCL.match(_norm(_sig[_j + 1:])):
                violations.append(f"degenerate_signature_confirmed: target `{_tn}`'s conclusion is "
                                  "Sort/Type-valued — a non-Prop degenerate statement, not a theorem")
    # INSTANCE-SHADOWING (2026-06-06, surfaced by the FALSIFY false-statement control): the agent may ADD
    # helper lemmas/defs, but an ADDED typeclass `instance` can SHADOW a core operation and SEMANTICALLY
    # HIJACK a VERBATIM statement — e.g. `local instance {α} : HAdd α Nat α where hAdd a _ := a` makes
    # `n + 1` elaborate to `n`, so `∀ n, n = n + 1` becomes `∀ n, n = n` and `rfl` closes it. The signature
    # diff above PASSES (statement text unchanged) and `#print axioms` stays clean — a real proof of a
    # hijacked statement. So flag any ADDED instance providing a core notation/operation class. (Added
    # instances for the agent's OWN new helper type providing a NON-core class are not flagged.)
    for name, block in probe.items():
        if name in orig:
            continue
        if _INSTANCE_HEAD.match(block) and _CORE_CLASS.search(_signature(block)):
            violations.append(f"instance_shadowing: probe ADDED a typeclass instance `{name}` providing a "
                              "CORE operation/notation class — an added instance can redefine the notation "
                              "the statement uses (semantic hijack of a verbatim statement). Added helper "
                              "lemmas/defs are allowed; core-operation instances are not.")
        # ADDED AXIOM (2026-06-06 re-mine): an `axiom` is an UNPROVEN assumption — a proof that cites an
        # added axiom is not a proof. (`#print axioms` catches a USED custom axiom, but flag the decl too.)
        elif re.match(r"^\s*(?:@\[[^\]]*\]\s*)?axiom\b", block):
            violations.append(f"added_axiom_confirmed: probe ADDED `axiom {name}` — an unproven assumption; "
                              "a closure that depends on an added axiom is laundered, not proved.")
    return IntegrityVerdict(ok=not violations, violations=violations)


def _self_test() -> int:
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    original = (
        "import Mathlib\n\n"
        "structure MollifierFamily (ι : Type) where\n"
        "  bump : ι → Nat\n"
        "  rOut_tendsto : True\n"
        "  ratio_bound : True\n\n"
        "def helper_corpus : Nat := 0\n\n"
        "theorem target (Φ : MollifierFamily ι) (h : Nat) : True := by\n"
        "  sorry\n")

    # CHEAT (the real one): agent added a field to MollifierFamily that bakes in the conclusion.
    cheat = original.replace(
        "  ratio_bound : True\n",
        "  ratio_bound : True\n  l2_approx_tendsto : True  -- baked-in conclusion\n").replace(
        "  sorry\n", "  exact Φ.l2_approx_tendsto\n")
    v = check(original, cheat, "target")
    ok("catches_structure_field_added", not v.ok and any("definition_altered" in s and "MollifierFamily" in s
                                                          for s in v.violations))

    # LEGIT: agent only ADDED a proven helper lemma + replaced the target's proof body. Allowed.
    legit = original.replace(
        "theorem target", "lemma my_new_helper : True := trivial\n\ntheorem target").replace(
        "  sorry\n", "  exact my_new_helper\n")
    v = check(original, legit, "target")
    ok("allows_added_helper_and_body_change", v.ok)

    # CHEAT: agent weakened the TARGET's own signature (dropped a hypothesis / changed statement).
    sig_cheat = original.replace("(Φ : MollifierFamily ι) (h : Nat) : True", "(h : Nat) : True").replace(
        "  sorry\n", "  trivial\n")
    v = check(original, sig_cheat, "target")
    ok("catches_target_signature_weakened", not v.ok and any("target_signature_altered" in s for s in v.violations))

    # CHEAT: agent DELETED a corpus def the statement depends on.
    del_cheat = original.replace("def helper_corpus : Nat := 0\n\n", "").replace("  sorry\n", "  trivial\n")
    v = check(original, del_cheat, "target")
    ok("catches_deleted_decl", not v.ok and any("deleted" in s for s in v.violations))

    # BENIGN: pure reformatting + comment changes on an untouched decl → NOT a violation.
    benign = original.replace("  bump : ι → Nat\n", "  bump : ι → Nat   -- the smooth bump\n").replace(
        "  sorry\n", "  trivial\n")
    v = check(original, benign, "target")
    ok("benign_comment_reformat_ok", v.ok)

    # ── INSTANCE-SHADOWING (2026-06-06, surfaced by the FALSIFY false-statement control) ──
    iorig = "import Mathlib\n\ntheorem fls : ∀ n : ℕ, n = n + 1 := by\n  sorry\n"
    # CHEAT: an ADDED `local instance` shadowing HAdd so `n+1` ≡ `n` → the FALSE verbatim statement is
    # hijacked into a true one; signature unchanged so the diff above passes. MUST be caught.
    ishadow = ("import Mathlib\n\nlocal instance {α : Type u} : HAdd α Nat α where\n  hAdd a _ := a\n\n"
               "theorem fls : ∀ n : ℕ, n = n + 1 := by\n  intro n\n  rfl\n")
    v = check(iorig, ishadow, "fls")
    ok("catches_instance_shadowing_HAdd",
       not v.ok and any("instance_shadowing" in s for s in v.violations))
    # NO FALSE-POSITIVE: an added helper LEMMA (not an instance) is allowed.
    v = check(iorig, iorig.replace("theorem fls", "lemma helper : True := trivial\n\ntheorem fls"), "fls")
    ok("instance_shadow_no_fp_on_added_lemma", v.ok)
    # NO OVER-FLAG: an added instance for a NON-core class (Inhabited) is not a notation hijack → allowed.
    v = check(iorig, iorig.replace("theorem fls", "instance : Inhabited Nat := ⟨0⟩\n\ntheorem fls"), "fls")
    ok("instance_shadow_allows_noncore_instance", v.ok)
    # 2026-06-06 re-mine: the widened _CORE_CLASS now also catches Decidable / Subsingleton instance shadows.
    dorig = "import Mathlib\n\ntheorem t : (3 : ℕ) = 3 := by\n  sorry\n"
    v = check(dorig, dorig.replace("theorem t", "instance : DecidableEq Nat := fun _ _ => isTrue (by sorry)\n\ntheorem t"), "t")
    ok("catches added DecidableEq instance (decide-hijack)",
       not v.ok and any("instance_shadowing" in s for s in v.violations))
    v = check(dorig, dorig.replace("theorem t", "instance : Subsingleton Nat := ⟨fun _ _ => by sorry⟩\n\ntheorem t"), "t")
    ok("catches added Subsingleton instance (proof-irrel collapse)",
       not v.ok and any("instance_shadowing" in s for s in v.violations))

    # ── DEGENERATE-SIGNATURE (binders-after-colon / in-signature-sorry parse-degeneracy) ──
    deg = "import Mathlib\n\ntheorem t : {x : Sort u} → {n : x} → sorry := fun _ _ => trivial\n"
    v = check(deg, deg, "t")   # orig==probe ⇒ signature-altered cannot fire; only the degeneracy leg can
    ok("catches sorry-in-signature (binders-after-colon non-statement)",
       not v.ok and any("degenerate_signature" in s for s in v.violations))
    deg2 = "import Mathlib\n\ntheorem t : Sort 1 := PUnit\n"
    ok("catches Sort/Type-valued conclusion (non-Prop)",
       not check(deg2, deg2, "t").ok)
    leg = "import Mathlib\n\ntheorem t : 2 + 2 = 4 := by norm_num\n"
    ok("normal Prop statement passes (no degenerate false-positive)", check(leg, leg, "t").ok)

    # ── REGRESSION: cold-review confirmed false-closures (namespaced/indented/anonymous) ──
    # (a) indented decl inside a namespace, both helper AND target altered → MUST catch.
    o = "import Mathlib\nnamespace N\n  def trap : Nat := 0\n  theorem target : trap = 0 := by sorry\nend N\n"
    p = "import Mathlib\nnamespace N\n  def trap : Nat := 1\n  theorem target : trap = 1 := by\n  rfl\nend N\n"
    v = check(o, p, "target")
    ok("catches_namespaced_indented_alteration", not v.ok)
    # (b) duplicate unqualified name across namespaces; only A.foo changed → MUST catch.
    o2 = "namespace A\ntheorem foo : True := trivial\nend A\nnamespace B\ntheorem foo : True := trivial\nend B\ntheorem target : True := by sorry\n"
    p2 = "namespace A\ntheorem foo : True := by trivial\nend A\nnamespace B\ntheorem foo : True := by exact True.intro\nend B\ntheorem target : True := trivial\n"
    v = check(o2, p2, "target")
    ok("namespace_dup_not_collapsed", "A.foo" in {n for n in dict(decl_blocks(o2))})
    # (c) anonymous instance altered → MUST catch (gets a synthetic name, compared).
    o3 = "instance : Inhabited Nat where default := 1\ntheorem target : (default : Nat) = 1 := by sorry\n"
    p3 = "instance : Inhabited Nat where default := 0\ntheorem target : (default : Nat) = 1 := by rfl\n"
    v = check(o3, p3, "target")
    ok("catches_anonymous_instance_alteration", not v.ok)

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
