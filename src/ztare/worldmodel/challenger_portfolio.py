"""Challenger portfolio: nondominated candidates vs champion in product order.

Maintains workspace/challenger_portfolio.jsonl — a NONDOMINATED set of
candidates drawn from batch-gate results in residual_specialists.jsonl PLUS
the version_space ledger.  A candidate is nondominated when the champion does
NOT strictly dominate it in the product order on
  (visible_fraction, holdout_depth).

Strictly dominated = champion is strictly better in BOTH dimensions
  (champion_vfrac > cand_vfrac AND champion_holdout > cand_holdout).
Equal in both, or incomparable (better on one, worse on the other),
or better on one and equal on the other — all are nondominated.

SOLE-PRIVILEGE RULE: portfolio members NEVER promote.  The portfolio's only
authority is to nominate distinguishing play targets (propose_distinguishing_targets).
There is no `promote()` method here by design.

API
───
  refresh(project_dir)                — rebuild portfolio jsonl from receipts
  propose_distinguishing_targets(project_dir)
    → appends executor-schema rows to version_space_disagreements.jsonl,
      returning the count of rows appended

Files read:
  workspace/residual_specialists.jsonl   — gate_results per lane
  workspace/version_space.jsonl          — admitted survivors (fingerprint+holdout via champion)
  workspace/champion_materialization.jsonl — to get champion holdout_depth
  workspace/version_space_disagreements.jsonl — for existing targets (dedup)

Files written:
  workspace/challenger_portfolio.jsonl   — nondominated set (rebuilt on refresh)
  workspace/version_space_disagreements.jsonl — new targets appended

Schema: ztare.challenger_portfolio.v1
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

_PORTFOLIO_SCHEMA = "ztare.challenger_portfolio.v1"
_PORTFOLIO_FILE = "challenger_portfolio.jsonl"
_DISAGREEMENTS_FILE = "version_space_disagreements.jsonl"

# ponytail: import at module level so tests can patch via this module's namespace
try:
    from ztare.worldmodel.evidence_consolidation import resolve_episode_paths
except ImportError:  # noqa: BLE001 — not available in all test environments
    def resolve_episode_paths(project_dir):  # type: ignore[misc]
        return {"visible": None, "holdout": None}


# ── champion metrics ───────────────────────────────────────────────────────────

def _champion_metrics(project_dir: Path) -> dict:
    """Return {visible_exact, visible_total, holdout_depth, holdout_total} for the champion.

    Prefers the last promoted entry in champion_materialization.jsonl.
    Falls back to the version_space ledger entry for test_model.py.
    Returns zeros on failure (safe: nothing enters portfolio if champion unknown).
    """
    ws = project_dir / "workspace"

    # Try champion_materialization for holdout info
    holdout_depth: int = 0
    holdout_total: int = 1
    cm = ws / "champion_materialization.jsonl"
    if cm.exists():
        for line in reversed(cm.read_text(encoding="utf-8", errors="ignore").splitlines()):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            if row.get("result") != "promoted":
                continue
            dr = row.get("dominance_receipt") or {}
            rank = dr.get("rank_after") or []
            # rank_after is [visible_exact, 0, holdout_depth] per materialization receipts
            if len(rank) >= 3:
                holdout_depth = int(rank[2])
            # holdout_total from gate_summary_after.score if available
            gs = row.get("gate_summary_after") or {}
            score = gs.get("score")
            if score is not None and score > 0 and holdout_depth > 0:
                holdout_total = max(1, round(holdout_depth / score))
            break

    # Visible metrics from version_space (test_model.py is typically duplicate there)
    visible_exact: int = 0
    visible_total: int = 1
    vs = ws / "version_space.jsonl"
    if vs.exists():
        for line in vs.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            if "test_model.py" in (row.get("candidate_ref") or ""):
                ve = row.get("visible_exact", 0)
                vt = row.get("visible_total", 1)
                if ve > visible_exact:
                    visible_exact = ve
                    visible_total = vt

    return {
        "visible_exact": visible_exact,
        "visible_total": visible_total,
        "holdout_depth": holdout_depth,
        "holdout_total": holdout_total,
    }


# ── dominance check ────────────────────────────────────────────────────────────

def _strictly_dominated(
    cand: dict,
    champ_vfrac: float,
    champ_holdout: int,
) -> bool:
    """True iff champion strictly dominates candidate in (vfrac, holdout) product order."""
    ve = cand.get("visible_exact", 0)
    vt = cand.get("visible_total") or 1
    hd = cand.get("holdout_depth", 0)
    cand_vfrac = ve / vt if vt else 0.0
    # Strictly dominated: champion strictly better in BOTH dimensions
    return champ_vfrac > cand_vfrac and champ_holdout > hd


# ── source collection ──────────────────────────────────────────────────────────

def _candidates_from_specialists(project_dir: Path) -> list[dict]:
    """Extract visible-perfect gate results from residual_specialists.jsonl."""
    rs = project_dir / "workspace" / "residual_specialists.jsonl"
    if not rs.exists():
        return []
    candidates: list[dict] = []
    for line in rs.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        gr = row.get("gate_results") or {}
        for lane, data in gr.items():
            if not isinstance(data, dict):
                continue
            if data.get("wrong_rows") != []:
                continue  # only visible-perfect
            ref = data.get("candidate")
            if not ref:
                continue
            candidates.append({
                "candidate_ref": str(ref),
                "visible_exact": data.get("visible_exact", 0),
                "visible_total": data.get("visible_total", 1),
                "holdout_depth": data.get("holdout_depth", 0),
                "holdout_total": data.get("holdout_total", 1),
                "source": f"residual_specialists/{lane}",
            })
    return candidates


def _candidates_from_version_space(project_dir: Path) -> list[dict]:
    """Return admitted VS survivors with their ledger visible metrics.

    Note: VS ledger does NOT store holdout_depth; we set holdout_depth=0 so
    these candidates only enter the portfolio if the champion's holdout is also 0
    (i.e. unreachable).  The residual_specialists source is the primary holdout source.
    """
    vs = project_dir / "workspace" / "version_space.jsonl"
    if not vs.exists():
        return []
    by_ref: dict[str, dict] = {}
    for line in vs.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if row.get("schema") != "ztare.version_space.v1":
            continue
        ref = row.get("candidate_ref")
        if ref:
            by_ref[ref] = row
    seen_fps: set[str] = set()
    result: list[dict] = []
    for rec in by_ref.values():
        if rec.get("status") != "admitted":
            continue
        fp = rec.get("fingerprint")
        if fp and fp in seen_fps:
            continue
        seen_fps.add(fp)
        result.append({
            "candidate_ref": str(rec["candidate_ref"]),
            "visible_exact": rec.get("visible_exact", 0),
            "visible_total": rec.get("visible_total", 1),
            "holdout_depth": 0,   # not stored in VS ledger
            "holdout_total": 1,
            "fingerprint": fp,
            "source": "version_space",
        })
    return result


# ── dedup by ref ──────────────────────────────────────────────────────────────

def _dedup_by_ref(candidates: list[dict]) -> list[dict]:
    """Keep highest holdout_depth entry per candidate_ref."""
    by_ref: dict[str, dict] = {}
    for c in candidates:
        ref = c["candidate_ref"]
        if ref not in by_ref or c.get("holdout_depth", 0) > by_ref[ref].get("holdout_depth", 0):
            by_ref[ref] = c
    return list(by_ref.values())


# ── public API ─────────────────────────────────────────────────────────────────

def refresh(project_dir: "str | Path") -> list[dict]:
    """Rebuild workspace/challenger_portfolio.jsonl from receipts.

    Returns the list of nondominated portfolio members written.
    """
    project_dir = Path(project_dir).resolve()
    ws = project_dir / "workspace"
    ws.mkdir(parents=True, exist_ok=True)

    champ = _champion_metrics(project_dir)
    champ_vfrac = (
        champ["visible_exact"] / champ["visible_total"]
        if champ["visible_total"] else 0.0
    )
    champ_holdout = champ["holdout_depth"]

    # Collect all candidates from both sources
    all_cands = _dedup_by_ref(
        _candidates_from_specialists(project_dir)
        + _candidates_from_version_space(project_dir)
    )

    # Filter: not strictly dominated by champion
    portfolio = [
        c for c in all_cands
        if not _strictly_dominated(c, champ_vfrac, champ_holdout)
    ]

    # Write (overwrite) portfolio file
    portfolio_path = ws / _PORTFOLIO_FILE
    with portfolio_path.open("w", encoding="utf-8") as fh:
        for member in portfolio:
            row = {
                "schema": _PORTFOLIO_SCHEMA,
                "ts": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
                "candidate_ref": member["candidate_ref"],
                "visible_exact": member.get("visible_exact"),
                "visible_total": member.get("visible_total"),
                "holdout_depth": member.get("holdout_depth"),
                "holdout_total": member.get("holdout_total"),
                "source": member.get("source"),
                "fingerprint": member.get("fingerprint"),
                "champion_metrics": champ,
            }
            fh.write(json.dumps(row, sort_keys=True) + "\n")

    return portfolio


def _load_portfolio(project_dir: Path) -> list[dict]:
    """Read the current portfolio from disk."""
    p = project_dir / "workspace" / _PORTFOLIO_FILE
    if not p.exists():
        return []
    result = []
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            result.append(json.loads(line))
        except Exception:  # noqa: BLE001
            pass
    return result


def _champion_predictor(project_dir: Path):
    """Return (predict_fn, None) for the champion, or (None, None) on failure."""
    try:
        from ztare.worldmodel.evidence_consolidation import _load_carrier_from_source
        from ztare.worldmodel.gates import as_predictor
        champ = project_dir / "test_model.py"
        if not champ.exists():
            return None, None
        prog = _load_carrier_from_source(champ.read_text(), str(champ), project_dir)
        return as_predictor(prog), None
    except Exception:  # noqa: BLE001
        return None, None


def _member_predictor(member: dict, project_dir: Path):
    """Return (predict_fn, None) for a portfolio member."""
    try:
        from ztare.worldmodel.evidence_consolidation import _load_carrier_from_source
        from ztare.worldmodel.gates import as_predictor
        ref = Path(member["candidate_ref"])
        if not ref.is_absolute():
            ref = project_dir / ref
        if not ref.exists():
            return None, None
        prog = _load_carrier_from_source(ref.read_text(), str(ref), project_dir)
        return as_predictor(prog), None
    except Exception:  # noqa: BLE001
        return None, None


def _existing_target_keys(project_dir: Path) -> set[str]:
    """Keys already present in version_space_disagreements.jsonl (avoid dup appends)."""
    p = project_dir / "workspace" / _DISAGREEMENTS_FILE
    if not p.exists():
        return set()
    keys: set[str] = set()
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        for ds in row.get("disagreement_states") or []:
            key = json.dumps(
                {"t": ds.get("t"), "action": ds.get("action"), "row_index": ds.get("row_index")},
                sort_keys=True, separators=(",", ":"),
            )
            keys.add(key)
    return keys


def propose_distinguishing_targets(project_dir: "str | Path") -> int:
    """For each portfolio member vs champion: compute prediction-divergence targets
    on the holdout-prefix propagated rollout and append executor-schema rows to
    version_space_disagreements.jsonl.

    Uses the same loader/predictor pattern as version_space/evidence_consolidation
    (build_row_bitmap → as_predictor) and writes survivor_split groups with full
    prediction grids matching the distinguishing_play.load_targets schema.

    SOLE PRIVILEGE: only proposes targets; never promotes.
    Returns count of new rows appended to version_space_disagreements.jsonl.
    """
    project_dir = Path(project_dir).resolve()
    portfolio = _load_portfolio(project_dir)
    if not portfolio:
        return 0

    # Load holdout episode
    try:
        from ztare.worldmodel.episode_log import EpisodeLog
        ep = resolve_episode_paths(project_dir)
        holdout_path = ep.get("holdout")
        if holdout_path is None or not holdout_path.exists():
            return 0
        rows = list(EpisodeLog.read_jsonl(holdout_path))
    except Exception:  # noqa: BLE001
        return 0

    if not rows:
        return 0

    # Champion predictor
    champ_predict, _ = _champion_predictor(project_dir)
    if champ_predict is None:
        return 0

    existing_keys = _existing_target_keys(project_dir)
    appended = 0

    for member in portfolio:
        member_predict, _ = _member_predictor(member, project_dir)
        if member_predict is None:
            continue

        # Propagated rollout: find first disagreement between champion and member
        state = rows[0].s
        for i, tr in enumerate(rows):
            try:
                champ_pred = champ_predict(state, tr.a, tr.t)
                member_pred = member_predict(state, tr.a, tr.t)
            except Exception:  # noqa: BLE001
                break

            if champ_pred is None and member_pred is None:
                break

            # Disagreement: predictions differ
            champ_grid = [list(r) for r in champ_pred] if champ_pred is not None else None
            member_grid = [list(r) for r in member_pred] if member_pred is not None else None

            if champ_grid != member_grid:
                key = json.dumps(
                    {"t": getattr(tr, "t", None), "action": int(tr.a), "row_index": i},
                    sort_keys=True, separators=(",", ":"),
                )
                if key in existing_keys:
                    # Advance propagated state using champion
                    if champ_pred is not None:
                        state = champ_pred
                    continue

                # Build survivor_split in distinguishing_play schema
                survivor_split = [
                    {
                        "n_survivors": 1,
                        "survivors": [str(project_dir / "test_model.py")],
                        "prediction": champ_grid,
                    },
                    {
                        "n_survivors": 1,
                        "survivors": [member["candidate_ref"]],
                        "prediction": member_grid,
                    },
                ]

                ds = {
                    "t": getattr(tr, "t", None),
                    "action": int(tr.a),
                    "row_index": i,
                    "n_unique_predictions": 2,
                    "survivor_split": survivor_split,
                    "pricing_hook": "residual_information_yield",
                    "source": "challenger_portfolio",
                    "challenger_ref": member["candidate_ref"],
                }

                report = {
                    "schema": "ztare.vs_disagreements.v1",
                    "ts": time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()),
                    "n_survivors": 2,
                    "n_distinct_fingerprints": 2,
                    "disagreement_states": [ds],
                    "scripted_probe_targets": [],
                    "note": (
                        f"challenger_portfolio: member={Path(member['candidate_ref']).name} "
                        f"vs champion diverges at holdout row {i} (t={getattr(tr, 't', None)}, a={int(tr.a)})"
                    ),
                }

                dis_path = project_dir / "workspace" / _DISAGREEMENTS_FILE
                dis_path.parent.mkdir(parents=True, exist_ok=True)
                with dis_path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps(report, sort_keys=True) + "\n")

                existing_keys.add(key)
                appended += 1
                break  # one target per member is enough

            # Advance propagated state using champion prediction
            if champ_pred is not None:
                state = champ_pred
            elif tr.s_next is not None:
                state = tr.s_next
            else:
                break

    return appended
