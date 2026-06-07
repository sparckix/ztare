"""Family lemma library — the COMPOUNDING ENGINE (validated 2026-06-03).

The family-compounding lift test confirmed: providing the proven invented helpers from one
closure (Type1Unimodal) let the agent close a sibling (Type1LogConcave) kernel-clean where
from-scratch failed. This module operationalizes that: a growing per-family CONTEXT =
corpus preamble + every invented helper banked from prior closures. Each new target is solved
with this context as its `defs`; on a closure, the NEW invented decls are appended. So the
harness's outputs COMPOUND — a reusable lemma proven once is handed to every later sibling.

NON-IATROGENIC by construction:
- Banked decls are KERNEL-VERIFIED (only banked from a clean closure).
- We bank ONLY decls NOT already in the context (dedup by name) and NEVER the target/probe
  theorem (`leaf_`/`lift_` prefix) — so provisioning cannot DUPLICATE-define (which would break
  compilation) and cannot smuggle the target's own statement.
- The new closure is STILL kernel-gated, and the prepended context must itself compile (a
  helper that doesn't port surfaces as a compile error, not a false closure).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ztare.fit.mdl import MDLLibrary  # canonical MDL engine; we plug in a Lean-token size function

# A top-level Lean decl start: column 0, optional modifiers, a decl keyword, then a name.
_DECL_START = re.compile(
    r"^(?:private\s+|protected\s+|noncomputable\s+|scoped\s+)*"
    r"(lemma|theorem|def|abbrev|instance)\s+([A-Za-z_][\w.']*)")
_TERMINATORS = re.compile(r"^(end\b|#|namespace\b|section\b|open\b|variable\b|set_option\b|import\b)")


def decl_blocks(text: str) -> "list[tuple[str, str]]":
    """Split `text` into top-level (name, block) pairs for each lemma/theorem/def/abbrev/instance.
    A block runs from its decl-start line to the next decl-start / terminator / EOF."""
    lines = text.splitlines(keepends=True)
    starts = []
    for i, ln in enumerate(lines):
        m = _DECL_START.match(ln)
        if m:
            starts.append((i, m.group(2)))
    out = []
    for k, (i, name) in enumerate(starts):
        # block end = next decl start, or first terminator line after i, whichever is first
        end = starts[k + 1][0] if k + 1 < len(starts) else len(lines)
        for j in range(i + 1, end):
            if _TERMINATORS.match(lines[j]):
                end = j
                break
        out.append((name, "".join(lines[i:end]).rstrip()))
    return out


def decl_names(text: str) -> "set[str]":
    return {n for n, _ in decl_blocks(text)}


def bankable_helpers(proof_text: str, context_names: "set[str]",
                     exclude_prefixes=("leaf_", "lift_", "barr", "AgenticLeafProbe")) -> "list[tuple[str, str]]":
    """Invented helpers worth banking from a closure: decls NOT already in the family context
    (dedup by name) and NOT the target/probe theorem itself."""
    out = []
    for name, block in decl_blocks(proof_text):
        if name in context_names:
            continue
        if any(name.startswith(p) for p in exclude_prefixes):
            continue
        out.append((name, block))
    return out


_BANK_MARKER = re.compile(r"^-- \[family-lemma-library\] banked: (\S+)\s*$")


def bank(context_path: "str | Path", proof_text: str) -> "list[str]":
    """Append the closure's NEW invented helpers to the family context file. Returns the names
    banked. The context file's existing decl names are the dedup/exclusion set, so the corpus
    preamble (present from init) and prior helpers are never re-banked or duplicated.

    Each banked lemma is also REGISTERED in the MDL ledger (reuse=0, exposure=0) so the selection
    layer can later compute its compression value."""
    p = Path(context_path)
    existing = p.read_text(encoding="utf-8") if p.exists() else ""
    existing_names = decl_names(existing)
    new = bankable_helpers(proof_text, existing_names)
    if not new:
        return []
    with p.open("a", encoding="utf-8") as f:
        for name, block in new:
            f.write(f"\n-- [family-lemma-library] banked: {name}\n{block}\n")
    led = _load_ledger(context_path)
    for name, _ in new:
        _ensure_ledger(led, name)
    _save_ledger(context_path, led)
    return [n for n, _ in new]


# --- MDL selection layer (reuse/exposure ledger + MDL-optimal provisioning) ----------------------
# A banked lemma earns its place by COMPRESSING future proofs (cited ≥2×). The ledger tracks each
# banked lemma's reuse (times cited by a downstream closure) and exposure (times provisioned to a
# target). The canonical `ztare.fit.mdl.MDLLibrary` turns those counts into a keep/retire verdict
# (shared with autoresearch's compression math); `provision_mdl` drops the proven dead weight from
# the context the leaf reads. The flat append-only file remains the archive. The ONLY leanmill-
# specific piece is the size function below — how big is a Lean decl, in tokens.

_DL_COMMENT_LINE = re.compile(r"^\s*--.*$", re.M)
_DL_BLOCK_COMMENT = re.compile(r"/-.*?-/", re.S)
_DL_TOKEN = re.compile(r"[A-Za-z_][\w.']*|[^\sA-Za-z_]")


def lean_description_length(block: str) -> int:
    """MDL size of a Lean decl block: token count with comments stripped (identifiers — incl.
    dotted/primed Lean names — plus single non-space symbols, the units the kernel/leaf pay for).
    Monotone, which is all the keep/retire ranking needs; the leanmill plug-in for MDLLibrary."""
    s = _DL_BLOCK_COMMENT.sub(" ", block)
    s = _DL_COMMENT_LINE.sub(" ", s)
    return len(_DL_TOKEN.findall(s))


# The leanmill MDL library: canonical engine + the Lean size function (Strategy pattern — no math
# reimplemented here). citation_cost / min_exposure use the canonical defaults.
_MDL = MDLLibrary(size_fn=lean_description_length)


def mdl_shortest(candidates: "list[tuple[str, str]]") -> "tuple[str, str]":
    """MDL proof-form selection: among proofs that close the SAME target (best-of-N candidates),
    pick the one with the smallest description length. The kernel certifies them all equally, so
    banking the shortest minimizes the library's total description length — leaner context for the
    leaf, faster recompiles, more portable lemmas. This is the proof-form analogue of
    `compress_champion`'s 'simplest gate-passing form', on the same MDL principle.

    `candidates` = [(label, proof_text), ...]; returns the (label, proof_text) of the shortest.
    Ties break by label for determinism. Empty/blank proofs are ignored; if none remain, returns
    the first candidate unchanged (caller still has a closure, just no shorter form to prefer)."""
    scored = [(lean_description_length(p), lbl, p) for lbl, p in candidates if p and p.strip()]
    if not scored:
        return candidates[0] if candidates else ("", "")
    scored.sort(key=lambda t: (t[0], t[1]))
    return scored[0][1], scored[0][2]


def _split_banked(text: str) -> "tuple[str, list[tuple[str, str]]]":
    """Split a context file into (corpus_preamble, [(name, banked_block), ...]). The banked section
    begins at the first `-- [family-lemma-library] banked:` marker; each block runs marker→next
    marker (the marker comment is kept in the block — harmless, and stripped from the DL count)."""
    lines = text.splitlines(keepends=True)
    markers = [(i, m.group(1)) for i, ln in enumerate(lines)
               if (m := _BANK_MARKER.match(ln))]
    if not markers:
        return text, []
    preamble = "".join(lines[:markers[0][0]])
    banked = []
    for k, (i, name) in enumerate(markers):
        end = markers[k + 1][0] if k + 1 < len(markers) else len(lines)
        banked.append((name, "".join(lines[i:end]).rstrip()))
    return preamble, banked


def _ledger_path(context_path: "str | Path") -> Path:
    return Path(str(context_path) + ".mdl.json")


def _load_ledger(context_path: "str | Path") -> dict:
    p = _ledger_path(context_path)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"lemmas": {}}


def _save_ledger(context_path: "str | Path", led: dict) -> None:
    _ledger_path(context_path).write_text(json.dumps(led, indent=2), encoding="utf-8")


def _ensure_ledger(led: dict, name: str) -> None:
    led.setdefault("lemmas", {}).setdefault(name, {"reuse": 0, "exposure": 0})


def record_exposure(context_path: "str | Path", names: "list[str]") -> None:
    """A target was solved with these banked lemmas in its provisioned context (+1 exposure each).
    Exposure without reuse is what eventually marks a lemma as dead weight."""
    if not names:
        return
    led = _load_ledger(context_path)
    for n in names:
        _ensure_ledger(led, n)
        led["lemmas"][n]["exposure"] += 1
    _save_ledger(context_path, led)


def record_reuse(context_path: "str | Path", cited_names: "list[str]") -> None:
    """A closure CITED these banked lemmas (+1 reuse each) — the compression signal."""
    if not cited_names:
        return
    led = _load_ledger(context_path)
    for n in cited_names:
        _ensure_ledger(led, n)
        led["lemmas"][n]["reuse"] += 1
    _save_ledger(context_path, led)


def _banked_lemmas_and_counts(context_path: "str | Path"):
    """(full_text, {name: block}, {name: reuse}, {name: exposure}) for the banked (non-corpus) lemmas."""
    text = provision(context_path)
    _, banked = _split_banked(text)
    lemmas = {n: b for n, b in banked}
    led = _load_ledger(context_path).get("lemmas", {})
    reuse = {n: led.get(n, {}).get("reuse", 0) for n in lemmas}
    exposure = {n: led.get(n, {}).get("exposure", 0) for n in lemmas}
    return text, lemmas, reuse, exposure


def mdl_stats(context_path: "str | Path"):
    """Per-banked-lemma MDL stats (ItemStat list from the canonical engine, best compressor first)."""
    _, lemmas, reuse, exposure = _banked_lemmas_and_counts(context_path)
    return _MDL.score(lemmas, reuse, exposure)


def provision_mdl(context_path: "str | Path") -> str:
    """MDL-optimal provisioned context = corpus preamble + only the banked lemmas that earn their
    place (net compressors + under-exposed provisionals). Proven dead weight (exposed, never reused)
    is dropped — leaner context for the leaf, fewer recompiles for the kernel, same closures."""
    text = provision(context_path)
    preamble, banked = _split_banked(text)
    if not banked:
        return text
    lemmas = {n: b for n, b in banked}
    led = _load_ledger(context_path).get("lemmas", {})
    reuse = {n: led.get(n, {}).get("reuse", 0) for n in lemmas}
    exposure = {n: led.get(n, {}).get("exposure", 0) for n in lemmas}
    keep, _retire = _MDL.partition(lemmas, reuse, exposure)
    keep_set = set(keep)
    out = preamble.rstrip() + "\n"
    for name, block in banked:
        if name in keep_set:
            out += "\n" + block + "\n"
    return out


def provision(context_path: "str | Path") -> str:
    """The family context to use as a target's `defs` (corpus preamble + banked helpers)."""
    p = Path(context_path)
    return p.read_text(encoding="utf-8") if p.exists() else ""


