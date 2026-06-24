"""Global proof cache — the COMPRESS + SCALE leg of the general proof-search engine.

A verified lemma is a COMPRESSED reusable node: it collapses an entire search subtree
into one citable fact. This cache is the growing, deduplicated, PERSISTENT library of
those facts — shared across the search, across target rows, and across substrates
(SCALE: a lemma proved once is free everywhere, the documented shared-memory speedup).

Substrate-agnostic: keys are normalized statement strings; values are verified proof
bodies. No Lean, no LLM, no substrate specifics — the search injects what it verifies.

Keying: statements are normalized (decl-name- and whitespace-agnostic) so the SAME
mathematical statement hits regardless of the local name the prover gave it. Only
KERNEL-VERIFIED proofs are ever cached — the cache never holds an unratified claim
(it is downstream of the proposes/ratifies boundary, never a bypass of it).
"""
from __future__ import annotations
import json
import os
import re
from pathlib import Path

# Strip the leading `theorem/lemma <name>` so `theorem foo : P` and `theorem bar : P`
# (same statement, different local name) collapse to one key.
_NAME_RE = re.compile(r"^\s*(?:theorem|lemma)\s+[A-Za-z_][\w'.]*")
_WS_RE = re.compile(r"\s+")


def normalize_statement(statement: str) -> str:
    # CANONICAL-STATEMENT KEY (2026-06-19 amnesia RCA): the cache was keyed on the ENRICHED probe — `import
    # Mathlib` + per-run `-- candidate premises (semantic shelf…)` comments + the theorem — so the SAME lemma
    # drifted to a NEW key every run (17 keys for one `iso_lemma1`) and reuse NEVER fired. Strip the comments
    # (per-run premise noise) and the import header (preamble, not the statement) FIRST, so the enriched stored
    # key and a clean `goal` lookup canonicalize to the same decl. Soundness unchanged: an over-collapse is only
    # ever closed after an in-context re-verify (cache_verify), so it is a re-verify miss, never a false closure.
    from ztare.leanmill.lean_source import signature_before_proof, strip_comments, theorem_names, extract_signature
    s = strip_comments(statement or "")
    s = re.sub(r"(?m)^\s*(import|open|set_option|variable)\b.*$", "", s)   # drop preamble lines, not the claim
    # MULTI-DECL TARGET (2026-06-24, the cache-never-hits RCA): a `define_then_state` probe inlines `def`/`abbrev`s
    # BEFORE the theorem (every theory-building campaign does this). `signature_before_proof` cuts at the FIRST
    # top-level `:=` — which is the LEADING abbrev's body assignment — so the key became that abbrev's signature
    # (`abbrev ClaimSchedule (ι : Type*)`), IDENTICAL across every probe sharing a first def and never matching a
    # bare-target-theorem goal lookup → reuse NEVER fired for multi-decl probes. Key on the TARGET theorem (the
    # LAST theorem/lemma) via the canonical extractor — the same single-door rule as `statement_fingerprint`.
    _tn = theorem_names(s)
    if _tn:
        _sig = extract_signature(s, _tn[-1])
        if (_sig or "").strip():
            s = _sig
    s = _NAME_RE.sub("theorem _", s.strip())
    # FORMAT-UNIFY (2026-06-19): a BARE signature (e.g. `_extract_target_signature` → `(n:Nat) … : G`, no decl
    # head) must key IDENTICALLY to the full `theorem name … : G := …` the cache stores — else (b)/governed
    # cache lookups with a derived goal MISS a banked full-theorem proof (the residual amnesia leak). Give a
    # head-less signature the same `theorem _` head so both canonicalize to one key.
    if not re.match(r"(?:theorem|lemma|def|abbrev|example|instance|structure|inductive)\b", s):
        s = "theorem _ " + s
    s = signature_before_proof(s)              # drop the proof `:=` body, BINDER-SAFE (not first `:=`,
    return _WS_RE.sub(" ", s).strip()          # which truncated a `let k := 5` hypothesis — same key bug)


