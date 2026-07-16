"""Width allocator — compute parallel shards and effort from receipt signals.

Policy v1 (Sol conjecture 3, anti-hand-constant law):
  parallel width and effort are COMPUTED from receipts, not hand-set.

Pure function of receipt files; no Date.now-style nondeterminism.

Environment overrides (operator-grade):
  ZTARE_SPECIALIST_MAX_SHARDS   — hard cap on shards (int)
  ZTARE_ALLOCATOR_EFFORT_CEILING — caps effort level (default "medium")

Receipt written to workspace/width_allocations.jsonl
  schema: ztare.width_allocation.v1

Substrate seam (named to prevent silent ossification): _compute_shards /
_cap_effort are the PURE POLICY (substrate-neutral — width follows
unexplained residual, stagnation, elimination rate). The signal extractors
above them are the WORLDMODEL ADAPTER (episodes, rollout depth). A second
substrate (prose/leanmill: unexplained = open obligations) gets its own
adapter feeding the same policy — split into modules when that consumer
exists, not before.
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

from ztare.worldmodel.carrier_loader import (
    CarrierEvidenceIdentityError,
    CurrentCarrierEvidenceIdentity,
    require_current_carrier_evidence_binding,
    resolve_current_carrier_evidence_identity,
)

RECEIPT_SCHEMA = "ztare.width_allocation.v1"
_EFFORT_ORDER = ["low", "medium", "high"]

# Hard bounds
_MIN_SHARDS = 1
_MAX_SHARDS = 6
_IDENTITY_UNSET = object()


# ── Signal extractors ──────────────────────────────────────────────────────────


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:  # noqa: BLE001
            pass
    return rows


def _holdout_total_from_failed_gates(failed_gates: list) -> int | None:
    """Parse 'holdout_rollout_exact: N' to extract N as holdout_total."""
    for fg in failed_gates or []:
        m = re.search(r"holdout_rollout_exact:\s*(\d+)", str(fg))
        if m:
            return int(m.group(1))
    return None


def _current_identity(project_dir: Path) -> CurrentCarrierEvidenceIdentity | None:
    try:
        return resolve_current_carrier_evidence_identity(project_dir)
    except (OSError, TypeError, ValueError):
        return None


def _is_current_receipt(
    row: dict,
    current: CurrentCarrierEvidenceIdentity,
) -> bool:
    try:
        require_current_carrier_evidence_binding(row, current)
    except CarrierEvidenceIdentityError:
        return False
    return True


def _unexplained_holdout_bits(
    project_dir: Path,
    current_identity: CurrentCarrierEvidenceIdentity | None | object = _IDENTITY_UNSET,
) -> tuple[int, int | None]:
    """Return (unexplained_bits, holdout_total).

    Only a candidate-memory observation bound to the current full carrier SHA
    and evidence epoch may steer width. Prefix matches, path-only records, and
    the former max-depth fallback remain historical telemetry.

    holdout_total parsed from counterexample_trace.failed_gates
    ('holdout_rollout_exact: N').  If not found, treated as None (no
    quiescence suppression).
    """
    ws = project_dir / "workspace"
    current = (
        _current_identity(project_dir)
        if current_identity is _IDENTITY_UNSET
        else current_identity
    )
    if not isinstance(current, CurrentCarrierEvidenceIdentity):
        return 1, None

    records: list[dict] = []
    cm_json = ws / "candidate_memory.json"
    if cm_json.exists():
        try:
            raw = json.loads(cm_json.read_text(encoding="utf-8"))
            records = raw.get("records") or [] if isinstance(raw, dict) else raw
        except Exception:  # noqa: BLE001
            pass
    if not records:
        records = _read_jsonl(ws / "candidate_memory.jsonl")

    champ_rec = next(
        (rec for rec in reversed(records) if _is_current_receipt(rec, current)),
        None,
    )

    if champ_rec is None:
        # Unknown population is not quiescence. The router treats one bit as
        # unresolved while the allocator stays at its narrow safe default.
        return 1, None

    depth: int = champ_rec.get("holdout_depth") or 0
    ct = champ_rec.get("counterexample_trace") or {}
    # PRIMARY total source: latest specialists gate_result rows carry an
    # authoritative holdout_total (the failed_gates string parse proved
    # unreliable — it yielded total=4 for a 16-step holdout and triggered
    # false quiescence, the worst allocator failure: starving the search
    # while 12 bits remained).
    holdout_total = None
    try:
        from ztare.worldmodel.evidence_consolidation import resolve_episode_paths
        hp = resolve_episode_paths(project_dir).get("holdout")
        if hp is not None and hp.exists():
            n = sum(1 for l in hp.read_text(encoding="utf-8", errors="ignore").splitlines() if l.strip())
            if n > 0:
                holdout_total = n
    except Exception:  # noqa: BLE001
        holdout_total = None
    if holdout_total is None:
        # last resort; note the failed_gates string carries the gate VALUE
        # (= depth), not the total — never trust it alone for quiescence
        holdout_total = ct.get("holdout_total")
    # unexplained = steps the champion has NOT yet explained
    if isinstance(holdout_total, int) and holdout_total > 0:
        unexplained = max(0, holdout_total - depth)
    else:
        # total unknown → never claim quiescence; assume moderate frontier
        unexplained = max(1, depth)
    return unexplained, holdout_total


def _recent_elimination_rate(
    project_dir: Path,
    n_runs: int = 3,
    current_identity: CurrentCarrierEvidenceIdentity | None | object = _IDENTITY_UNSET,
) -> int:
    """Count eliminated_family + refuted_mechanism rows in last N run entries
    of workspace/residual_specialists.jsonl."""
    rows = _read_jsonl(project_dir / "workspace" / "residual_specialists.jsonl")
    current = (
        _current_identity(project_dir)
        if current_identity is _IDENTITY_UNSET
        else current_identity
    )
    if not rows or not isinstance(current, CurrentCarrierEvidenceIdentity):
        return 0
    recent = [row for row in rows if _is_current_receipt(row, current)][-n_runs:]
    count = 0
    for row in recent:
        for disp in row.get("dispatches") or []:
            if disp.get("eliminated_family") or disp.get("refuted_mechanism"):
                count += 1
    return count


def _stagnation(
    project_dir: Path,
    current_identity: CurrentCarrierEvidenceIdentity | None | object = _IDENTITY_UNSET,
) -> int:
    """Current-population runs since a promotion of this carrier identity."""
    rows = _read_jsonl(project_dir / "workspace" / "champion_materialization.jsonl")
    current = (
        _current_identity(project_dir)
        if current_identity is _IDENTITY_UNSET
        else current_identity
    )
    if not isinstance(current, CurrentCarrierEvidenceIdentity):
        return 0
    stag = 0
    for row in reversed(rows):
        if not _is_current_receipt(row, current):
            continue
        if row.get("result") == "promoted":
            break
        stag += 1
    return stag


# ── Policy ────────────────────────────────────────────────────────────────────


def _cap_effort(effort: str, ceiling: str) -> str:
    ci = _EFFORT_ORDER.index(ceiling) if ceiling in _EFFORT_ORDER else 1
    ei = _EFFORT_ORDER.index(effort) if effort in _EFFORT_ORDER else 0
    return _EFFORT_ORDER[min(ei, ci)]


def _compute_shards(
    unexplained: int,
    holdout_total: int | None,
    elimination_rate: int,
    stagnation: int,
) -> int:
    """Policy v1: width grows with unexplained bits and stagnation;
    shrinks toward 1 when depth approaches holdout_total (quiescence)."""

    # Quiescence: nothing unexplained remains (unexplained = total - depth)
    if holdout_total is not None and holdout_total > 0 and unexplained == 0:
        return 1

    # Base: 1 shard
    shards = 1

    # Unexplained bits drive width
    if unexplained >= 6:
        shards = 3
    elif unexplained >= 2:
        shards = 2

    # Stagnation adds one more
    if stagnation >= 2:
        shards += 1

    # Some recent eliminations signal convergence — don't over-expand
    if elimination_rate >= 3:
        shards = max(1, shards - 1)

    return max(_MIN_SHARDS, min(_MAX_SHARDS, shards))


def allocate_width(project_dir: str | Path) -> dict:
    """Compute parallel width and effort from receipts.

    Returns:
        {
          "shards": int,
          "samples_per_shard": int,
          "effort": str,
          "rationale": str,
          "signals": {...},
        }

    Side-effect: appends one row to workspace/width_allocations.jsonl.
    """
    project_dir = Path(project_dir)
    ws = project_dir / "workspace"

    # ── Gather signals ──
    current = _current_identity(project_dir)
    unexplained, holdout_total = _unexplained_holdout_bits(project_dir, current)
    elimination_rate = _recent_elimination_rate(
        project_dir, current_identity=current
    )
    stag = _stagnation(project_dir, current)

    signals = {
        "unexplained_holdout_bits": unexplained,
        "holdout_total": holdout_total,
        "recent_elimination_rate": elimination_rate,
        "stagnation": stag,
        "identity_status": "current" if current is not None else "unavailable",
    }

    # ── Operator overrides (env wins) ──
    env_max = os.environ.get("ZTARE_SPECIALIST_MAX_SHARDS")
    effort_ceiling = os.environ.get("ZTARE_ALLOCATOR_EFFORT_CEILING", "medium")

    # ── Policy ──
    shards = _compute_shards(unexplained, holdout_total, elimination_rate, stag)
    if env_max is not None:
        # ponytail: env override wins; still clamp to hard bounds
        shards = max(_MIN_SHARDS, min(_MAX_SHARDS, int(env_max)))

    samples_per_shard = 2 if stag >= 2 else 1

    effort_raw = "medium" if stag >= 3 else "low"
    effort = _cap_effort(effort_raw, effort_ceiling)

    # ── Rationale ──
    parts = [
        f"identity={'current' if current is not None else 'unavailable'}",
        f"unexplained_bits={unexplained}",
        f"stagnation={stag}",
        f"elimination_rate={elimination_rate}",
    ]
    if holdout_total is not None and unexplained >= holdout_total and holdout_total > 0:
        parts.append("quiescence→shards=1")
    if env_max is not None:
        parts.append(f"env_override=ZTARE_SPECIALIST_MAX_SHARDS:{env_max}")
    rationale = f"policy_v1 [{', '.join(parts)}] → shards={shards} samples={samples_per_shard} effort={effort}"

    result = {
        "shards": shards,
        "samples_per_shard": samples_per_shard,
        "effort": effort,
        "rationale": rationale,
        "signals": signals,
        "carrier_evidence_identity": current.to_dict() if current is not None else None,
    }

    # ── Emit receipt ──
    ws.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "signals": signals,
        "decision": {"shards": shards, "samples_per_shard": samples_per_shard, "effort": effort},
        "rationale": rationale,
        "ts": time.time(),
    }
    if current is not None:
        receipt["carrier_evidence_identity"] = current.to_dict()
    receipt_path = ws / "width_allocations.jsonl"
    with receipt_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(receipt) + "\n")

    return result
