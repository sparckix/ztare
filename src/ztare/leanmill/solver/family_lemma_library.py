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


def _open_namespaces(text: str) -> "list[str]":
    """Distinct namespaces the env DECLARES (its defs live inside them), first-seen order. A banked rung is
    appended at EOF — OUTSIDE those namespaces — so without re-opening them its short-name references to the
    campaign defs autobind as local variables ⇒ `Function expected` / `not a proposition` ⇒ noncompile ⇒ silent
    revert. This was why the pari-passu feasibility (298-line proof citing `namespace AbsolutePriorityWaterfall`
    defs) could never bank while pure-NNReal lemmas (no namespaced refs) banked fine. RCA 2026-06-24."""
    from ztare.leanmill.lean_source import strip_comments   # canonical comment stripper — no `namespace` in a comment false-matches
    seen: "list[str]" = []
    for raw in strip_comments(text or "").splitlines():
        parts = raw.split()                                  # token split, NOT a Lean regex: a `namespace X` command
        if len(parts) >= 2 and parts[0] == "namespace" and parts[1] not in seen:
            seen.append(parts[1])                            # `X` or `X.Y` — the declared namespace
    return seen


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
    # NAMESPACED ENV: re-open the env's namespaces in a SECTION so the appended flat rungs can resolve the campaign
    # defs by short name (the decls themselves persist top-level — `section` scopes only the `open`, not the decls,
    # so a later rung still cites them flat). Non-namespaced env ⇒ nss empty ⇒ bare append (byte-parity). 2026-06-24.
    nss = _open_namespaces(existing)
    with p.open("a", encoding="utf-8") as f:
        if nss:
            f.write("\nsection  -- [family-lemma-library] banked rungs (re-open env namespaces for short-name refs)\n")
            for n in nss:
                f.write(f"open {n}\n")
        for name, block in new:
            f.write(f"\n-- [family-lemma-library] banked: {name}\n{block}\n")
        if nss:
            f.write("\nend\n")
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


# --- campaign WARM-ENV banking (the cross-run amnesia fix, 2026-06-19) ----------------------------
# The notes-channel campaign run registers a theory file via `repl_compile.set_campaign_substrate`; the
# verify seam loads it ONCE into the warm REPL env (`campaign_file_env`, re-opens on mtime change) so the
# cascade's `exact?`/`aesop` CITE its decls BY TYPE. But nothing appended closed rungs to that file, so it
# stayed static → every run re-derived (RCA: a root-splitting `iso_lemma1` proved at 18:50 was re-derived
# byte-identical at 00:02). `bank_decl_to_env` is the missing append — same engine as `bank` (decl_blocks /
# dedup), with TWO additions justified by the SHARED warm-env (vs `bank`'s provision-as-defs, where a bad
# decl only fails ITS target's compile): a CONTENT-STABLE name so the planner's GENERIC node names
# (`iso_lemma1` is ≥3 distinct theorems) don't collide-and-drop, and a whole-file REVERIFY+REVERT so a
# non-porting rung can't poison every subsequent warm-env verify in the run.


def content_stable_name(base_name: str, decl_text: str) -> str:
    """A decl name UNIQUE to the statement's content (α-key hashed), so generic planner node names don't
    collide in the shared env and identical statements dedupe to one library decl."""
    import hashlib
    from ztare.leanmill.solver.proof_cache import normalize_statement_equiv
    h = hashlib.sha256(normalize_statement_equiv(decl_text or "").encode("utf-8")).hexdigest()[:8]
    safe = re.sub(r"[^A-Za-z0-9_]", "_", base_name or "rung").strip("_") or "rung"
    return f"{safe}__{h}"


def _rename_decl_head(decl_text: str, old_name: str, new_name: str) -> str:
    """Rename ONLY the binding occurrence in the decl head; safe (a decl's name isn't referenced by its own body)."""
    if not old_name or old_name == new_name:
        return decl_text
    return re.sub(r"\b((?:theorem|lemma|def|abbrev)\s+)" + re.escape(old_name) + r"\b",
                  lambda m: m.group(1) + new_name, decl_text, count=1)