# --- EQUIVALENCE-keyed normalization (default OFF; ZTARE_LEANMILL_EQUIV_CACHE=1) -----------------
# The covering-space-quotient lever: cache by proof-EQUIVALENCE, not exact text, so structurally
# identical goals that differ only in bound-variable NAMES (α-equivalence) collapse to one key —
# turning reuse into reach (collapse equivalent subgoals), not just speed. SAFE BY CONSTRUCTION: a
# cache hit is RE-VERIFIED in-context before it can close anything (governed_dag_search.cache_verify),
# so an over-broad α-collapse that doesn't actually port is just a cache MISS, never a false closure.
# Conservative: only α-renames binder-introduced identifiers; everything else is unchanged.
#
# UNIT-ECONOMICS (the "execution trap"): computing TRUE semantic/definitional proof-state
# equivalence needs the kernel and would cost as much as (or more than) just running the proof step —
# which would drag the loop to a halt. We do NOT do that. This is a PURELY SYNTACTIC normal form
# (one full-string re.sub per DISTINCT binder ⇒ O(n_distinct_binders × len); sub-ms for real Lean
# statements with a handful of binders, and a binder-count guard below falls back to the plain key on
# a pathological input so it can never go quadratic-slow): the normalized string IS the hash key; no
# kernel, no elaboration, no API call. So it
# can never cost more than a proof step. The price is reach: it catches only syntactic (α / whitespace
# / name) equivalence, NOT definitional unfolding. That is the right trade — the re-verify guards
# correctness on the hits we DO get, and missed deeper-equivalences are just missed cache hits (no
# harm). If we ever want deeper equivalence, the only economics-safe source is the goal term Lean
# ALREADY elaborates as a byproduct of attempt setup (hash that) — never a dedicated equivalence call.
_BINDER_AFTER = re.compile(r"(?:∀|∃|Σ|Π|λ|\bfun\b)\s+([A-Za-z_][\w']*(?:\s+[A-Za-z_][\w']*)*)")
_BINDER_PAREN = re.compile(r"\(\s*([A-Za-z_][\w']*(?:\s+[A-Za-z_][\w']*)*)\s*:")


def normalize_statement_equiv(statement: str) -> str:
    """α-equivalence-aware key: bound variables renamed to canonical positional names (b0, b1, …)
    by first appearance, so `∀ x, P x` and `∀ y, P y` collapse. Built on `normalize_statement`."""
    s = normalize_statement(statement)
    order: list[str] = []
    for rgx in (_BINDER_AFTER, _BINDER_PAREN):
        for m in rgx.finditer(s):
            for tok in m.group(1).split():
                if tok and tok not in order:
                    order.append(tok)
    if not order:
        return s
    if len(order) > 64:   # economics guard: a pathological binder count → fall back to the plain key
        return s
    placeholder = {nm: f"\x00{i}\x00" for i, nm in enumerate(order)}
    # longest names first so a short name can't clobber a longer one's substring
    for nm in sorted(order, key=len, reverse=True):
        s = re.sub(r"(?<![\w'])" + re.escape(nm) + r"(?![\w'])", placeholder[nm], s)
    return re.sub(r"\x00(\d+)\x00", lambda m: f"b{m.group(1)}", s)


def _key_for(statement: str) -> str:
    """Cache key: α-equivalence-collapsed (DEFAULT-ON 2026-06-19; `ZTARE_LEANMILL_EQUIV_CACHE=0` reverts to
    exact). SOUND by construction: an equiv hit is only ever CLOSED after an in-context re-verify
    (`governed_dag_search.cache_verify` / the agentic `_cache_reuse` short-circuit), so an over-broad
    α-collapse is just a re-verify miss, never a false closure. Flipped default-on because the EXACT key was
    binder-name-sensitive — `iso_lemma1 (hsplit …)` and the banked `iso_lemma_split (hnum …)` got different
    keys → the planner re-derived banked rungs from scratch (the 2026-06-19 amnesia RCA)."""
    if os.environ.get("ZTARE_LEANMILL_EQUIV_CACHE", "1") != "0":
        return normalize_statement_equiv(statement)
    return normalize_statement(statement)


