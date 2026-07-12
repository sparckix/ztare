"""No-good store — the REFUTATION DUAL of `proof_cache.ProofCache` (the COMPRESS/win store).

`proof_cache` memoizes VERIFIED proofs (wins); this memoizes CONFIRMED REFUTATIONS (no-goods):
a probe that governance/kernel REJECTED, keyed by the SAME normalized statement, carrying the
distinguishing witness + a failure class. The CEGIS/CDCL "no-good clause" mechanism (counterexample-
guided inductive synthesis + SAT conflict-driven clause learning) — surfaced as the one genuinely-new
dual-purpose borrow by the 2026-06-05 external-comparison workflow (beyond the #36 mining): leanmill
recorded each rejection only to a per-run AUDIT certificate (`adhoc_closure_certificates.jsonl`) and
then DISCARDED the witness, so the same gamed/dead-end shape could recur. Here the witness is recycled.

EXTENSION POINT (cited; not a parallel build): this sits beside `proof_cache.py` in the solver
package and REUSES its key function (`normalize_statement`/`_key_for`) — one source of truth for the
statement key. The store file is `OUT_DIR/solver_lane_no_good_store.jsonl`, the dual of
`solver_lane_proof_cache.jsonl`.

SCOPE (this module = the no-regret, A/B-INDEPENDENT calibration rig; the search-side is DEFERRED):
  - RECORD a refutation (only a CONFIRMED one — the CDCL soundness invariant) and INFORM the leaf via
    `prompt_block` (the READ-side: "these probes were refuted, do not repeat — here is the witness").
  - It NEVER blocks a path. The SEARCH-side forbid/down-rank in `governed_dag_search` (the §3b shared-
    infra change whose lift depends on the in-flight PutnamBench cascade-vs-DAG A/B — B "variant
    library" vs C "no-good" compete for the same budget) is intentionally NOT wired here. It needs the
    A/B verdict + an adversarial-survival pass first (infra/forcing-function change ⇒ adversary before
    trust). Recording + prompt-injection is no-regret and independent of that verdict.

SOUNDNESS (CDCL property: a learned clause is logically valid — it never excludes a satisfying
assignment). Two guards make a recorded no-good unable to suppress a genuinely-closable proof:
  1. record ONLY a CONFIRMED refutation (`confirmed=True` required) — never a flaky/inconclusive
     "didn't fire" (the standing rule: a negative is INADMISSIBLE without calibration).
  2. `matches`/`prompt_block` only INFORM generation; they cannot close OR block, so even an over-broad
     key can at worst nudge the leaf prompt, never prune a path. The `_selftest` ships the POSITIVE
     control (the real P1 cheat CLASS — a `definition_altered` refutation recorded + surfaced) AND the
     NEGATIVE control (a SOUND add-only probe is NOT recorded) through the SAME code path — the
     positive+negative-controls-through-one-path discipline, before anything consumes the store.
"""
from __future__ import annotations
import json
from pathlib import Path
import re

from ztare.common.conflict_ledger import ConflictClause, ConflictLedger

# REUSE the canonical key (decl-name- + whitespace-agnostic, equiv-flag-aware) — do NOT duplicate the
# normalizer; the no-good must hit on the SAME key the proof cache uses, so a refuted statement and its
# later identical re-statement collapse regardless of the local name the leaf gave it.
from ztare.leanmill.solver.proof_cache import _key_for, normalize_statement  # noqa: F401  (re-exported)