def _sorried_placeholder_present(text: str, name: str) -> bool:
    """True iff `text` holds a decl named `name` whose body is a `sorry` work-item placeholder. This is the
    SUPERSESSION trigger (RCA 2026-06-25): the consolidation seeds `theorem name … := by sorry` as the canonical
    work-item; once proven, the proof must TAKE OVER that canonical name, not bank under a mangled sibling that
    leaves the sorried placeholder owning the name (downstream `exact?`/short-name citations then bind to the
    sorry → sorryAx)."""
    for n, block in decl_blocks(text):
        if n == name and re.search(r"\bsorry\b", block):
            return True
    return False


def _strip_named_decl(text: str, name: str) -> str:
    """Remove the (first) top-level decl named `name`, together with an immediately-preceding doc/`--` comment
    block (a dangling `/-- … -/` would otherwise mis-attach or error). Span logic mirrors `decl_blocks` — no
    Lean re-parse, canonical `_DECL_START`/`_TERMINATORS`."""
    lines = text.splitlines(keepends=True)
    starts = [(i, m.group(2)) for i, ln in enumerate(lines) if (m := _DECL_START.match(ln))]
    for k, (i, n) in enumerate(starts):
        if n != name:
            continue
        end = starts[k + 1][0] if k + 1 < len(starts) else len(lines)
        for j in range(i + 1, end):
            if _TERMINATORS.match(lines[j]):
                end = j
                break
        # absorb a contiguous preceding comment/blank block (its doc comment belonged to this decl)
        s = i
        while s - 1 >= 0 and (lines[s - 1].lstrip().startswith(("--", "/-", "-/")) or not lines[s - 1].strip()
                              or "-/" in lines[s - 1]):
            s -= 1
        del lines[s:end]
        return "".join(lines)
    return text


def _default_reverify(file_path: "str | Path", lean_root: "str | Path") -> bool:
    """Reverify the appended campaign file via the PRODUCTION load path (`repl_compile.campaign_file_env`): it
    re-elaborates the file's decls onto the warm Mathlib env and returns an env id iff the file compiles (None on
    a hard error / dead REPL / toolchain drift). Read-only on the file — NOT `_compile_probe`, which copies to a
    temp probe and runs a substrate-hygiene cleanup that DELETED the file (real bug, caught in the real-Lean
    test 2026-06-19). Faithful: an env here ⇒ the run's verify seam can actually cite the rung."""
    from ztare.formal.repl_compile import campaign_file_env
    return campaign_file_env(str(Path(file_path).resolve()), str(Path(lean_root).resolve())) is not None


def _default_axiom_audit(file_path: "str | Path", lean_root: "str | Path", decl_name: str) -> "tuple[bool, str]":
    """Persistence-context axiom audit for a just-banked decl: `(clean_or_unknown, reason)`.

    THE GUARD (2026-06-25 RCA): a banked rung must be `#print axioms`-clean IN THE FILE it is persisted in,
    not just in the isolated probe. The bank reverify only checked COMPILE (`campaign_file_env`), so a rung
    that cites a still-`sorry` decl by its canonical name (the proven proof was banked under a MANGLED name,
    leaving the canonical name owned by the sorried work-item placeholder) compiled fine and was banked —
    `sorryAx` only surfaced when the assembled target was re-elaborated standalone (probe-world vs
    persistence-world). This audits the persisted env via the SAME warm `#print axioms` path the cold
    governance audit uses.

    Returns `(False, …)` ONLY when a `sorryAx` is DETECTED in the persisted env — that is fail-CLOSED (revert
    the bank). Infra-dead / inconclusive ⇒ `(True, 'unavailable')` — fail-OPEN at the per-rung gate so flaky
    REPL infra never blocks compounding; the campaign's final-target audit and the cold governance audit remain
    as the backstops for that case."""
    try:
        from ztare.formal.repl_compile import campaign_file_decl_axiom_clean
        res = campaign_file_decl_axiom_clean(str(file_path), str(lean_root), decl_name)
    except Exception:  # noqa: BLE001 — audit infra error ⇒ unavailable (fail-open), not a taint verdict
        return (True, "axiom_audit_unavailable")
    if res is None:                                  # inconclusive / infra unusable ⇒ fail-open at this gate
        return (True, "axiom_audit_unavailable")
    clean, diag = res
    return (clean, diag if not clean else "axiom_clean")