class ProofCache:
    """Persistent JSONL-backed cache of {normalized statement -> verified proof}.

    Append-only on disk (an audit trail of every cached proof); deduped in memory on
    the normalized key (first verified proof wins; later identical statements reuse it).
    """

    def __init__(self, path: "str | Path"):
        self.path = Path(path)
        self._mem: dict[str, dict] = {}
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                    # RE-KEY ON LOAD (2026-06-19): the on-disk text `key` was computed in whatever EQUIV mode was
                    # active at write time; recompute from the stored `statement` under the CURRENT mode so a
                    # default flip (exact→equiv) doesn't orphan every banked entry.
                    # DUAL-INDEX (2026-06-24): a canonical `H:`-prefixed `Expr.hash` key is PRESERVED as-is (a text
                    # re-key would orphan it), AND the entry is ALSO indexed under its text key so a no-REPL / text
                    # lookup still hits. So an entry is reachable by either key.
                    _stored = r.get("key") or ""
                    _text = _key_for(r.get("statement", "")) or r.get("text_key") or ""
                    if _stored.startswith("H:"):
                        self._mem.setdefault(_stored, r)
                    if _text:
                        self._mem.setdefault(_text, r)
                    elif _stored and not _stored.startswith("H:"):
                        self._mem.setdefault(_stored, r)   # legacy row, statement missing
                except Exception:
                    continue

    def get(self, statement: str, key: "str | None" = None) -> "str | None":
        # CANONICAL KEY (2026-06-24): the caller may supply a precomputed `key` — the kernel `Expr.hash` of the
        # target's de-Bruijn TYPE (`repl_compile.canonical_type_hash_via_repl`), which is α-/∀-fronting-invariant
        # where the text key is not. Try it FIRST, then fall back to the text key so a legacy text-keyed entry
        # (and the no-REPL path) still hits. The cache stays a pure store: it never calls Lean; the solver, which
        # already runs the REPL to verify, computes the key and passes it in.
        if key:
            r = self._mem.get("H:" + key)
            if r:
                return r["proof"]
        r = self._mem.get(_key_for(statement))
        return r["proof"] if r else None

    def has(self, statement: str, key: "str | None" = None) -> bool:
        return (bool(key) and ("H:" + key) in self._mem) or _key_for(statement) in self._mem

    def put(self, statement: str, proof: str, source: str = "", key: "str | None" = None) -> bool:
        """Cache a VERIFIED proof. Returns True if newly added (False if the statement
        was already cached). Caller MUST have kernel-verified `proof` first. `key` (optional) = the canonical
        `Expr.hash` key (see `get`); when supplied the entry is stored under BOTH it and the text key, so a later
        lookup hits whether or not the REPL is live."""
        text_key = _key_for(statement)
        primary = ("H:" + key) if key else text_key
        if not primary or not (proof or "").strip() or primary in self._mem:
            return False
        rec = {"key": primary, "text_key": text_key, "statement": statement.strip(), "proof": proof, "source": source}
        self._mem[primary] = rec
        if text_key:
            self._mem.setdefault(text_key, rec)   # DUAL-INDEX: also reachable by the text key (no-REPL lookups)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
        return True

    def __len__(self) -> int:
        return len(self._mem)

    def stats(self) -> dict:
        from collections import Counter
        return {"n": len(self._mem),
                "by_source": dict(Counter(r.get("source", "") for r in self._mem.values()))}


