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
    s = _NAME_RE.sub("theorem _", (statement or "").strip())
    s = s.split(":=")[0]                       # drop any trailing `:= …` body/sorry
    return _WS_RE.sub(" ", s).strip()


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
    """Cache key: equivalence-collapsed iff ZTARE_LEANMILL_EQUIV_CACHE=1 (default: exact, parity)."""
    if os.environ.get("ZTARE_LEANMILL_EQUIV_CACHE") == "1":
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
                    self._mem.setdefault(r["key"], r)
                except Exception:
                    continue

    def get(self, statement: str) -> "str | None":
        r = self._mem.get(_key_for(statement))
        return r["proof"] if r else None

    def has(self, statement: str) -> bool:
        return _key_for(statement) in self._mem

    def put(self, statement: str, proof: str, source: str = "") -> bool:
        """Cache a VERIFIED proof. Returns True if newly added (False if the statement
        was already cached). Caller MUST have kernel-verified `proof` first."""
        key = _key_for(statement)
        if not key or not (proof or "").strip() or key in self._mem:
            return False
        rec = {"key": key, "statement": statement.strip(), "proof": proof, "source": source}
        self._mem[key] = rec
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