# Failure classes — the token a consumer keys on. Sourced from the EXOGENOUS organs' own witness
# strings (statement_integrity violations, v33/governance_organs reasons, conjecture_advances rejects),
# never narrated by the leaf. Kept small + mechanism-named (not effect-named).
FAILURE_CLASSES = (
    "definition_altered",        # statement_integrity: a depended-on decl was modified (the P1 cheat)
    "target_signature_altered",  # statement_integrity: the target statement itself was changed
    "deleted_decl",              # statement_integrity: an original decl is missing from the probe
    "non_load_bearing_lemma",    # conjecture_advances: cited lemma compiles with `:= True` (unused)
    "vacuous_closure",           # nondegenerate_instance_probe / v33: the statement is vacuously true
    "sz_falsified",              # randomized differential probe: a mutant closed (proof not genuine)
    "kernel_laundering",         # v33 anti-laundering: leakage / paraphrase / single-lemma
    "statement_false",           # the STATEMENT itself is kernel-FALSE (¬G proven) — a mis-formalization, not a
    #                              bad proof; recorded so the faithfulness reference() never gates a strengthened
    #                              reformalization against a refuted rendering (2026-06-23, the single ledger).
    "other",
)


def _target_name_from_statement(statement: str) -> str:
    m = re.search(r"(?m)^\s*(?:theorem|lemma|example)\s+([A-Za-z_][\w'.]*)", statement or "")
    return m.group(1) if m else ""


def _emit_no_good_verdict(statement: str, failure_class: str, witness: str, *, source: str = "") -> None:
    try:
        from ztare.leanmill.control_plane import StatementId, Verdict, VerdictKind
        from ztare.leanmill.verdict_store import emit_verdict
        emit_verdict(Verdict(
            kind=(VerdictKind.REFUTED if failure_class == "statement_false"
                  else VerdictKind.REJECTED_BY_GOVERNANCE),
            statement_id=StatementId.from_parts(
                target_name=_target_name_from_statement(statement),
                source_text=statement,
                closed_prop=normalize_statement(statement),
            ),
            provenance="no_good_store.confirmed_no_good",
            detail=(witness or "")[:600],
        ), extra={"source": source or "", "failure_class": failure_class})
    except Exception:  # noqa: BLE001 - telemetry must never affect no-good recording
        pass


def _statement_id_json(statement: str) -> dict:
    try:
        from ztare.leanmill.control_plane import StatementId
        return StatementId.from_parts(
            target_name=_target_name_from_statement(statement),
            source_text=statement,
            closed_prop=normalize_statement(statement),
        ).to_json()
    except Exception:  # noqa: BLE001 - legacy key remains authoritative
        return {}


def failure_class_of(witness: str) -> str:
    """Map a raw organ witness string to a failure class. statement_integrity violations are
    `"<class>: <detail>"`; everything else falls back by keyword, then `other`."""
    head = (witness or "").split(":", 1)[0].strip().lower()
    if head in FAILURE_CLASSES:
        return head
    w = (witness or "").lower()
    if "deleted" in head or "missing from the probe" in w:
        return "deleted_decl"
    if "signature" in head:
        return "target_signature_altered"
    if "definition_altered" in head or "was modified" in w:
        return "definition_altered"
    if "load-bearing" in w or "load_bearing" in w or "cited but unused" in w:
        return "non_load_bearing_lemma"
    if "vacu" in w or "degenerate" in w:
        return "vacuous_closure"
    if "mutant" in w or "schwartz" in w or "differential" in w:
        return "sz_falsified"
    if "leak" in w or "paraphrase" in w or "single-lemma" in w or "single_lemma" in w:
        return "kernel_laundering"
    return "other"