def _selftest() -> int:
    import tempfile, os
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    db = tempfile.mktemp(suffix=".jsonl")
    c = ProofCache(db)
    ok("empty get", c.get("theorem foo : P") is None)
    ok("put new", c.put("theorem foo : P", "by exact h", "leaf"))
    ok("get hit", c.get("theorem foo : P") == "by exact h")
    # name-agnostic: same statement, different local name → same key → hit
    ok("name-agnostic hit", c.get("theorem bar : P") == "by exact h")
    # body-agnostic key: a `:= sorry`-suffixed statement hits the same key
    ok("body-agnostic key", c.get("theorem baz : P := sorry") == "by exact h")
    ok("put duplicate returns False", c.put("theorem qux : P", "by other") is False)
    ok("put empty proof rejected", c.put("theorem e : Q", "  ") is False)
    # persistence across reopen
    c2 = ProofCache(db)
    ok("persisted across reopen", c2.get("theorem foo : P") == "by exact h" and len(c2) == 1)
    os.remove(db)

    # --- CANONICAL Expr.hash KEY (2026-06-24): the caller supplies a precomputed key (the kernel type hash);
    # the entry is dual-indexed so it hits by the Expr key AND by the text key (no-REPL fallback), survives reopen,
    # and a DIFFERENT statement with the SAME supplied Expr key hits (the whole point: α/∀-fronting variants). ---
    dbk = tempfile.mktemp(suffix=".jsonl")
    ck = ProofCache(dbk)
    ok("put with Expr key", ck.put("theorem t1 (h : p) : q := by sorry", "by exact e", "leaf", key="999"))
    ok("get by Expr key hits", ck.get("theorem t1 (h : p) : q := by sorry", key="999") == "by exact e")
    ok("get by text key (no key arg) hits same entry", ck.get("theorem t1 (h : p) : q := by sorry") == "by exact e")
    # a ∀-fronted / α-renamed variant has a DIFFERENT text key but the SAME Expr key ⇒ hits via the key
    ok("Expr-key hit on a textually-different variant",
       ck.get("theorem other : ∀ (a : p), q := by sorry", key="999") == "by exact e")
    ck2 = ProofCache(dbk)
    ok("Expr key survives reopen (not orphaned by text re-key)",
       ck2.get("theorem whatever : zzz := by sorry", key="999") == "by exact e")
    os.remove(dbk)

    # --- EQUIVALENCE-keyed cache (default-off lever) ---
    # By default (flag off) α-variants do NOT collapse (parity with exact keying).
    ok("default_off_alpha_distinct",
       normalize_statement("theorem a : ∀ x, P x") != normalize_statement("theorem b : ∀ y, P y")
       or "∀" not in "∀")  # exact normalizer keeps x≠y
    ok("equiv_alpha_collapses",
       normalize_statement_equiv("theorem a : ∀ x, P x → P x")
       == normalize_statement_equiv("theorem b : ∀ y, P y → P y"))
    ok("equiv_distinguishes_real_difference",
       normalize_statement_equiv("theorem a : ∀ x, P x")
       != normalize_statement_equiv("theorem b : ∀ x, Q x"))
    ok("equiv_paren_binder_collapses",
       normalize_statement_equiv("theorem a : (n : ℕ) → n = n")
       == normalize_statement_equiv("theorem b : (m : ℕ) → m = m"))
    # MULTI-DECL TARGET KEY (2026-06-24 cache-never-hits RCA): a define_then_state probe (defs THEN the theorem)
    # must key on the TARGET theorem, not the leading def's `:=` — else every such probe collides to its first
    # def's signature and never matches a bare-target-theorem goal lookup (reuse silently never fires).
    _probe = ("import Mathlib\nabbrev CS (ι : Type*) := ι → Nat\n"
              "def Feas {ι : Type*} (c : CS ι) (p : CS ι) : Prop := ∀ i, p i ≤ c i\n"
              "theorem tgt {ι : Type*} (c : CS ι) : Feas c c := by sorry")
    _goal = "theorem tgt {ι : Type*} (c : CS ι) : Feas c c := by sorry"
    ok("multidecl keys on TARGET theorem (not leading def)",
       "Feas" in normalize_statement(_probe) and "CS (ι" not in normalize_statement(_probe))
    ok("multidecl probe key == bare goal key (deposit matches lookup)",
       normalize_statement(_probe) == normalize_statement(_goal)
       and normalize_statement_equiv(_probe) == normalize_statement_equiv(_goal))
    # two probes sharing the leading def but DIFFERENT targets must NOT collide
    _probe2 = _probe.replace("theorem tgt {ι : Type*} (c : CS ι) : Feas c c",
                             "theorem tgt {ι : Type*} (c : CS ι) : Feas c c ∧ True")
    ok("different targets, same leading def ⇒ different keys",
       normalize_statement(_probe) != normalize_statement(_probe2))
    # flag flips the cache key
    os.environ["ZTARE_LEANMILL_EQUIV_CACHE"] = "1"
    try:
        db3 = tempfile.mktemp(suffix=".jsonl")
        c3 = ProofCache(db3)
        c3.put("theorem t1 : ∀ x, P x → P x", "by tauto")
        ok("equiv_cache_hits_alpha_variant", c3.get("theorem t2 : ∀ z, P z → P z") == "by tauto")
        os.remove(db3)
    finally:
        del os.environ["ZTARE_LEANMILL_EQUIV_CACHE"]

    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