def _supersede_in_place(text: str, target_name: str, decl_text: str):
    """IN-PLACE supersession (RCA 2026-06-25, the v3 reverted_noncompile fix): replace the sorried placeholder
    `target_name` with its PROOF *where it sits* — keeping its namespace position and qualified name
    `NS.target_name` — so COMPOSITE proofs that cite it by that name still resolve. (Strip + re-bank-at-EOF
    RELOCATES the decl to top-level, changing `NS.F` → `F`, which broke every composite lemma citing `F` →
    reverted_noncompile.) The proof's NEW inline helpers are content-stable-renamed (no cross-lemma generic-name
    collision) and inserted right BEFORE the proof (in scope + ordered). Returns (new_text, banked_names) or
    (None, []) when the placeholder span can't be located cleanly (caller then keeps the mangled path)."""
    lines = text.splitlines(keepends=True)
    starts = [(i, m.group(2)) for i, ln in enumerate(lines) if (m := _DECL_START.match(ln))]
    span = None
    for k, (i, n) in enumerate(starts):
        if n != target_name:
            continue
        end = starts[k + 1][0] if k + 1 < len(starts) else len(lines)
        for j in range(i + 1, end):
            if _TERMINATORS.match(lines[j]):
                end = j
                break
        span = (i, end)
        break
    if span is None:
        return (None, [])
    existing = decl_names(text)
    blocks = decl_blocks(decl_text)
    target_block = next((b for n, b in blocks if n == target_name), None)
    if not target_block:
        return (None, [])
    helpers = [(n, b) for n, b in blocks if n != target_name and n not in existing
               and not any(n.startswith(pre) for pre in ("leaf_", "lift_", "barr", "AgenticLeafProbe"))]
    rename = {n: content_stable_name(n, b) for n, b in helpers}   # collision-safe helper names
    def _apply(s: str) -> str:
        for old, new in rename.items():
            s = re.sub(r"\b" + re.escape(old) + r"\b", new, s)
        return s
    replacement = "".join(_apply(b).rstrip() + "\n\n" for _n, b in helpers) + _apply(target_block).rstrip() + "\n"
    return ("".join(lines[:span[0]] + [replacement] + lines[span[1]:]), [rename[n] for n, _ in helpers] + [target_name])