class NoGoodStore:
    """Persistent JSONL-backed store of {normalized statement -> [confirmed refutation tokens]}.

    Append-only on disk (an audit trail of every recorded no-good); deduped in memory on the tuple
    (key, failure_class, witness) so the SAME statement can carry several distinct no-goods but an
    identical one is not double-counted. Mirrors `ProofCache`'s load/append idiom exactly.
    """

    def __init__(self, path: "str | Path"):
        self.path = Path(path)
        self._mem: dict[str, list[dict]] = {}
        self._seen: set = set()
        if self.path.exists():
            for line in self.path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                self._index(r)

    def _index(self, rec: dict) -> bool:
        key = rec.get("key")
        sig = (key, rec.get("failure_class"), rec.get("witness"))
        if not key or sig in self._seen:
            return False
        self._seen.add(sig)
        self._mem.setdefault(key, []).append(rec)
        return True

    def record(self, statement: str, failure_class: str, witness: str,
               *, confirmed: bool, source: str = "") -> bool:
        """Record a CONFIRMED refutation. Returns True if newly added.

        `confirmed` is REQUIRED and must be True — a recorded no-good asserts the shape was genuinely
        refuted by an exogenous organ. A flaky/inconclusive "didn't fire" must NEVER be recorded (it is
        the inadmissible-negative failure mode: it would let a tooling hiccup masquerade as a permanent
        no-good). Caller passes `confirmed=True` only when the organ returned a CONFIRMED verdict."""
        if not confirmed:
            return False
        key = _key_for(statement)
        if not key or not (witness or "").strip():
            return False
        fc = failure_class if failure_class in FAILURE_CLASSES else failure_class_of(witness)
        rec = {"key": key, "statement": statement.strip(), "failure_class": fc,
               "witness": witness.strip(), "source": source}
        sid = _statement_id_json(statement)
        if sid:
            rec["statement_id"] = sid
        if not self._index(rec):
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Shared fact logs can be written by several campaign workers.  The
        # in-memory dedupe is local; the locked append is the cross-process
        # integrity boundary, with convergence handling duplicate facts later.
        from ztare.leanmill.common import append_jsonl_locked
        append_jsonl_locked(self.path, rec)
        _emit_no_good_verdict(statement, fc, witness, source=source)
        return True

    def learn(self, conflict_receipt) -> ConflictClause:
        statement = str((conflict_receipt or {}).get("statement") or (conflict_receipt or {}).get("candidate_signature") or "")
        failure_class = str((conflict_receipt or {}).get("failure_class") or "other")
        witness = str((conflict_receipt or {}).get("witness_summary") or (conflict_receipt or {}).get("witness") or "")
        source = str((conflict_receipt or {}).get("source") or "")
        self.record(statement, failure_class, witness, confirmed=True, source=source)
        return ConflictClause(
            signature=_key_for(statement),
            receipts_refs=tuple(str(x) for x in (conflict_receipt or {}).get("receipts_refs", ()) if str(x).strip()),
            witness_summary=witness,
            provenance=(conflict_receipt or {}).get("provenance", "no_good_store.confirmed_no_good"),
            defeasible=bool((conflict_receipt or {}).get("defeasible", False)),
        )

    def blocks(self, candidate_signature: str) -> "ConflictClause | None":
        hits = self.matches(candidate_signature)
        if not hits:
            return None
        h = hits[-1]
        return ConflictClause(
            signature=_key_for(candidate_signature),
            receipts_refs=tuple(),
            witness_summary=h.get("witness", ""),
            provenance=h.get("source") or "no_good_store.confirmed_no_good",
            defeasible=h.get("failure_class") != "statement_false",
        )

    def revive(self, evidence_card):
        if isinstance(evidence_card, dict) and evidence_card.get("statement"):
            return self.record(
                evidence_card["statement"],
                str(evidence_card.get("failure_class") or "other"),
                str(evidence_card.get("witness") or evidence_card.get("witness_summary") or ""),
                confirmed=bool(evidence_card.get("confirmed", True)),
                source=str(evidence_card.get("source") or ""),
            )
        return evidence_card

    def open_clauses(self) -> list[ConflictClause]:
        out: list[ConflictClause] = []
        for recs in self._mem.values():
            for rec in recs:
                out.append(ConflictClause(
                    signature=rec.get("key", ""),
                    receipts_refs=tuple(),
                    witness_summary=rec.get("witness", ""),
                    provenance=rec.get("source") or "no_good_store.confirmed_no_good",
                    defeasible=rec.get("failure_class") != "statement_false",
                ))
        return out

    def record_integrity_verdict(self, statement: str, verdict, *, source: str = "") -> int:
        """Adapter — turn a FAILED `statement_integrity.IntegrityVerdict` into no-goods. The integrity
        check is deterministic + exogenous (a decl diff, no LLM), so an `ok=False` verdict IS a
        confirmed refutation; each violation string becomes one no-good. Returns the count recorded.
        A passing verdict (ok=True) records NOTHING — a SOUND probe is never turned into a no-good
        (the fail-open / never-block-a-closable-path guarantee). Accepts a verdict object with
        `.ok`/`.violations` or the equivalent dict (`{"ok":..., "violations":[...]}`)."""
        ok = getattr(verdict, "ok", None)
        violations = getattr(verdict, "violations", None)
        if ok is None and isinstance(verdict, dict):
            ok, violations = verdict.get("ok"), verdict.get("violations")
        if ok is not False:                      # ok True OR unknown ⇒ record nothing (fail-open)
            return 0
        n = 0
        for v in (violations or []):
            if self.record(statement, failure_class_of(v), v, confirmed=True, source=source):
                n += 1
        return n

    def matches(self, statement: str) -> "list[dict]":
        """All confirmed no-goods recorded for this statement's normalized key (possibly empty)."""
        return list(self._mem.get(_key_for(statement), []))

    def statement_false_keys(self) -> set:
        """The set of normalized-statement KEYS recorded as kernel-FALSE (failure class `statement_false`, i.e.
        ¬G proven — a mis-formalization, not a bad proof). The faithfulness store's `reference()` consults THIS
        (the single refutation ledger) so a refuted rendering never gates a strengthened reformalization — one
        ledger + one canonical key, no parallel surface. Keys only (the consumer just needs membership)."""
        return {k for k, recs in self._mem.items()
                if any(r.get("failure_class") == "statement_false" for r in recs)}

    def statement_false_witness(self, statement: str) -> str:
        """READ-side: the recorded `statement_false` WITNESS (the counterexample NUGGET) for this statement, or "".
        The CEGIS/CDCL no-good clause RECYCLED as a refutation seed: `conjecture.falsify_generate`'s `nugget`
        reads this so a re-attempt/re-run of the SAME goal (canonical `_key_for`) ADAPTS the known crux instead of
        re-deriving it from scratch. Advisory only — the skeptic still proves ¬(OUR goal) and the kernel re-checks
        it, so a stale witness merely fails to help. Most-recently recorded witness wins."""
        from ztare.leanmill.solver.proof_cache import _key_for
        recs = [r for r in self._mem.get(_key_for(statement), [])
                if r.get("failure_class") == "statement_false" and (r.get("witness") or "").strip()]
        return (recs[-1].get("witness") or "") if recs else ""

    def prompt_block(self, statement: str, max_items: int = 4) -> str:
        """READ-side: render the recorded no-goods as a leaf-prompt block. Empty string if none — so a
        caller can unconditionally append it. Informs generation only; it does not (and must not) close
        or block anything."""
        hits = self.matches(statement)
        if not hits:
            return ""
        lines = ["-- ⚠ PRIOR REFUTED ATTEMPTS for this goal (do NOT repeat these — they were rejected "
                 "by exogenous governance, not by a tooling error):"]
        for h in hits[:max_items]:
            lines.append(f"--   [{h.get('failure_class')}] {h.get('witness')}")
        if len(hits) > max_items:
            lines.append(f"--   … and {len(hits) - max_items} more.")
        lines.append("-- Prove the statement EXACTLY AS GIVEN, genuinely; alter NO definition the "
                     "target depends on; introduce NO vacuity; cite lemmas that are load-bearing.")
        return "\n".join(lines)

    def __len__(self) -> int:
        return sum(len(v) for v in self._mem.values())

    def stats(self) -> dict:
        from collections import Counter
        c = Counter(r.get("failure_class") for v in self._mem.values() for r in v)
        return {"n": len(self), "n_keys": len(self._mem), "by_class": dict(c)}


