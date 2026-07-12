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

RECEIPT_SCHEMA = "ztare.width_allocation.v1"
_EFFORT_ORDER = ["low", "medium", "high"]

# Hard bounds
_MIN_SHARDS = 1
_MAX_SHARDS = 6


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


def _unexplained_holdout_bits(project_dir: Path) -> tuple[int, int | None]:
    """Return (unexplained_bits, holdout_total).

    Source priority:
      1. Latest champion from champion_materialization.jsonl, matched in
         candidate_memory.json (or .jsonl).
      2. Fallback: candidate_memory max holdout_depth record.

    holdout_total parsed from counterexample_trace.failed_gates
    ('holdout_rollout_exact: N').  If not found, treated as None (no
    quiescence suppression).
    """
    ws = project_dir / "workspace"

    # 1. Find champion sha
    champion_sha: str | None = None
    cm_rows = _read_jsonl(ws / "champion_materialization.jsonl")
    for row in reversed(cm_rows):
        sha = row.get("promoted_sha") or row.get("from_ref")
        if not sha:
            gs = row.get("gate_summary_after") or {}
            sha = gs.get("gated_sha256")
        if sha:
            champion_sha = sha
            break

    # 2. Load candidate records
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

    # 3. Match champion record
    champ_rec: dict | None = None
    if champion_sha and records:
        short = champion_sha[:8]
        for rec in records:
            rsha = rec.get("sha") or ""
            if rsha.startswith(short) or champion_sha.startswith(rsha[:8]):
                champ_rec = rec
                break
    # fallback: highest holdout_depth
    if champ_rec is None and records:
        champ_rec = max(records, key=lambda r: r.get("holdout_depth") or 0)

    if champ_rec is None:
        return 0, None

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


def _recent_elimination_rate(project_dir: Path, n_runs: int = 3) -> int:
    """Count eliminated_family + refuted_mechanism rows in last N run entries
    of workspace/residual_specialists.jsonl."""
    rows = _read_jsonl(project_dir / "workspace" / "residual_specialists.jsonl")
    if not rows:
        return 0
    recent = rows[-n_runs:]
    count = 0
    for row in recent:
        for disp in row.get("dispatches") or []:
            if disp.get("eliminated_family") or disp.get("refuted_mechanism"):
                count += 1
    return count


def _stagnation(project_dir: Path) -> int:
    """Consecutive prior runs with no promotion in champion_materialization.jsonl."""
    rows = _read_jsonl(project_dir / "workspace" / "champion_materialization.jsonl")
    stag = 0
    for row in reversed(rows):
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
    unexplained, holdout_total = _unexplained_holdout_bits(project_dir)
    elimination_rate = _recent_elimination_rate(project_dir)
    stag = _stagnation(project_dir)

    signals = {
        "unexplained_holdout_bits": unexplained,
        "holdout_total": holdout_total,
        "recent_elimination_rate": elimination_rate,
        "stagnation": stag,
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
    receipt_path = ws / "width_allocations.jsonl"
    with receipt_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(receipt) + "\n")

    return result