def bank_decl_to_env(context_path: "str | Path", target_name: str, decl_text: str, lean_root: "str | Path",
                     *, reverify_fn=None, axiom_audit_fn=None) -> dict:
    """Bank ONE kernel-closed rung's full decl into the campaign warm-env file, content-stable-renamed, with a
    reverify+revert via the production load path. Incremental (call at the kernel-ratify site) ⇒ death-robust
    (you keep what you proved even if the run dies mid-way) AND within-run citable. Reuses `bank` (dedup) and
    `decl_names`. Returns {banked_as: <name>|None, reason}. Sound: the rung was already axiom-audited; the
    reverify+revert keeps the shared env compiling (a non-porting rung is dropped, never minted) — and even if a
    bad rung slipped in, `campaign_file_env` would return None ⇒ the run falls back to inline elaboration, so the
    worst case is lost compounding, never unsoundness."""
    p = Path(context_path)
    if not (decl_text or "").strip() or not p.exists():
        return {"banked_as": None, "reason": "no_decl_or_no_context"}
    blocks = dict(decl_blocks(decl_text))
    block = blocks.get(target_name) or (next(iter(blocks.values()), "") if len(blocks) == 1 else "")
    if not block or "sorry" in block:
        return {"banked_as": None, "reason": "no_proven_decl"}
    before = p.read_text(encoding="utf-8")
    # SUPERSESSION (RCA 2026-06-25): if `target_name` is a sorried work-item PLACEHOLDER in the env, the proof
    # must TAKE OVER that canonical name so downstream short-name / `exact?` citations bind to the PROOF, not the
    # sorry (the laundered-sorried-decl class). Done IN PLACE (`_supersede_in_place`) — the body is swapped where
    # the placeholder sits, KEEPING its namespace + qualified name `NS.F`, so COMPOSITE proofs citing `F` still
    # resolve. (The earlier strip+rebank-at-EOF RELOCATED `F` to top-level → `NS.F` vanished → every composite
    # citing it failed reverted_noncompile — the v3 bug.) Otherwise (a generic planner node name, no placeholder)
    # keep the content-stable mangling that disambiguates distinct same-name theorems. The reverify + axiom-guard
    # backstop either path (a non-porting / sorry-tainted bank reverts to `before`, restoring the placeholder).
    _superseded, _superseded_names, _new_text = False, [], None
    if _sorried_placeholder_present(before, target_name):
        _new_text, _superseded_names = _supersede_in_place(before, target_name, decl_text)
        _superseded = _new_text is not None
    if _superseded:
        new_name = target_name
        renamed = decl_text                                    # (for the event log)
        p.write_text(_new_text, encoding="utf-8")
    else:
        if target_name in decl_names(before) and not _sorried_placeholder_present(before, target_name):
            return {"banked_as": None, "reason": "already"}    # canonical proof already banked (superseded)
        new_name = content_stable_name(target_name, block)
        if new_name in decl_names(before):
            return {"banked_as": None, "reason": "already"}        # identical statement already in the env
        # CARRY THE INLINE HELPERS (RCA 2026-06-24): rename the target's head IN THE FULL PROBE so `bank()` appends
        # the renamed headline AND the inline helper lemmas its proof cites — TOGETHER. `bankable_helpers` dedups
        # NEW decls by name, so the probe's def preamble + already-banked helpers are skipped (no duplicate-def).
        renamed = _rename_decl_head(decl_text, target_name, new_name)
    _rv = reverify_fn or _default_reverify

    def _try(path) -> bool:
        try:
            return bool(_rv(path, lean_root))
        except Exception:  # noqa: BLE001 — a tooling error ⇒ treat as a failed reverify, never a crash
            return False

    banked = _superseded_names if _superseded else bank(p, renamed)   # in-place supersede, else EOF append+dedup+MDL
    if new_name not in banked:
        return {"banked_as": None, "reason": "dedup_or_excluded"}
    if _try(p):
        # THE GUARD (RCA 2026-06-25): persistence-context axiom audit — a banked rung must be #print-axioms
        # clean IN THE FILE, not just compile. Catches a rung that cites a still-`sorry` canonical name (the
        # proven proof banked under a MANGLED name, the sorried work-item placeholder still owning the canonical
        # namespaced name reachable via the `open`). Skipped only under an injected reverify_fn (unit tests, no
        # live REPL) unless an explicit axiom_audit_fn is supplied. Fail-CLOSED on a detected sorryAx (revert).
        _aa = axiom_audit_fn if axiom_audit_fn is not None else (_default_axiom_audit if reverify_fn is None else None)
        if _aa is not None:
            _clean, _areason = _aa(p, lean_root, new_name)
            if not _clean:
                p.write_text(before, encoding="utf-8")   # REVERT a sorry-tainted bank (no false-clean rung)
                return {"banked_as": None, "reason": f"reverted_axiom_taint:{_areason}"}
        _helpers = [n for n in banked if n != new_name]
        # EVENT-SOURCING (the derived-view leg, 2026-06-25): also emit the bank as a durable, node-stamped event
        # to the mergeable bank-events log. The .lean file is the live MATERIALIZED VIEW (cited this run); the
        # event log is the SOURCE OF TRUTH a merged or fresh node re-derives the view from (see
        # `rederive_library_from_events`). This makes the compounding library node-agnostic and dissolves the
        # concurrent-append race (each node appends to a content-addressed log; the union re-materializes
        # deterministically). Non-fatal: a telemetry failure must never break banking.
        try:
            record_bank_event(p.name, new_name, renamed, helpers=_helpers)
        except Exception:  # noqa: BLE001
            pass
        return {"banked_as": new_name, "reason": "banked", "helpers_banked": _helpers}
    p.write_text(before, encoding="utf-8")                     # REVERT — a non-porting rung must not poison the env
    # CLASSIFY the failure honestly (positive control on the reverted file): a reverify that returns False for
    # BOTH "infra is dead" (toolchain-less root / dead REPL / flag off) and "the rung genuinely breaks the env"
    # is a dead instrument — that conflation hid the wrong-lean_root banking bug for an entire P1 run (every
    # rung silently mislabeled `reverted_noncompile`). The unmodified `before` file is known-good (it loaded as
    # the campaign env), so if it ALSO fails to reverify, the reverify apparatus — not the rung — is the
    # problem. Only paid on the failure path; the common (banked) path stays one elaboration.
    reason = "reverted_noncompile" if _try(p) else "reverify_unavailable"
    return {"banked_as": None, "reason": reason}


