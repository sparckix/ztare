"""Pre-registered evaluation protocol — anti-adaptive-testing hardening.

Cold-review findings 2/3/5:
  2. Pre-registered evaluation against adaptive testing: register_evaluation,
     record_attempt, reserve_audit_slice.
  3. Policy-vs-law validation: eval_plan + validate_slice enforce that the
     evaluation slice MUST contain all precommitted distinguishing interventions.
  5. Taint lineage: mark_taint / is_tainted / assert_untainted_chooser.

All state is append-only JSONL under workspace/ of the given project_dir.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_EVAL_LEDGER = "eval_protocol.jsonl"
_TAINT_LEDGER = "taint_lineage.jsonl"
_AUDIT_SLICES = "audit_slices.jsonl"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _workspace(project_dir: str | Path) -> Path:
    p = Path(project_dir) / "workspace"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _append(ledger: Path, row: dict) -> None:
    with ledger.open("a") as f:
        f.write(json.dumps(row) + "\n")


def _read_all(ledger: Path) -> list[dict]:
    if not ledger.exists():
        return []
    rows = []
    for line in ledger.read_text().splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


# ---------------------------------------------------------------------------
# Finding 2: pre-registered evaluation (budget-gated, attempt-recorded)
# ---------------------------------------------------------------------------

def _lineage_attempts(ledger: Path, lineage_id: str) -> int:
    """Count all attempt records for a lineage (across all candidates)."""
    return sum(
        1 for r in _read_all(ledger)
        if r.get("record_type") == "attempt" and r.get("lineage_id") == lineage_id
    )


def register_evaluation(
    project_dir: str | Path,
    candidate_sha: str,
    *,
    lineage_id: str,
    budget: int = 3,
    acceptance_rule: str = "fresh_slice_holdout_depth==total",
) -> dict:
    """Register a new evaluation for candidate_sha under lineage_id.

    Returns the ledger row written. If the lineage has exhausted its budget
    the row has status='refused_budget_exhausted' and nothing is registered
    as an active evaluation.
    """
    ws = _workspace(project_dir)
    ledger = ws / _EVAL_LEDGER

    used = _lineage_attempts(ledger, lineage_id)
    if used >= budget:
        row: dict[str, Any] = {
            "schema": "ztare.eval_protocol.v1",
            "record_type": "registration",
            "lineage_id": lineage_id,
            "candidate_sha": candidate_sha,
            "budget": budget,
            "attempts_used": used,
            "acceptance_rule": acceptance_rule,
            "status": "refused_budget_exhausted",
        }
        _append(ledger, row)
        return row

    row = {
        "schema": "ztare.eval_protocol.v1",
        "record_type": "registration",
        "lineage_id": lineage_id,
        "candidate_sha": candidate_sha,
        "budget": budget,
        "attempts_used": 0,
        "acceptance_rule": acceptance_rule,
        "status": "registered",
    }
    _append(ledger, row)
    return row


def record_attempt(
    project_dir: str | Path,
    candidate_sha: str,
    *,
    lineage_id: str,
    slice_ref: str,
    outcome: str,
    stopping_rule: str,
) -> dict:
    """Record one evaluation attempt (pass or fail). Always appended.

    Refuses if slice_ref is reserved (returns status='refused_reserved_slice').
    """
    ws = _workspace(project_dir)
    ledger = ws / _EVAL_LEDGER

    if _slice_is_reserved(project_dir, slice_ref):
        row: dict[str, Any] = {
            "schema": "ztare.eval_protocol.v1",
            "record_type": "attempt",
            "lineage_id": lineage_id,
            "candidate_sha": candidate_sha,
            "slice_ref": slice_ref,
            "outcome": outcome,
            "stopping_rule": stopping_rule,
            "status": "refused_reserved_slice",
        }
        _append(ledger, row)
        return row

    row = {
        "schema": "ztare.eval_protocol.v1",
        "record_type": "attempt",
        "lineage_id": lineage_id,
        "candidate_sha": candidate_sha,
        "slice_ref": slice_ref,
        "outcome": outcome,
        "stopping_rule": stopping_rule,
        "status": "recorded",
    }
    _append(ledger, row)
    return row


# ---------------------------------------------------------------------------
# Audit-slice registry (never-reusable)
# ---------------------------------------------------------------------------

def _slice_is_reserved(project_dir: str | Path, slice_ref: str) -> bool:
    ws = _workspace(project_dir)
    ledger = ws / _AUDIT_SLICES
    return any(r.get("slice_ref") == slice_ref for r in _read_all(ledger))


def reserve_audit_slice(project_dir: str | Path, slice_ref: str) -> dict:
    """Mark slice_ref as reserved — all future attempts against it are refused."""
    ws = _workspace(project_dir)
    ledger = ws / _AUDIT_SLICES
    row: dict[str, Any] = {
        "schema": "ztare.eval_protocol.v1",
        "record_type": "audit_slice_reservation",
        "slice_ref": slice_ref,
    }
    _append(ledger, row)
    return row


# ---------------------------------------------------------------------------
# Finding 3: policy-vs-law validation (precommitted interventions)
# ---------------------------------------------------------------------------

def _unresolved_probe_targets(project_dir: str | Path) -> list[str]:
    """Return unresolved probe target ids from the LIVE disagreement schema.

    Primary source: distinguishing_play.load_targets (the executor's own
    reader — same ids, same resolution filtering; one schema, one reader).
    Fallback: the legacy `required_probe_targets` field for planted fixtures.
    """
    targets: list[str] = []
    try:
        from ztare.worldmodel.distinguishing_play import load_targets
        for t in load_targets(project_dir):
            tid = t.get("_target_id")
            if tid and tid not in targets:
                targets.append(tid)
    except Exception:  # noqa: BLE001
        pass
    ws = Path(project_dir) / "workspace"
    path = ws / "version_space_disagreements.jsonl"
    if path.exists():
        for row in _read_all(path):
            if row.get("resolved"):
                continue
            for t in row.get("required_probe_targets", []):
                if t not in targets:
                    targets.append(t)
    return targets


def eval_plan(project_dir: str | Path, lineage_id: str) -> dict:
    """Emit the evaluation plan for lineage_id.

    required_interventions are the unresolved probe target ids from
    version_space_disagreements.jsonl — a fresh slice that avoids these
    disputed contexts is INVALID for acceptance.
    """
    targets = _unresolved_probe_targets(project_dir)
    row: dict[str, Any] = {
        "schema": "ztare.eval_protocol.v1",
        "record_type": "eval_plan",
        "lineage_id": lineage_id,
        "required_interventions": targets,
        "policy_neutral_sample": len(targets),  # at minimum
    }
    return row


def validate_slice(slice_rows: list[dict], plan: dict) -> dict:
    """Check that slice_rows cover all required_interventions from plan.

    Each slice row may carry 'target_id' (real schema), 'probe_target_id', or
    'intervention_id' — all are accepted.  target_id is preferred (primary key
    in the real distinguishing_play / executor rows; the other two are legacy
    names from earlier specs).
    Returns {valid: bool, missing_interventions: list[str]}.
    """
    required = set(plan.get("required_interventions", []))
    covered: set[str] = set()
    for r in slice_rows:
        tid = r.get("target_id") or r.get("probe_target_id") or r.get("intervention_id")
        if tid:
            covered.add(tid)
    missing = sorted(required - covered)
    return {"valid": len(missing) == 0, "missing_interventions": missing}


# ---------------------------------------------------------------------------
# Finding 5: taint lineage
# ---------------------------------------------------------------------------

def mark_taint(
    project_dir: str | Path,
    candidate_sha: str,
    *,
    source: str,
    parents: list[str] | None = None,
) -> dict:
    """Append a taint record for candidate_sha."""
    ws = _workspace(project_dir)
    ledger = ws / _TAINT_LEDGER
    row: dict[str, Any] = {
        "schema": "ztare.eval_protocol.v1",
        "record_type": "taint",
        "candidate_sha": candidate_sha,
        "source": source,
        "parents": parents or [],
    }
    _append(ledger, row)
    return row


def is_tainted(project_dir: str | Path, candidate_sha: str) -> bool:
    """Walk taint lineage transitively. Returns True if candidate_sha or any
    ancestor is directly tainted."""
    ws = _workspace(project_dir)
    ledger = ws / _TAINT_LEDGER
    rows = _read_all(ledger)

    # Build adjacency: sha -> {parent shas}
    parents_of: dict[str, list[str]] = {}
    directly_tainted: set[str] = set()
    for r in rows:
        if r.get("record_type") != "taint":
            continue
        sha = r["candidate_sha"]
        directly_tainted.add(sha)
        parents_of[sha] = r.get("parents", [])

    # BFS from candidate_sha upward through parents
    visited: set[str] = set()
    frontier = [candidate_sha]
    while frontier:
        cur = frontier.pop()
        if cur in visited:
            continue
        visited.add(cur)
        if cur in directly_tainted:
            return True
        frontier.extend(parents_of.get(cur, []))
    return False


def assert_untainted_chooser(project_dir: str | Path, chooser_id: str) -> None:
    """Assert that chooser_id is not tainted.

    Tainted components must not choose evaluation contexts. Raises
    AssertionError if the chooser is tainted.
    """
    if is_tainted(project_dir, chooser_id):
        raise AssertionError(
            f"Tainted chooser '{chooser_id}' must not select evaluation contexts. "
            "Tainted components cannot choose evaluation contexts — assign an "
            "untainted selector."
        )
