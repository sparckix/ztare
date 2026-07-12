"""Worldmodel refutations as ConflictClauses — the CDCL contract for killed experiments.

A carrier_repair / evidence card the executor disposes ``killed`` is a CONFIRMED
refutation: the probe ran and produced a killing counterexample witness (a holdout
witness, a first-mismatch, or a matched kill condition). Those verdicts already
persist to ``strategy_experiment_executions.jsonl``; before this module they only
lived there as prose the office re-rendered, so the SAME killed failure_family could
be re-proposed with no machine block.

This is the REFUTATION DUAL for the worldmodel, keyed on ``failure_family_sha`` — the
same signature ``write_proposal_cards`` dedups cards by. It does NOT add a third store:
the executions jsonl IS the backing log (the executor is the writer at the killed
disposition), and this reads it into ConflictClauses. Unifies onto the one
``conflict_ledger.ConflictLedger`` Protocol rather than standing up a parallel
refuted-pattern surface.

SOUNDNESS (CDCL: a learned clause is logically valid). Only ``disposition == "killed"``
becomes a clause — a rejected probe (``blocked`` / ``rejected_unlowerable``) proves
nothing and is never recorded; an ``observed`` evidence probe neither survives nor
kills. So a clause here always carries a real killing witness. Clauses are defeasible:
a revised carrier is a NEW family (new sha), so a genuine repair is never suppressed.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ztare.common.conflict_ledger import ConflictClause

_EXECUTIONS = "strategy_experiment_executions.jsonl"


def _witness_summary(row: dict[str, Any]) -> str:
    """The killing witness for a killed execution row: the counterexample trace's
    holdout witness / first mismatch when present, else the matched kill condition,
    else the outcome summary. Never game-specific hints — this is the row's own
    recorded evidence, verbatim and bounded."""
    for live in row.get("live_rows") or []:
        if not isinstance(live, dict):
            continue
        ce = live.get("counterexample_trace")
        if isinstance(ce, dict):
            hw = ce.get("holdout_witness") or ce.get("first_mismatch")
            if hw:
                return f"counterexample: {json.dumps(hw, sort_keys=True, default=str)[:400]}"
            sig = ce.get("first_mismatch_signature")
            if sig:
                return f"first_mismatch_signature: {str(sig)[:400]}"
    if row.get("kill_condition_matched") and row.get("kill_condition"):
        return f"kill condition met: {str(row.get('kill_condition'))[:400]}"
    return f"killed: {str(row.get('outcome_summary') or '')[:400]}"


def _row_to_clause(row: dict[str, Any]) -> ConflictClause | None:
    sig = str(row.get("failure_family_sha") or "")
    if not sig or str(row.get("disposition") or "") != "killed":
        return None
    return ConflictClause(
        signature=sig,
        receipts_refs=(f"{_EXECUTIONS}#{row.get('outcome_sha256', '')}",),
        witness_summary=_witness_summary(row),
        provenance={
            "source": "worldmodel_experiment_executor",
            "kind": row.get("kind"),
            "executed_utc": row.get("executed_utc"),
        },
        defeasible=True,  # a revised carrier is a new family (new sha)
    )


class RefutedExperimentsLedger:
    """ConflictLedger over the killed rows of ``strategy_experiment_executions.jsonl``.

    Read-only view: the executor is the WRITER (it appends the killed row at the
    killed disposition). One clause per killed failure_family_sha; the latest row
    wins so a re-run's fresher witness supersedes a stale one.
    """

    def __init__(self, project: "Path | str"):
        self.path = Path(project) / "workspace" / _EXECUTIONS

    def _killed_rows(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:  # noqa: BLE001 - a malformed line is not a refutation
                continue
            if isinstance(row, dict) and str(row.get("disposition") or "") == "killed":
                rows.append(row)
        return rows

    def _clauses_by_sig(self) -> dict[str, ConflictClause]:
        out: dict[str, ConflictClause] = {}
        for row in self._killed_rows():  # append order → latest row wins
            clause = _row_to_clause(row)
            if clause:
                out[clause.signature] = clause
        return out

    def learn(self, conflict_receipt: Any) -> ConflictClause:
        """Adapt a killed execution row (or {signature,...} dict) into a clause.
        The executor persists the row; this just surfaces it — no separate write."""
        row = dict(conflict_receipt or {})
        clause = _row_to_clause(row)
        if clause:
            return clause
        return ConflictClause(
            signature=str(row.get("failure_family_sha") or row.get("signature") or ""),
            witness_summary=str(row.get("witness_summary") or ""),
            provenance=row.get("provenance") or {"source": "worldmodel_experiment_executor"},
            defeasible=True,
        )

    def blocks(self, candidate_signature: str) -> "ConflictClause | None":
        return self._clauses_by_sig().get(str(candidate_signature))

    def revive(self, evidence_card: Any) -> Any:
        return evidence_card

    def open_clauses(self) -> list[ConflictClause]:
        return list(self._clauses_by_sig().values())

    def blocked_signatures(self) -> set[str]:
        return set(self._clauses_by_sig())


def render_refuted_block(project: "Path | str", *, limit: int = 8) -> str:
    """Render open refutation clauses as a REFUTED (machine-blocked) prompt section.
    Empty string when nothing is refuted, so a caller can append unconditionally."""
    clauses = RefutedExperimentsLedger(project).open_clauses()
    if not clauses:
        return ""
    lines = [
        "=== REFUTED (machine-blocked): these failure families were KILLED by a "
        "counterexample and are pruned from re-proposal — commission a DIFFERENT "
        "family (a revised carrier is a new family) ==="
    ]
    for clause in clauses[:limit]:
        kind = (clause.provenance or {}).get("kind") if isinstance(clause.provenance, dict) else None
        lines.append(f"- family {clause.signature[:12]} kind={kind} — witness {clause.witness_summary}")
    if len(clauses) > limit:
        lines.append(f"  … and {len(clauses) - limit} more refuted families.")
    return "\n".join(lines)


def _selftest() -> int:
    import tempfile

    fails: list[str] = []

    def ok(name: str, cond: bool) -> None:
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            fails.append(name)

    d = Path(tempfile.mkdtemp())
    (d / "workspace").mkdir()
    execs = d / "workspace" / _EXECUTIONS
    killed = {
        "schema": "ztare-strategy-experiment-execution-v1",
        "failure_family_sha": "deadbeef" * 8,
        "kind": "compressed_counterexample_repair",
        "disposition": "killed",
        "kill_condition": "repair fails at first post-boundary step",
        "kill_condition_matched": True,
        "outcome_summary": "candidate mismatched holdout",
        "outcome_sha256": "abc123",
        "executed_utc": "2026-07-09T00:00:00+00:00",
        "live_rows": [{
            "kind": "carrier_repair_probe",
            "counterexample_trace": {"holdout_witness": {"t": 19, "step_index": 0}},
        }],
    }
    survived = {**killed, "failure_family_sha": "feed" * 16, "disposition": "survived"}
    blocked = {**killed, "failure_family_sha": "0bad" * 16, "disposition": "blocked"}
    with execs.open("w") as f:
        for r in (killed, survived, blocked):
            f.write(json.dumps(r) + "\n")

    led = RefutedExperimentsLedger(d)

    # blocks() returns the clause WITH the witness for a killed family
    clause = led.blocks("deadbeef" * 8)
    ok("blocks() returns clause for killed family", clause is not None)
    ok("clause carries the counterexample witness", clause is not None and "t" in clause.witness_summary and "19" in clause.witness_summary)
    ok("clause provenance names the executor", isinstance(clause.provenance, dict) and clause.provenance.get("source") == "worldmodel_experiment_executor")

    # SOUNDNESS: survived/blocked are NOT refutations → no clause, never blocked
    ok("survived family is not blocked", led.blocks("feed" * 16) is None)
    ok("blocked (never-ran) family is not blocked", led.blocks("0bad" * 16) is None)
    ok("only the killed sig is open", led.blocked_signatures() == {"deadbeef" * 8})

    # render surfaces the machine-blocked section with the witness
    block = render_refuted_block(d)
    ok("render shows REFUTED (machine-blocked)", "REFUTED (machine-blocked)" in block)
    ok("render names the witness", "19" in block)
    ok("render empty when nothing refuted", render_refuted_block(Path(tempfile.mkdtemp())) == "")

    print("SELFTEST", "PASSED" if not fails else f"FAILED {fails}")
    return 1 if fails else 0


if __name__ == "__main__":
    import sys

    sys.exit(_selftest())