def _selftest() -> int:
    import tempfile, os
    fails = []

    def ok(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    db = tempfile.mktemp(suffix=".jsonl")
    s = NoGoodStore(db)
    ok("empty matches", s.matches("theorem foo : P") == [])
    ok("empty prompt_block is ''", s.prompt_block("theorem foo : P") == "")

    # record a confirmed no-good → surfaced; name-agnostic key (mirrors proof_cache)
    ok("record confirmed", s.record("theorem foo : P", "vacuous_closure",
                                     "statement is vacuously true (S=∅)", confirmed=True, source="t"))
    ok("matches after record", len(s.matches("theorem foo : P")) == 1)
    ok("name-agnostic surface", len(s.matches("theorem bar : P := sorry")) == 1)
    ok("prompt_block names the witness", "vacuously true" in s.prompt_block("theorem foo : P"))
    ok("duplicate not double-counted", s.record("theorem foo : P", "vacuous_closure",
                                                 "statement is vacuously true (S=∅)",
                                                 confirmed=True) is False)

    # CALIBRATION — a non-confirmed negative is INADMISSIBLE (the standing rule)
    ok("unconfirmed rejected", s.record("theorem g : Q", "other", "maybe failed?",
                                        confirmed=False) is False)
    ok("unconfirmed not stored", s.matches("theorem g : Q") == [])

    # ---- POSITIVE control: the REAL P1 cheat CLASS, through statement_integrity (deterministic) ----
    from ztare.leanmill.solver import statement_integrity as si
    original = ("import Mathlib\n\ndef helper_corpus : Nat := 0\n\n"
                "theorem tgt : helper_corpus = 0 := by sorry\n")
    # the cheat: AGENT WEAKENED a depended-on def to make the goal trivial (the P1 algebraicFunctionPoint
    # move, in miniature) — statement_integrity flags `definition_altered`, exactly as it did on P1.
    cheat = ("import Mathlib\n\ndef helper_corpus : Nat := 1\n\n"
             "theorem tgt : helper_corpus = 1 := by rfl\n")
    v_cheat = si.check(original, cheat, "tgt")
    ok("positive: integrity FLAGS the cheat", v_cheat.ok is False)
    n = s.record_integrity_verdict("theorem tgt : helper_corpus = 0", v_cheat, source="p1_class")
    ok("positive: cheat recorded as no-good(s)", n >= 1)
    ok("positive: a definition/signature class present",
       any(m["failure_class"] in ("definition_altered", "target_signature_altered")
           for m in s.matches("theorem tgt : helper_corpus = 0")))
    ok("positive: prompt_block names the altered decl",
       "helper_corpus" in s.prompt_block("theorem tgt : helper_corpus = 0"))

    # ---- NEGATIVE control: a SOUND add-only probe is NEVER turned into a no-good (fail-open) ----
    # Use a DISTINCT, never-refuted goal (`other_corpus = 5`) so it does NOT collapse onto the
    # positive control's key. (A sound RE-attempt at the SAME statement as a prior cheat WOULD
    # legitimately surface the warning — keying is by statement, not by attempt; that is the
    # `name-agnostic surface` assertion above. The fail-open guarantee under test here is the
    # different claim: a sound attempt at a goal that was never refuted carries no no-good.)
    sound = ("import Mathlib\n\ndef other_corpus : Nat := 5\n\n"
             "theorem lemma_aux : other_corpus = 5 := rfl\n\n"
             "theorem tgt2 : other_corpus = 5 := by exact lemma_aux\n")
    orig2 = ("import Mathlib\n\ndef other_corpus : Nat := 5\n\n"
             "theorem tgt2 : other_corpus = 5 := by sorry\n")
    v_sound = si.check(orig2, sound, "tgt2")
    ok("negative: integrity PASSES the sound probe", v_sound.ok is True)
    n0 = s.record_integrity_verdict("theorem tgt2 : other_corpus = 5", v_sound, source="sound_ctrl")
    ok("negative: sound probe records NOTHING", n0 == 0)
    ok("negative: never-refuted sound goal has no no-good (never blocks a closable path)",
       s.matches("theorem tgt2 : other_corpus = 5") == [])

    # persistence across reopen
    s2 = NoGoodStore(db)
    ok("persisted across reopen", len(s2.matches("theorem foo : P")) == 1 and len(s2) == len(s))
    os.remove(db)

    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys
    sys.exit(_selftest())