# --- event-sourcing: the bank-events log + view re-derivation (the derived-view leg, 2026-06-25) ----
# DDIA: the .lean library is a MATERIALIZED VIEW; the source of truth is an append-only log of bank
# events. Each event is one kernel-verified rung (content-stable name + its full renamed probe, helpers
# carried). The log is a CvRDT (grow-only set keyed by (substrate, name)) — two nodes' logs union
# cleanly, and `rederive_library_from_events` folds the union back into a node-agnostic .lean view. This
# is what makes compounding distributed-safe; the live incremental append (in `bank`/`bank_decl_to_env`)
# is unchanged and remains the per-run cache.


def _repo_root() -> Path:
    # src/ztare/leanmill/solver/family_lemma_library.py → parents[4] == repo root
    return Path(__file__).resolve().parents[4]


def bank_events_path() -> Path:
    """Canonical bank-events log, co-located with the other solver-lane stores (env-overridable)."""
    import os
    env = os.environ.get("ZTARE_LEANMILL_BANK_EVENTS")
    if env:
        return Path(env)
    return _repo_root() / "analytics" / "public" / "queries" / "solver_lane_bank_events.jsonl"


def record_bank_event(substrate: str, name: str, decl_text: str,
                      *, helpers=None, path: "str | Path | None" = None) -> None:
    """Append a durable, node-stamped bank event — the source of truth the .lean view is folded from.

    `substrate` is the theory file BASENAME (node-agnostic id); `name` is the content-stable rung name;
    `decl_text` is the full renamed probe that was banked (helpers carried), so a replay reproduces the
    exact decls. Append-only; identity for the merge is (substrate, name) — see
    `state_convergence.STORE_SPECS`. Best-effort: callers wrap in try/except so telemetry never breaks
    banking."""
    p = Path(path) if path else bank_events_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        from ztare.leanmill.state_convergence import stamp_provenance
        rec = stamp_provenance({"substrate": substrate, "name": name,
                                "decl_text": decl_text, "helpers": list(helpers or [])})
    except Exception:  # noqa: BLE001 — provenance is optional; the fact still records
        rec = {"substrate": substrate, "name": name, "decl_text": decl_text,
               "helpers": list(helpers or [])}
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=True) + "\n")


def read_bank_events(path: "str | Path | None" = None) -> "list[dict]":
    p = Path(path) if path else bank_events_path()
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            out.append(obj)
    return out


