"""Faithfulness store — the FAITHFULNESS DUAL of `no_good_store` / `proof_cache` (the 10x the 2026-06-10
3-axis self-learning inventory found missing).

`proof_cache` memoizes verified PROOFs; `no_good_store` memoizes confirmed REFUTATIONS; this memoizes
confirmed FAITHFULNESS CORRESPONDENCES (NL ↔ the agreed formal statement) + cross-substrate CONFLICTS
(known mistranslation traps). The inventory's headline: the autoformalize / faithfulness axis is the ONLY
axis that learns NOTHING persistent — every firewall verdict (compile / round-trip / cross-vote kernel-
equivalence cliques / structural fingerprint) is recomputed COLD and discarded, even though the cross-vote
leg pays N cold Mathlib `↔` compiles each time, and `structural_faithfulness` runs in NO-OP advisory mode
because production never feeds it a stored reference (`autoformalize.py:221-222`). This store is the cached
dual:

  • a re-seen NL recalls its AGREED faithful statement (skip re-dispatching the formalizer panel);
  • an exact reference(nl) can feed the structural identity guard; semantic neighbours are generation-only
    leads and never supply a fingerprint, defeq comparand, or reuse statement;
  • a recorded cross-substrate `faithfulness_conflict` (from `cross_substrate_consensus`) is a translation-
    bug MEMO — "this NL has a known mistranslation trap" — the faithfulness analogue of a no-good.

EXTENSION POINT (cited, NOT a parallel build): sits beside `proof_cache.py` / `no_good_store.py` in the
solver package, mirrors their JSONL load/append idiom + the CONFIRMED-only soundness invariant. Store file
`OUT_DIR/solver_lane_faithfulness_store.jsonl`. It INFORMS generation (recall + reference + prompt_block); it
NEVER admits or blocks — the firewall's kernel legs remain the SOLE faithfulness arbiter, so even an
over-broad NL key can at worst surface a stale reference, never admit an unfaithful statement.

SOUNDNESS (mirrors no_good_store's CDCL discipline): record a correspondence ONLY when the firewall
CONFIRMED it faithful (`confirmed=True`) — a flaky/advisory admit is INADMISSIBLE (the standing rule: a
verdict is inadmissible without calibration). The selftest ships the POSITIVE control (a confirmed
correspondence recorded + recalled) AND the NEGATIVE control (an unconfirmed admit is NOT recorded) through
the SAME code path before anything consumes the store.

  python -m ztare.leanmill.solver.faithfulness_store --selftest
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path


def nl_key(nl: str) -> str:
    """The retrieval key for a natural-language claim — lowercase, whitespace-collapsed, stripped of
    surrounding punctuation (so a trivial paraphrase still hits). Coarse ON PURPOSE: the firewall re-checks
    faithfulness on a hit, so an over-broad key only ever surfaces a stale reference, never admits a wrong one."""
    return re.sub(r"\s+", " ", (nl or "").strip().lower()).strip(" .;:!?")


def _scoped_key(nl: str) -> str:
    """The `nl_key` NAMESPACED by the current substrate's def-vocabulary fingerprint — the general-purpose,
    single-door cure for SUBSTRATE-BLIND reuse (2026-07-05, CLOB: v2's existential `Marketable` rendering was
    reused verbatim over v3's decidable substrate → the proof stalled on a def the substrate no longer had). A
    record written against one vocabulary lands under `<fp>\\0<nl>`; a read against a DIFFERENT vocabulary looks up
    `<fp'>\\0<nl>` and misses → re-derive fresh. Reuse is preserved on a STABLE substrate (same fp every run) and
    correctly invalidated only when a meaning-bearing def changes. FLAT (no prefix) when no substrate is registered
    ⇒ non-campaign reuse keeps its original namespace. Applied at EVERY read+write key so scoping is transparent."""
    base = nl_key(nl)
    try:
        from ztare.formal.repl_compile import current_substrate_fingerprint as _cfp
        fp = _cfp()
    except Exception:  # noqa: BLE001 — no fingerprint ⇒ flat namespace (never breaks reuse)
        fp = ""
    return f"{fp}\x00{base}" if fp else base



def _stmt_identity(statement: str) -> str:
    """The NAME-AGNOSTIC identity of a Lean statement — the SAME normalizer the proof_cache keys on
    (`normalize_statement`: decl-name- and whitespace-agnostic, extracts the last theorem). This is THE single
    door for "is this the same statement?" (2026-07-03 RCA): the #105 prior-confirmed short-circuit rolled its
    own EXACT-string compare that INCLUDED the theorem name, so the formalizer's run-to-run name non-determinism
    (`admissible_user_sequence…` vs `reachable_state_solvency_guarded_actions` — same Prop, different name)
    defeated it and the flaky round-trip judge re-litigated a re-confirmed target. Route every store-side identity
    check through here so name non-determinism can never break reuse again. Fail-open to whitespace-normalize
    (advisory store; a missing normalizer only costs a short-circuit, never admits anything)."""
    try:
        # α-/∀-fronting-tolerant normalizer (2026-07-05): the plain `normalize_statement` was only name+whitespace
        # agnostic, so the formalizer's run-to-run RESTYLING (bound-var renames, ∀-fronted vs param-bound) defeated
        # the prior-confirmed short-circuit → every re-run paid a full re-formalize + firewall (the RBAC "why is it
        # slow after hours" RCA: 0 confirms()-hits despite banked lemmas). `normalize_statement_equiv` collapses the
        # α-variants the proof-cache already keys on — the SAME single door, one tier stronger.
        from ztare.leanmill.solver.proof_cache import normalize_statement_equiv as _nse
        return _nse(statement or "")
    except Exception:  # noqa: BLE001 — no normalizer ⇒ coarse fallback (still name-BEARING, but never wrong)
        try:
            from ztare.leanmill.solver.proof_cache import normalize_statement as _ns
            return _ns(statement or "")
        except Exception:  # noqa: BLE001
            return " ".join((statement or "").split())


def _target_name_from_statement(statement: str) -> str:
    m = re.search(r"(?m)^\s*(?:theorem|lemma|example)\s+([A-Za-z_][\w'.]*)", statement or "")
    return m.group(1) if m else ""


def _statement_id_json(nl: str, statement: str) -> dict:
    try:
        from ztare.leanmill.control_plane import StatementId
        return StatementId.from_parts(
            target_name=_target_name_from_statement(statement),
            source_text=statement,
            closed_prop=_stmt_identity(statement),
            nl_exact=nl,
        ).to_json()
    except Exception:  # noqa: BLE001 - legacy `norm` remains authoritative
        return {}


class FaithfulnessStore:
    """Persistent JSONL store of {nl_key -> [confirmed correspondence | conflict records]}. Append-only on
    disk (an audit trail); deduped in memory on (key, kind, statement|distinguishing). Mirrors `NoGoodStore`."""

    def __init__(self, path: "str | Path"):
        self.path = Path(path)
        self._mem: "dict[str, list[dict]]" = {}
        self._seen: set = set()
        self._emb_index: "list[tuple[dict, list]] | None" = None   # lazy NL-embedding index for semantic reference()
        self._emb_n: int = -1                                       # candidate count the index was built for (rebuild if grown)
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        self._index(json.loads(line))
                    except Exception:  # noqa: BLE001
                        continue

    def _index(self, rec: dict) -> bool:
        key = rec.get("key")
        sig = (key, rec.get("kind"), rec.get("statement") or rec.get("distinguishing"))
        if not key or sig in self._seen:
            return False
        self._seen.add(sig)
        self._mem.setdefault(key, []).append(rec)
        return True

    def _append(self, rec: dict) -> bool:
        if not self._index(rec):
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return True

    def record(self, nl: str, statement: str, *, confirmed: bool, fingerprint=None, source: str = "") -> bool:
        """Record a CONFIRMED faithful correspondence NL→statement (the firewall ADMITTED it). CONFIRMED-only —
        a flaky/advisory admit is INADMISSIBLE. `fingerprint` is the agreed statement's structural fingerprint
        (for the load-bearing reference check). Returns whether newly stored."""
        if not confirmed or not (nl or "").strip() or not (statement or "").strip():
            return False
        rec = {"key": _scoped_key(nl), "kind": "faithful", "nl": (nl or "")[:400],
               # STORE THE STATEMENT WHOLE — NO raw-char cap (2026-07-03). A Lean statement is a bounded
               # semantic object; a char budget (was 4000/600) is an ARBITRARY line that bisects a
               # def-heavy target's THEOREM, so the formalizer anchor (`prompt_block`) and the
               # kernel-defeq reference lose the conclusion → the formalizer improvises a weaker conjunct
               # → structural correctly rejects → the target can never re-close. The correctness-bearing
               # MATCH is `norm` (the complete, name-agnostic theorem, always small) — never truncated.
               # The `statement` is the anchor/reference and must be complete, so it is kept whole.
               "statement": statement.strip(),
               # NAME-AGNOSTIC identity key, computed on the FULL statement BEFORE truncation — the
               # single door `confirms()` matches on. Survives both the formalizer's theorem-name
               # non-determinism AND the 4000-char truncation (the normalized theorem is small).
               "norm": _stmt_identity(statement),
               "fingerprint": fingerprint, "source": source}
        sid = _statement_id_json(nl, statement)
        if sid:
            rec["statement_id"] = sid
        return self._append(rec)

    def record_conflict(self, nl: str, substrates: "list[str]", distinguishing: str, *, source: str = "") -> bool:
        """Record a cross-substrate FAITHFULNESS CONFLICT — ≥2 substrates disagreed on the same NL claim ⇒ a
        localized mistranslation (a 'do not trust a naive rendering here' memo). Disagreement IS the exogenous
        confirmation, so no separate `confirmed` flag is needed."""
        if not (nl or "").strip():
            return False
        return self._append({"key": _scoped_key(nl), "kind": "conflict", "nl": (nl or "")[:400],
                             "substrates": list(substrates or []), "distinguishing": (distinguishing or "")[:300],
                             "source": source})

    def reference(self, nl: str) -> "dict | None":
        """The stored faithful reference for an NL (the most-recent confirmed correspondence NOT marked
        kernel-FALSE): {statement, fingerprint}. Exact references can strengthen the identity guard and enable
        exact-key reuse; semantic references are
        advisory generation leads only and never gate or skip re-formalization.
        EXCLUDES any rendering the ONE refutation ledger (`NoGoodStore`, failure class `statement_false`, keyed by
        the canonical statement normalizer) marked kernel-FALSE — a refuted faithful-but-false reference must
        never gate a STRENGTHENED reformalization (else the firewall rejects the corrected statement: the
        operator-caught false-negative). Single source of refutations — NO parallel store here. None if unseen or
        every confirmed rendering has since been refuted."""
        recs = [r for r in self._mem.get(_scoped_key(nl), []) if r.get("kind") == "faithful"]
        if not recs:
            _sem = self._semantic_reference(nl)   # exact key MISS → semantic fallback (survives phrasing/decomposition change)
            if _sem is not None:
                _sem = {**_sem, "exact": False}   # semantic lead: it must not gate or skip re-formalization
            return _sem                            # re-formalization (else adding a HYPOTHESIS is seen as a rephrase → stale reuse)
        _refuted = self._refuted_keys()
        # SUBSTRATE-DRIFT exclusion (2026-07-05, the CLOB reuse-ghost the morning's sufficient-statistic reuse
        # exposed): a rendering confirmed faithful BEFORE the drift gate existed (or against a since-updated
        # substrate) can DRIFT from the CURRENT substrate — a WEAKER carrier (`[LinearOrder K]` → `[LT K][LE K]`) or a
        # divergent def body — a DIFFERENT Prop the firewall now rejects. Served as the reuse SEED it replays the
        # ghost forever (skips the live formalizer, where the carrier-context note fixes it) → reject loop, never
        # closes. The substrate is the source of truth: exclude it HERE, at the ONE retrieval door, exactly as
        # refuted renderings are excluded — through the SAME `substrate_infidelities` predicate the firewall + falsify
        # gates use (one drift definition, three enforcement sites). No substrate/reader ⇒ always-False ⇒ byte-parity.
        _drift = self._substrate_drift_pred()
        try:
            from ztare.leanmill.solver.proof_cache import _key_for as _kf
        except Exception:  # noqa: BLE001 — no normalizer ⇒ can't check refuted; still apply the drift filter
            _kf = None
        for r in reversed(recs):                       # most-recent confirmed correspondence, not refuted, not drifted
            _s = r.get("statement") or ""
            if _drift(_s):
                continue
            if _refuted and _kf and _kf(_s) in _refuted:
                continue
            return {"statement": _s, "fingerprint": r.get("fingerprint"), "exact": True}
        return None

    def _substrate_drift_pred(self):
        """A predicate `stmt -> bool` flagging a stored rendering that DRIFTS from the CURRENT campaign substrate
        (weaker carrier or divergent def body) — the ONE `lean_source.substrate_infidelities` door the firewall and
        falsify gates also use. No substrate / no reader ⇒ always-False (no exclusion ⇒ byte-parity off-campaign).
        Reads the substrate ONCE per call (retrieval is not hot); a read/import failure fails SAFE to no-exclusion."""
        try:
            from ztare.formal.repl_compile import get_campaign_substrate
            from ztare.leanmill.lean_source import substrate_infidelities
            cs = get_campaign_substrate()
            if not cs or not Path(cs).exists():
                return lambda _s: False
            sub = Path(cs).read_text(encoding="utf-8", errors="replace")
            return lambda _s: bool((_s or "").strip()) and bool(substrate_infidelities(_s, sub))
        except Exception:  # noqa: BLE001 — advisory; never break retrieval
            return lambda _s: False

    def _semantic_reference(self, nl: str, threshold: "float | None" = None) -> "dict | None":
        """SEMANTIC fallback for `reference()` (2026-07-04, the reuse-churn once-and-for-all). The exact `nl_key`
        match is brittle to PHRASING: an AGNOSTIC re-authored blueprint (or a planner that decomposes the target
        itself) emits a semantically-EQUIVALENT sub-lemma NL under different words, so the exact key misses and a
        CONFIRMED rendering is re-formalized from scratch (the CLOB regression: 8 codex re-formalize dispatches
        with 19 reusable renderings in the store). Retrieve the NEAREST stored faithful NL by LOCAL-embedding
        cosine (no API/key — `_embed_local`); return its rendering when sim ≥ threshold and it is not refuted.
        SOUND, not laundering: the statement is reused only as the FIRST rendering — the FULL firewall (compile /
        round-trip / structural / triviality) re-gates it for THIS nl downstream (autoformalize), so a mis-retrieval
        is REJECTED and falls through to a fresh formalize; it can never admit a weaker/different Prop. Retrieval =
        affordance; the kernel is the gate. Fail-safe: no embedder ⇒ None (exact-only, today's behaviour).
        ZTARE_LEANMILL_SEMANTIC_REFERENCE=0 reverts."""
        if os.environ.get("ZTARE_LEANMILL_SEMANTIC_REFERENCE", "1") == "0" or not (nl or "").strip():
            return None
        # The cosine floor is POLICY-owned (env `ZTARE_LEANMILL_SEMANTIC_REFERENCE_THRESHOLD` → factory policy
        # `operations.faithfulness.semantic_reference_threshold` → calibrated fallback), never an inline magic
        # number here. Calibrated on all-MiniLM-L6-v2 over real CLOB NLs (correct paraphrase 0.76 / wrong 0.50).
        if threshold is None:
            try:
                from ztare.leanmill.policy import semantic_reference_threshold as _srt
                threshold = _srt()
            except Exception:  # noqa: BLE001 — no policy ⇒ fail SAFE to exact-only (never invent a floor here)
                return None
        try:
            from ztare.common.embeddings import _embed_local, _cos
        except Exception:  # noqa: BLE001 — no embedder ⇒ exact-only, never break the firewall
            return None
        _refuted = self._refuted_keys()
        _drift = self._substrate_drift_pred()   # same ONE door as reference() — a semantic hit must be substrate-faithful too
        cands = [r for recs in self._mem.values() for r in recs
                 if r.get("kind") == "faithful" and (r.get("nl") or "").strip() and (r.get("statement") or "").strip()
                 and _stmt_identity(r.get("statement") or "") not in _refuted and not _drift(r.get("statement") or "")]
        if not cands:
            return None
        # lazy NL-embedding index (built once per store; rebuilt only if the candidate set grew this session)
        if self._emb_index is None or self._emb_n != len(cands):
            try:
                _vecs = _embed_local([r.get("nl") or "" for r in cands], task_type="RETRIEVAL_DOCUMENT")
            except Exception:  # noqa: BLE001 — embedder unavailable/failed ⇒ exact-only
                return None
            self._emb_index = list(zip(cands, _vecs))
            self._emb_n = len(cands)
        try:
            _qv = _embed_local([nl], task_type="RETRIEVAL_QUERY")[0]
        except Exception:  # noqa: BLE001
            return None
        best, best_sim = None, -1.0
        for r, v in self._emb_index:
            s = _cos(_qv, v)
            if s > best_sim:
                best, best_sim = r, s
        if best is not None and best_sim >= threshold:
            return {"statement": best.get("statement"), "fingerprint": best.get("fingerprint"),
                    "semantic_sim": round(best_sim, 3), "semantic_nl": (best.get("nl") or "")[:140]}
        return None

    def confirms(self, nl: str, statement: str) -> bool:
        """THE single door for the #105 prior-confirmed short-circuit: is `statement` a CONFIRMED-faithful
        rendering for this NL — NAME-AGNOSTICALLY? Matches on `_stmt_identity` (the proof_cache normalizer) so the
        formalizer's run-to-run theorem-NAME non-determinism cannot defeat it (2026-07-03 RCA: the old inline
        EXACT-string compare in autoformalize.py included the name ⇒ a re-confirmed target false-rejected on the
        flaky judge). SOUND: skipping the round-trip JUDGE only — the deterministic legs (compile / triviality /
        structural-vs-reference / battery) still run on THIS statement, so this can never admit a weaker/different
        Prop. Legacy records (no `norm`) fall back to normalizing their stored (possibly truncated) statement."""
        cand = _stmt_identity(statement)
        if not cand:
            return False
        for r in self._mem.get(_scoped_key(nl), []):
            if r.get("kind") != "faithful":
                continue
            # RECOMPUTE from the stored statement (do NOT trust the stored `norm` — old records were keyed with the
            # weaker name-only normalizer; recomputing puts both sides through the CURRENT α-tolerant door).
            ident = _stmt_identity(r.get("statement") or "") or r.get("norm")
            if ident and ident == cand:
                return True
        return False

    def refuted_literal(self, nl: str) -> str:
        """The kernel-REFUTED literal rendering for an NL — a correspondence once admitted faithful, now marked
        `statement_false` in the one refutation ledger. This is BOTH the LICENSE (its existence proves the
        literal NL claim is kernel-false) AND the comparand for a disclosed strengthening (the firewall checks
        the strengthened candidate ADDS hypotheses + preserves the conclusion vs THIS). "" when the literal was
        never refuted (⇒ no license ⇒ the firewall stays strict). The license is non-fakeable: it exists only
        because a kernel ¬G was recorded at the single refutation chokepoint."""
        recs = [r for r in self._mem.get(_scoped_key(nl), []) if r.get("kind") == "faithful"]
        if not recs:
            return ""
        refuted = self._refuted_keys()
        if not refuted:
            return ""
        try:
            from ztare.leanmill.solver.proof_cache import _key_for as _kf
        except Exception:  # noqa: BLE001
            return ""
        for r in reversed(recs):
            if _kf(r.get("statement") or "") in refuted:
                return r.get("statement") or ""
        return ""

    def _refuted_keys(self) -> set:
        """The normalized-statement keys the ONE refutation ledger (`NoGoodStore`) marked kernel-FALSE (failure
        class `statement_false`) — consulted by `reference()` so a refuted rendering never gates. Lazy + cached;
        fail-open to empty (the consult is advisory). Same store + canonical key the proof_cache uses — one
        ledger, no parallel surface."""
        cached = getattr(self, "_refuted_cache", None)
        if cached is not None:
            return cached
        keys: set = set()
        try:
            from ztare.leanmill.solver.no_good_store import NoGoodStore
            keys = NoGoodStore(self.path.parent / "solver_lane_no_good_store.jsonl").statement_false_keys()
        except Exception:  # noqa: BLE001 — refutation-ledger consult is advisory; never break the reference
            keys = set()
        self._refuted_cache = keys
        return keys

    def conflicts(self, nl: str) -> "list[dict]":
        return [r for r in self._mem.get(_scoped_key(nl), []) if r.get("kind") == "conflict"]

    def prompt_block(self, nl: str, max_items: int = 3) -> str:
        """Agent-facing: a KNOWN-FAITHFUL rendering to anchor on + any KNOWN mistranslation traps for this NL.
        INFORMS the formalizer; the firewall still re-checks (this can never admit an unfaithful statement)."""
        ref = self.reference(nl)
        confs = self.conflicts(nl)[:max_items]
        if not ref and not confs:
            return ""
        lines: "list[str]" = []
        if ref and ref.get("exact") is True:
            lines.append("PRIOR FAITHFUL RENDERING (anchor on this exact statement if it matches the NL):")
            lines.append("  " + (ref.get("statement") or ""))
        elif ref:
            lines.append(
                "RELATED PRIOR RENDERING (semantic lead only; it is not the identity of this claim; "
                "re-formalize and verify from the current NL):"
            )
            lines.append("  " + (ref.get("statement") or ""))
        if confs:
            lines.append("KNOWN MISTRANSLATION TRAP(S) on this claim — an independent substrate disagreed:")
            for c in confs:
                lines.append(f"  - {', '.join(c.get('substrates') or [])}: {c.get('distinguishing')}")
        return "\n".join(lines) + "\n"

    def stats(self) -> dict:
        n_f = sum(1 for v in self._mem.values() for r in v if r.get("kind") == "faithful")
        n_c = sum(1 for v in self._mem.values() for r in v if r.get("kind") == "conflict")
        return {"n_keys": len(self._mem), "faithful": n_f, "conflict": n_c}

    def __len__(self):
        return sum(len(v) for v in self._mem.values())


def _selftest() -> int:
    import tempfile
    fails: "list[str]" = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    with tempfile.TemporaryDirectory() as d:
        store = FaithfulnessStore(Path(d) / "fs.jsonl")
        NL = "For all natural numbers a and b, a + b = b + a."
        STMT = "theorem t (a b : ℕ) : a + b = b + a := by sorry"

        # POSITIVE control: a CONFIRMED correspondence is recorded + recalled
        ok("records a confirmed faithful correspondence",
           store.record(NL, STMT, confirmed=True, fingerprint={"conclusion_op": "eq"}, source="firewall"))
        ref = store.reference(NL)
        ok("reference() recalls the agreed statement + fingerprint (the load-bearing feed)",
           ref is not None and ref["statement"] == STMT and ref["fingerprint"] == {"conclusion_op": "eq"})
        ok("a whitespace/case paraphrase of the NL hits the SAME key (coarse retrieval)",
           store.reference("  For All Natural Numbers A And B, A + B = B + A  ") is not None
           and store.reference("a different claim about prime factorization") is None)

        # #105 REGRESSION GUARD (2026-07-03): confirms() must be NAME-AGNOSTIC — the formalizer picks a different
        # theorem name each run, and the old exact-string compare let the flaky round-trip judge re-litigate a
        # re-confirmed target. Same Prop under a DIFFERENT name ⇒ still confirmed; a genuinely different Prop ⇒ not.
        ok("confirms() the EXACT stored statement", store.confirms(NL, STMT))
        ok("confirms() a same-Prop statement under a DIFFERENT theorem NAME (the name-non-determinism fix)",
           store.confirms(NL, "theorem renamed_by_a_later_run (a b : ℕ) : a + b = b + a := by sorry"))
        ok("confirms() survives a def-heavy PREAMBLE + name change (truncation-proof via `norm`)",
           store.confirms(NL, "-- big preamble\ndef foo := 1\ntheorem other_name (a b : ℕ) : a + b = b + a := by sorry"))
        ok("confirms() REJECTS a genuinely different Prop under this NL (no false short-circuit)",
           not store.confirms(NL, "theorem t (a b : ℕ) : a + b = a * b := by sorry"))
        ok("confirms() REJECTS an unseen NL", not store.confirms("a totally unseen claim", STMT))

        # NEGATIVE control: an UNCONFIRMED admit is NOT recorded (the inadmissible-without-calibration rule)
        ok("an UNCONFIRMED admit is refused (not recorded)",
           not store.record("some other claim", "theorem u : True := by sorry", confirmed=False))
        ok("the refused unconfirmed claim is absent", store.reference("some other claim") is None)

        # CONFLICT: a cross-substrate disagreement becomes a mistranslation-trap memo
        ok("records a cross-substrate faithfulness conflict",
           store.record_conflict(NL, ["lean", "smt_z3"], "z3: sat at a=0,b=1 (the rendering dropped a hypothesis)"))
        ok("conflicts() recalls the trap", len(store.conflicts(NL)) == 1)

        # prompt_block surfaces BOTH the faithful anchor and the trap to the agent
        blk = store.prompt_block(NL)
        ok("prompt_block surfaces the faithful anchor + the trap",
           "PRIOR FAITHFUL RENDERING" in blk and "MISTRANSLATION TRAP" in blk and "z3: sat" in blk)

        # persistence: a fresh store reloads from disk
        store2 = FaithfulnessStore(Path(d) / "fs.jsonl")
        ok("reloads from JSONL (persistent across process)", store2.reference(NL) is not None)
        ok("dedup: re-recording the same correspondence is a no-op",
           not store2.record(NL, STMT, confirmed=True, fingerprint={"conclusion_op": "eq"}))
        ok("stats: 1 faithful + 1 conflict", store2.stats()["faithful"] == 1 and store2.stats()["conflict"] == 1)

        # SEMANTIC reference (2026-07-04 reuse-churn fix): a PARAPHRASED NL — different words, same intent — that
        # exact-key MISSES must still recall the confirmed rendering (the CLOB agnostic-blueprint case). Skips
        # gracefully if the local embedder is unavailable (exact-only is the fail-safe).
        try:
            from ztare.common.embeddings import _embed_local
            _embed_local(["probe"], task_type="RETRIEVAL_QUERY")   # embedder live?
            _embed_ok = True
        except Exception:  # noqa: BLE001
            _embed_ok = False
        if _embed_ok:
            para = "The sum of any two naturals is unchanged when you swap their order: b + a equals a + b."
            ok("semantic reference() recalls the confirmed rendering for a PARAPHRASED (exact-key-MISS) NL",
               store2.reference(para) is not None and store2.reference(para)["statement"] == STMT)
            ok("semantic reference() does NOT match a semantically-UNRELATED NL (no spurious reuse)",
               store2.reference("The determinant of a product of matrices equals the product of determinants.") is None)
        else:
            print("  [SKIP] semantic reference() — local embedder unavailable (exact-only fail-safe path)")

        # SUBSTRATE-SCOPED reuse (2026-07-05): a record confirmed against one theory vocabulary must NOT be served
        # against a DIFFERENT one (the substrate-blind-reuse cure). Simulate a substrate change via the fingerprint.
        import ztare.formal.repl_compile as _rc
        _saved = _rc.current_substrate_fingerprint
        try:
            _rc.current_substrate_fingerprint = lambda: "FP_A"
            store.record("scoped claim", "theorem sc : Q := by sorry", confirmed=True)
            ok("same-substrate fingerprint → reference HITS", store.reference("scoped claim") is not None)
            _rc.current_substrate_fingerprint = lambda: "FP_B"          # a meaning-bearing def changed
            ok("changed-substrate fingerprint → reference MISSES (stale reuse invalidated)",
               store.reference("scoped claim") is None)
            ok("changed-substrate fingerprint → confirms() MISSES too",
               not store.confirms("scoped claim", "theorem sc : Q := by sorry"))
        finally:
            _rc.current_substrate_fingerprint = _saved

    print("SELFTEST", "PASSED" if not fails else f"FAILED: {fails}")
    return 0 if not fails else 1


if __name__ == "__main__":
    import sys
    sys.exit(_selftest() if "--selftest" in sys.argv else (print(__doc__) or 0))