def init_context(context_path: "str | Path", corpus_preamble: str) -> None:
    """Seed a fresh family context with the corpus preamble (the shared defs/Props)."""
    Path(context_path).write_text(corpus_preamble.rstrip() + "\n", encoding="utf-8")


def _self_test() -> int:
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    corpus = (
        "import Mathlib\n\n"
        "def Foo (n : ℕ) : ℕ := n + 1\n\n"
        "def TargetProp : Prop := ∀ n, Foo n = n + 1\n")
    proof = corpus + (
        "\nlemma helper_a (n : ℕ) : Foo n = n + 1 := rfl\n"
        "\nnoncomputable def helper_b : ℕ := 0\n"
        "\ntheorem leaf_TargetProp : TargetProp := by intro n; exact helper_a n\n")

    blocks = dict(decl_blocks(proof))
    ok("extracts_all_decls", {"Foo", "TargetProp", "helper_a", "helper_b", "leaf_TargetProp"} <= set(blocks))
    ok("block_is_multiline_ok", "helper_a" in blocks["helper_a"] and ":= rfl" in blocks["helper_a"])

    import tempfile, os
    ctx = tempfile.mktemp(suffix=".lean")
    init_context(ctx, corpus)
    banked = bank(ctx, proof)
    ok("banks_only_invented_helpers", set(banked) == {"helper_a", "helper_b"})  # NOT Foo/TargetProp (corpus) NOR leaf_
    ok("no_corpus_or_target_banked", "Foo" not in banked and "TargetProp" not in banked
       and "leaf_TargetProp" not in banked)
    prov = provision(ctx)
    ok("provision_has_corpus_and_helpers",
       "def Foo" in prov and "TargetProp" in prov and "helper_a" in prov and "helper_b" in prov)
    ok("provision_excludes_target_theorem", "leaf_TargetProp" not in prov)
    # idempotent: re-banking the same proof adds nothing (dedup by name → no duplicate defs)
    again = bank(ctx, proof)
    ok("rebank_is_idempotent", again == [])

    # --- MDL selection layer ---
    # banking registered both helpers in the ledger at reuse=0, exposure=0
    pre, banked = _split_banked(provision(ctx))
    ok("split_isolates_banked", {n for n, _ in banked} == {"helper_a", "helper_b"})
    ok("split_preamble_is_corpus", "def Foo" in pre and "helper_a" not in pre)

    # helper_a gets reused 2× and exposed; helper_b only ever exposed (dead weight)
    record_reuse(ctx, ["helper_a"]); record_reuse(ctx, ["helper_a"])
    for _ in range(4):
        record_exposure(ctx, ["helper_a", "helper_b"])
    stats = {s.name: s for s in mdl_stats(ctx)}
    ok("reused_helper_kept", stats["helper_a"].verdict == "KEEP")
    ok("dead_weight_retired", stats["helper_b"].verdict == "RETIRE")
    prov_mdl = provision_mdl(ctx)
    ok("mdl_provision_keeps_compressor", "helper_a" in prov_mdl)
    ok("mdl_provision_drops_dead_weight", "helper_b" not in prov_mdl)
    ok("mdl_provision_keeps_corpus", "def Foo" in prov_mdl and "TargetProp" in prov_mdl)

    os.path.exists(ctx) and os.remove(ctx)
    lp = ctx + ".mdl.json"
    os.path.exists(lp) and os.remove(lp)

    # --- MDL proof-form selection: shortest of equivalent closers ---
    short = "by simp"
    long = "by\n  intro n h\n  have h1 : n + 1 > 1 := by omega\n  exact Nat.lt_of_lt_of_le h1 (le_refl _)"
    pick_lbl, pick_proof = mdl_shortest([("codex", long), ("claude", short)])
    ok("mdl_shortest_picks_smallest", pick_proof == short and pick_lbl == "claude")
    ok("mdl_shortest_tie_break_deterministic",
       mdl_shortest([("b", short), ("a", short)])[0] == "a")
    ok("mdl_shortest_ignores_blank", mdl_shortest([("x", "  "), ("y", short)])[0] == "y")
    ok("mdl_shortest_empty_safe", mdl_shortest([]) == ("", ""))

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