def rederive_library_from_events(context_path: "str | Path", lean_root: "str | Path",
                                 events: "list[dict] | None" = None,
                                 *, reverify_fn=None) -> dict:
    """Rebuild a substrate's banked section from the union of bank events (the materialized-view fold).

    Node-agnostic and idempotent: the same event set re-materializes the same library (events deduped by
    name, replayed in name order for a reproducible, diff-clean file). The SOUNDNESS boundary is the SAME
    reverify+revert as incremental banking — a view that does not compile is rejected and the prior
    known-good .lean is kept. This is the reconcile step after a cross-node merge / on a fresh node; the
    live per-run path still appends incrementally (this is not auto-run, to avoid churn).

    Returns {rederived: <n>, reason}. The corpus preamble (the original theory, non-banked) is preserved.
    """
    p = Path(context_path)
    if not p.exists():
        return {"rederived": 0, "reason": "no_context"}
    substrate = p.name
    evs = [e for e in (events if events is not None else read_bank_events())
           if e.get("substrate") == substrate and (e.get("decl_text") or "").strip()]
    # dedup by content-stable name (the union may carry the same fact from N nodes)
    by_name: "dict[str, dict]" = {}
    for e in evs:
        by_name.setdefault(e["name"], e)
    ordered = [by_name[n] for n in sorted(by_name)]
    before = p.read_text(encoding="utf-8")
    preamble, _ = _split_banked(before)
    p.write_text(preamble.rstrip() + "\n", encoding="utf-8")
    for e in ordered:
        bank(p, e["decl_text"])               # reuse the canonical append+dedup+namespace-open+MDL-ledger
    _rv = reverify_fn or _default_reverify
    try:
        ok = bool(_rv(p, lean_root))
    except Exception:  # noqa: BLE001
        ok = False
    if not ok:
        p.write_text(before, encoding="utf-8")  # never ship a non-compiling view; keep the known-good one
        return {"rederived": 0, "reason": "reverify_failed", "kept_previous": True}
    return {"rederived": len(ordered), "reason": "ok"}


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

    # --- campaign warm-env banking: the generic-name-collision + revert behaviour (cross-run amnesia fix) ---
    env = tempfile.mktemp(suffix=".lean")
    init_context(env, "import Mathlib\n")
    # injected reverify (file_path, lean_root) -> bool — file compiles unless it carries the bad-dep marker
    _rv = lambda path, root: "NoSuchThing" not in Path(path).read_text(encoding="utf-8")
    a = bank_decl_to_env(env, "iso_lemma1", "theorem iso_lemma1 (n:Nat): n+0=n := by simp", ".", reverify_fn=_rv)
    b = bank_decl_to_env(env, "iso_lemma1", "theorem iso_lemma1 (n:Nat): n*1=n := by simp", ".", reverify_fn=_rv)
    ok("env: first generic iso_lemma1 banked under a content name", bool(a["banked_as"]))
    ok("env: SECOND distinct iso_lemma1 ALSO banked (no name-collision drop)", bool(b["banked_as"]))
    ok("env: the two distinct lemmas got DIFFERENT content names", a["banked_as"] != b["banked_as"])
    txt = Path(env).read_text(encoding="utf-8")
    ok("env: both distinct lemmas live in the file", "n+0=n" in txt and "n*1=n" in txt)
    c = bank_decl_to_env(env, "iso_lemma1", "theorem iso_lemma1 (m:Nat): m+0=m := by simp", ".", reverify_fn=_rv)
    ok("env: α-identical statement deduped (not re-banked)", c["banked_as"] is None and c["reason"] == "already")
    d = bank_decl_to_env(env, "bad", "theorem bad (n:Nat): n=n := NoSuchThing", ".", reverify_fn=_rv)
    ok("env: non-compiling rung reverted (not banked)", d["banked_as"] is None and d["reason"] == "reverted_noncompile")
    ok("env: reverted rung is NOT in the file", "NoSuchThing" not in Path(env).read_text(encoding="utf-8"))
    e = bank_decl_to_env(env, "s", "theorem s : False := by sorry", ".", reverify_fn=_rv)
    ok("env: sorried rung not banked", e["banked_as"] is None)
    # DEAD-INFRA classification: a reverify that ALWAYS fails (toolchain-less root / dead REPL — the wrong-root
    # banking bug, 2026-06-20) must NOT be mislabeled `reverted_noncompile`; the positive control on the
    # known-good reverted file catches the conflation and reports `reverify_unavailable`.
    _rv_dead = lambda path, root: False
    f = bank_decl_to_env(env, "good", "theorem good (n:Nat): n+1=n+1 := by rfl", ".", reverify_fn=_rv_dead)
    ok("env: dead reverify-infra reported as reverify_unavailable (not a false non-compile)",
       f["banked_as"] is None and f["reason"] == "reverify_unavailable")
    # MULTI-HELPER CARRY (RCA 2026-06-24): a proof citing a LOCAL helper must bank the helper too, else the renamed
    # headline can't recompile standalone → silent revert (the bug that zeroed reuse + caused the pari-passu AP gap).
    # _rv_dep models 'unknown identifier': fails iff the target uses `helper_aux` but no `helper_aux` decl is present.
    _rv_dep = lambda path, root: not (
        "helper_aux n" in (_t := Path(path).read_text(encoding="utf-8")) and "theorem helper_aux" not in _t)
    multi = ("theorem helper_aux (n : Nat) : n + 0 = n := by simp\n"
             "theorem multi_target (n : Nat) : n + 0 = n := helper_aux n")
    g = bank_decl_to_env(env, "multi_target", multi, ".", reverify_fn=_rv_dep)
    ok("env: multi-helper proof BANKS (inline helper carried, not dropped → no silent revert)", bool(g["banked_as"]))
    ok("env: the inline helper was carried (reported in helpers_banked)", "helper_aux" in (g.get("helpers_banked") or []))
    ok("env: helper_aux decl present in the banked env (citable next run)",
       "theorem helper_aux" in Path(env).read_text(encoding="utf-8"))
    # NAMESPACED ENV (RCA 2026-06-24): a flat rung citing a namespaced def must bank WITH `open NS`, else its
    # short-name refs autobind as locals → noncompile → silent revert (why the pari-passu feasibility, citing
    # `namespace AbsolutePriorityWaterfall` defs, never banked while pure-NNReal lemmas did).
    nsenv = tempfile.mktemp(suffix=".lean")
    init_context(nsenv, "import Mathlib\nnamespace NS\ndef foo : Nat := 0\nend NS\n")
    _rv_ns = lambda path, root: ("uses_foo" not in (_t := Path(path).read_text(encoding="utf-8"))) or ("open NS" in _t)
    h = bank_decl_to_env(nsenv, "uses_foo", "theorem uses_foo : foo = foo := rfl", ".", reverify_fn=_rv_ns)
    ok("env: namespaced-env rung banks WITH open (flat refs to namespaced defs resolve)", bool(h["banked_as"]))
    ok("env: banked block re-opens the env namespace", "open NS" in Path(nsenv).read_text(encoding="utf-8"))
    # AXIOM GUARD (RCA 2026-06-25): a rung that COMPILES but is sorry-tainted in the PERSISTED env must be
    # REVERTED, not banked — the laundered-sorried-canonical-name class (proven proof under a mangled name; the
    # sorried work-item placeholder still owning the canonical namespaced name reachable via the `open`).
    gtaint = bank_decl_to_env(nsenv, "tainted_rung", "theorem tainted_rung (n:Nat) : n = n := rfl", ".",
                              reverify_fn=_rv_ns, axiom_audit_fn=lambda f, r, n: (False, "sorryAx_in_persisted_env"))
    ok("env: axiom-guard REVERTS a sorry-tainted bank (compiles but #print axioms dirty)",
       gtaint["banked_as"] is None and "axiom_taint" in gtaint["reason"])
    ok("env: reverted-by-axiom-guard rung is NOT in the file", "tainted_rung" not in Path(nsenv).read_text(encoding="utf-8"))
    gclean = bank_decl_to_env(nsenv, "clean_rung", "theorem clean_rung (n:Nat) : n + 0 = n := by simp", ".",
                              reverify_fn=_rv_ns, axiom_audit_fn=lambda f, r, n: (True, "axiom_clean"))
    ok("env: axiom-guard ALLOWS a clean bank", bool(gclean["banked_as"]))
    # SUPERSESSION (RCA 2026-06-25): a proof for a work-item with a sorried placeholder must TAKE OVER the
    # canonical name (strip placeholder, bank un-mangled) so downstream citations bind to the proof, not the sorry.
    supenv = tempfile.mktemp(suffix=".lean")
    init_context(supenv, "import Mathlib\n\n/-- work item -/\ntheorem wf (n : Nat) : n = n := by sorry\n")
    _rv_sup = lambda path, root: "sorry" not in Path(path).read_text(encoding="utf-8")  # compiles iff no sorry remains
    sup = bank_decl_to_env(supenv, "wf", "theorem wf (n : Nat) : n = n := rfl", ".",
                           reverify_fn=_rv_sup, axiom_audit_fn=lambda f, r, n: (True, "axiom_clean"))
    _suptxt = Path(supenv).read_text(encoding="utf-8")
    ok("supersede: proof banked under the CANONICAL name (un-mangled)", sup["banked_as"] == "wf")
    ok("supersede: sorried placeholder removed (no sorry remains)", "sorry" not in _suptxt)
    ok("supersede: exactly one `theorem wf` (the proof, not a sibling)", _suptxt.count("theorem wf") == 1 and ":= rfl" in _suptxt)
    # a generic (non-placeholder) name still mangles, as before
    gen = bank_decl_to_env(supenv, "iso_lemma1", "theorem iso_lemma1 (n:Nat) : n+0=n := by simp", ".",
                           reverify_fn=_rv_sup, axiom_audit_fn=lambda f, r, n: (True, "axiom_clean"))
    ok("supersede: generic name without a placeholder still gets a content-stable __hash", (gen["banked_as"] or "").startswith("iso_lemma1__"))
    # IN-PLACE composite (RCA 2026-06-25, the v3 reverted_noncompile fix): a NAMESPACED placeholder superseded
    # must STAY in the namespace (qualified name `NS.F` kept) so COMPOSITE proofs citing it resolve — NOT
    # relocated to EOF (which changed `NS.F`→`F` and broke every composite → reverted_noncompile).
    _nstext = "import Mathlib\n\nnamespace NS\n\ntheorem F : True := by sorry\n\ntheorem G : True := by sorry\n\nend NS\n"
    _nt, _nm = _supersede_in_place(_nstext, "F", "theorem F : True := trivial")
    ok("supersede in-place: F kept INSIDE the namespace (not relocated to EOF)",
       _nt is not None and _nt.index("theorem F : True := trivial") < _nt.index("end NS"))
    _nt2, _ = _supersede_in_place(_nt, "G", "theorem G : True := F")
    ok("supersede in-place: composite G cites F and both stay in scope",
       _nt2 is not None and "theorem G : True := F" in _nt2 and "theorem F : True := trivial" in _nt2)
    _nt3, _nm3 = _supersede_in_place(_nstext, "F", "theorem aux : True := trivial\ntheorem F : True := aux")
    ok("supersede in-place: inline helper content-stable-renamed (no cross-lemma collision)",
       _nt3 is not None and any(n.startswith("aux__") for n in _nm3) and "aux__" in _nt3)
    os.path.exists(supenv) and os.remove(supenv); os.path.exists(supenv + ".mdl.json") and os.remove(supenv + ".mdl.json")
    os.path.exists(nsenv) and os.remove(nsenv)
    os.path.exists(nsenv + ".mdl.json") and os.remove(nsenv + ".mdl.json")
    os.path.exists(env) and os.remove(env)
    os.path.exists(env + ".mdl.json") and os.remove(env + ".mdl.json")

    # --- event-sourcing: bank events log + view re-derivation (the derived-view leg) ---
    be = tempfile.mktemp(suffix=".bank_events.jsonl")
    os.environ["ZTARE_LEANMILL_BANK_EVENTS"] = be
    try:
        esv = tempfile.mktemp(suffix=".lean")
        init_context(esv, "import Mathlib\n")
        _rv_ok = lambda path, root: "NoSuchThing" not in Path(path).read_text(encoding="utf-8")
        r1 = bank_decl_to_env(esv, "es_lemma", "theorem es_lemma (n:Nat): n+0=n := by simp", ".", reverify_fn=_rv_ok)
        ok("es: bank emitted to event log", bool(r1["banked_as"]))
        evs = read_bank_events(be)
        ok("es: one event recorded with substrate+name", len(evs) == 1
           and evs[0]["substrate"] == Path(esv).name and evs[0]["name"] == r1["banked_as"])
        ok("es: event carries node provenance (underscore-prefixed)", "_node" in evs[0])
        ok("es: event decl_text replays the rung", "n+0=n" in evs[0]["decl_text"])
        # rederive into a FRESH context (simulating a fresh node / post-merge reconcile)
        fresh = tempfile.mktemp(suffix=".lean")
        # the fresh node must use the SAME substrate basename for events to match → copy name via symlink-ish
        fresh = str(Path(fresh).with_name(Path(esv).name))
        init_context(fresh, "import Mathlib\n")
        rr = rederive_library_from_events(fresh, ".", evs, reverify_fn=_rv_ok)
        ok("es: rederive rebuilt the rung from the event log", rr["rederived"] == 1)
        ok("es: rederived .lean contains the banked rung", "n+0=n" in Path(fresh).read_text(encoding="utf-8"))
        # idempotent: a second rederive from the same events yields the same library
        body1 = Path(fresh).read_text(encoding="utf-8")
        rederive_library_from_events(fresh, ".", evs, reverify_fn=_rv_ok)
        ok("es: rederive is idempotent", Path(fresh).read_text(encoding="utf-8") == body1)
        # a non-compiling view is rejected; the prior known-good .lean is kept
        bad_ev = [{"substrate": Path(fresh).name, "name": "bad__x", "decl_text": "theorem bad__x : True := NoSuchThing"}]
        rr_bad = rederive_library_from_events(fresh, ".", evs + bad_ev, reverify_fn=_rv_ok)
        ok("es: non-compiling rederive rejected, previous kept",
           rr_bad["reason"] == "reverify_failed"
           and Path(fresh).read_text(encoding="utf-8") == body1)
        for f in (esv, fresh, esv + ".mdl.json", fresh + ".mdl.json"):
            os.path.exists(f) and os.remove(f)
    finally:
        os.environ.pop("ZTARE_LEANMILL_BANK_EVENTS", None)
        os.path.exists(be) and os.remove(be)

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_self_test())
