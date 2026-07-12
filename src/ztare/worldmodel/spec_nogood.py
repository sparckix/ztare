"""Visible-replay nogoods for the spec-abduction proposer — CDCL learned clauses
that shrink the abduction search ACROSS runs.

RefutedExperimentsLedger records failure families the EXECUTOR killed. This is the
dual for the PROPOSER: when spec_abduction rejects a candidate rule-list on a
VISIBLE replay counterexample (its lowered step_fn predicts the wrong successor on
one of that action's own transitions), the candidate's spec-behavior signature +
the first mismatch is persisted as a ConflictClause. A later run consults the
recorded clauses and skips any candidate that PROVABLY reproduces the recorded
visible counterexample — the same candidate is not re-scored from scratch.

CONTAMINATION FIREWALL (critical). Every clause carries a provenance
``evidence: "visible" | "holdout"`` tag. The proposer may consult ONLY visible
clauses; consulting a holdout clause is training on the rollout holdout and
silently defeats the gate. ``visible_clauses`` filters to evidence=="visible" and
``assert_visible`` raises on any holdout clause, so a holdout clause can never
reach hypothesis formation.

NEVER CHANGES A WINNER (invariant). A clause records the WRONG successor the
rejected candidate produced on a witnessed (s, a, t). Pruning replays the NEW
candidate on that same (s, a, t) and skips it IFF it emits that same wrong grid.
A candidate that would gate clean cannot reproduce a wrong prediction, so it is
never pruned — mirrors the galois pruner's "never changes a winner" discipline.

ENV-GATED, DEFAULT ON (``ZTARE_SPEC_NOGOOD``, set "0" to disable). Inert when off: no
clause is written, no candidate is consulted, behaviour is byte-identical.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from ztare.common.conflict_ledger import ConflictClause

_NOGOODS = "spec_visible_nogoods.jsonl"


def enabled() -> bool:
    return os.environ.get("ZTARE_SPEC_NOGOOD", "1") != "0"


def _grid_to_lists(g) -> list:
    return [list(row) for row in g]


def behavior_signature(rules: "list[dict]") -> str:
    """Spec-behavior key: the frozen candidate rule-list (the rules ARE the
    deterministic behavior under lowering), hashed. NOT a card sha."""
    from ztare.worldmodel.spec_abduction import _freeze_deep

    payload = json.dumps(_freeze_deep(list(rules)), sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def assert_visible(clause: ConflictClause) -> ConflictClause:
    """Firewall guard: refuse any clause not tagged visible. Raises so a holdout
    clause can never silently reach hypothesis formation."""
    ev = (clause.provenance or {}).get("evidence") if isinstance(clause.provenance, dict) else None
    if ev != "visible":
        raise ValueError(
            f"spec_nogood firewall: proposer may only consult evidence=='visible' "
            f"clauses; got evidence={ev!r} for signature {clause.signature[:12]}"
        )
    return clause


class SpecNogoodLedger:
    """ConflictLedger over visible-replay nogoods, backed by a workspace jsonl
    (mirrors RefutedExperimentsLedger). The proposer is BOTH writer (on a visible
    rejection) and reader (at candidate enumeration). Latest row per signature
    wins."""

    def __init__(self, project: "Path | str"):
        self.path = Path(project) / "workspace" / _NOGOODS

    # ---- FEED --------------------------------------------------------------
    def record_visible(self, rules: "list[dict]", tr, predicted_next) -> ConflictClause:
        """Persist a visible-provenance nogood: the candidate's behavior signature
        + the witnessed (t, step-start grid) and the WRONG successor the candidate
        produced. `predicted_next` is the candidate's own (falsified) prediction
        on `tr`; `tr.s_next` is the truth it failed to match.

        ACTION NORMALIZATION (F4 fix, 2026-07-09): the frag is always lowered
        under action key "0" (the per-action option builder calls
        frag(s, 0, t) regardless of the real transition action). Storing
        tr.a here caused reproduces() to replay frag(s, real_a, t), which
        has no rules for real_a → identity → never matches recorded wrong
        output → the nogood prune was inert for all non-zero actions. Both
        sides are now normalized to action 0: the clause contract is
        action-normalized, not real-action-indexed."""
        sig = behavior_signature(rules)
        first = _first_mismatch(predicted_next, tr.s_next)
        clause = ConflictClause(
            signature=sig,
            receipts_refs=(f"{_NOGOODS}#{sig[:16]}",),
            witness_summary=(
                f"visible replay mismatch t={tr.t} a=0 (action-normalized) "
                f"cell(row={first[0]},col={first[1]}) predicted {first[2]} actual {first[3]}"
                if first else f"visible replay mismatch t={tr.t} a=0 (action-normalized)"
            ),
            provenance={
                "source": "spec_abduction_proposer",
                "evidence": "visible",
                "t": int(tr.t),
                "a": 0,   # action-normalized: frag contract is always action 0
                "s": _grid_to_lists(tr.s),
                "predicted_next": _grid_to_lists(predicted_next),
            },
            defeasible=True,
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a") as f:
            f.write(json.dumps({
                "signature": sig,
                "witness_summary": clause.witness_summary,
                "provenance": clause.provenance,
            }) + "\n")
        return clause

    # ---- CONSULT -----------------------------------------------------------
    def _clauses_by_sig(self) -> "dict[str, ConflictClause]":
        out: dict[str, ConflictClause] = {}
        if not self.path.exists():
            return out
        for line in self.path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:  # noqa: BLE001 - a malformed line is not a nogood
                continue
            sig = str(row.get("signature") or "")
            if not sig:
                continue
            out[sig] = ConflictClause(  # append order -> latest wins
                signature=sig,
                witness_summary=str(row.get("witness_summary") or ""),
                provenance=row.get("provenance") or {},
                defeasible=True,
            )
        return out

    def visible_clauses(self) -> "dict[str, ConflictClause]":
        """FIREWALL: only evidence=='visible' clauses are ever returned to the
        proposer. Any holdout clause is filtered out here AND would raise in
        `reproduces` via assert_visible."""
        return {sig: c for sig, c in self._clauses_by_sig().items()
                if isinstance(c.provenance, dict) and c.provenance.get("evidence") == "visible"}

    def learn(self, conflict_receipt: Any) -> ConflictClause:
        row = dict(conflict_receipt or {})
        return ConflictClause(
            signature=str(row.get("signature") or ""),
            witness_summary=str(row.get("witness_summary") or ""),
            provenance=row.get("provenance") or {},
            defeasible=True,
        )

    def blocks(self, candidate_signature: str) -> "ConflictClause | None":
        return self.visible_clauses().get(str(candidate_signature))

    def revive(self, evidence_card: Any) -> Any:
        return evidence_card

    def open_clauses(self) -> "list[ConflictClause]":
        return list(self.visible_clauses().values())


def reproduces(clause: ConflictClause, frag) -> bool:
    """PROVABLE prune check (invariant #2): replay the candidate's lowered `frag`
    on the clause's witnessed (s, a, t) and return True IFF it emits the recorded
    WRONG successor. A candidate that would gate clean cannot reproduce a wrong
    grid, so it is never pruned. Refuses a non-visible clause (firewall)."""
    assert_visible(clause)
    prov = clause.provenance
    s = prov.get("s")
    wrong = prov.get("predicted_next")
    if s is None or wrong is None:
        return False
    from ztare.worldmodel.grid_dsl import grid_from_lists

    try:
        out = frag(grid_from_lists(s), int(prov["a"]), int(prov["t"]))
    except Exception:  # noqa: BLE001 - a candidate that crashes here did not reproduce
        return False
    if out is None:
        return False
    return _grid_to_lists(out) == [list(r) for r in wrong]


def _first_mismatch(pred, real):
    if pred is None:
        return None
    for y in range(len(real)):
        for x in range(len(real[0])):
            if y < len(pred) and x < len(pred[y]) and pred[y][x] != real[y][x]:
                return (y, x, pred[y][x], real[y][x])
    return None
