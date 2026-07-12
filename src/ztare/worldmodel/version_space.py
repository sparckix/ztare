"""Version-space ledger: population of surviving world-model programs.

Identifies mechanisms by BEHAVIOR (fingerprint of prediction bitvector),
not by prose or path. Maintains all visible-perfect survivors as a population
and exposes the disagreement structure across that population to suggest
distinguishing experiments.

This is the EXTENSIONAL dual of the nogood/derived-constraints ledgers (they
describe the space by its boundaries; this enumerates its surviving members).
Distinguishing experiments require the extensional side — constraints cannot
disagree with each other, models can. `hypothesis_split_ratio` in p0_metrics is
the pre-existing metric hook: |survivors after| / |survivors before| per
observation.

Kernel-level naming (fractal-siblings convention — shared names, separate
evidence semantics):
  admit()                 → ADMIT cell in decision_support_primitives
  disagreement_report()   → AGENDA cell
  pruning (on new obs.)   → MAINTAIN cell

Substrate seam:
  Substrate-neutral core: ledger operations (admit/dedupe/disagreement).
  Worldmodel adapter: battery construction (probe_battery) + carrier loading
    (_load_carrier_from_source). A numeric-substrate adapter would fingerprint
    I_model on a feature battery; split into separate modules only when a
    second consumer exists.

Files written:
  workspace/version_space.jsonl          — append-only ledger
  workspace/version_space_disagreements.jsonl — one row per report call

CLI:
  python -m ztare.worldmodel.version_space --project P [--seed] [--report]
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.evidence_consolidation import (
    _load_carrier_from_source,
    build_row_bitmap,
    resolve_episode_paths,
)
from ztare.worldmodel.gates import as_predictor, env_frame_indices


# ── probe battery ─────────────────────────────────────────────────────────────

def probe_battery(project_dir: "str | Path") -> list[dict]:
    """Build the probe battery: union of three provenance sources.

    Returns list of dicts:
      {row_index: int, provenance: list[str], provenance_count: int}

    Sources (deduplicated by row_index, provenance accumulated):
      (a) rows where ANY existing bitmap disagrees (union of wrong_rows)
      (b) deterministic stride-sample of ~200 visible rows (seed=row_count)
      (c) last 50 visible rows (newest evidence)

    FROZEN per episode: the battery is persisted to
    workspace/version_space_battery.json keyed by the visible episode hash and
    reused on every subsequent call. Without this, seeding itself grows source
    (a) — each rejected candidate writes a bitmap whose wrong_rows expand the
    battery — and candidates fingerprinted at different times get hashed
    against different probe sets: same behavior, different sha. (Observed on
    arc3_ls20_gov: 3 'distinct' fingerprints among survivors that the live
    pairwise report proved behaviorally identical.) A new visible episode hash
    starts a new battery epoch; delete the snapshot file to re-epoch manually.
    """
    project_dir = Path(project_dir).resolve()
    ep = resolve_episode_paths(project_dir)
    visible_path = ep["visible"]
    if visible_path is None or not visible_path.exists():
        return []

    log = EpisodeLog.read_jsonl(visible_path)
    total = len(log)
    if total == 0:
        return []

    episode_hash = log.content_hash()[:16]
    snapshot_file = project_dir / "workspace" / "version_space_battery.json"
    if snapshot_file.exists():
        try:
            snap = json.loads(snapshot_file.read_text())
            if snap.get("episode_hash") == episode_hash:
                return snap["battery"]
        except Exception:  # noqa: BLE001
            pass  # corrupt snapshot → rebuild

    # env-frame indices — excluded from evaluation, skip them in probes
    env_idx = env_frame_indices(log)

    probes: dict[int, list[str]] = {}  # row_index -> [provenance strings]

    def _add(idx: int, source: str) -> None:
        if idx not in env_idx and 0 <= idx < total:
            probes.setdefault(idx, []).append(source)

    # (a) union of wrong_rows from existing bitmaps
    bitmap_dir = project_dir / "workspace" / "row_bitmaps"
    if bitmap_dir.is_dir():
        for bf in bitmap_dir.glob("*.json"):
            try:
                bm = json.loads(bf.read_text())
                for row in bm.get("wrong_rows", []):
                    _add(row, f"bitmap:{bf.stem[:12]}")
            except Exception:  # noqa: BLE001
                pass

    # (b) deterministic stride-sample ~200 rows
    n_sample = min(200, total)
    if n_sample > 0:
        # seed from total row count — deterministic
        step = max(1, total // n_sample)
        offset = (total * 7 + 3) % step  # deterministic offset from count
        for i in range(offset, total, step):
            _add(i, "stride_sample")

    # (c) last 50 rows
    for i in range(max(0, total - 50), total):
        _add(i, "last_50")

    # Build result, sorted by provenance_count desc then row_index
    result = [
        {"row_index": idx, "provenance": srcs, "provenance_count": len(srcs)}
        for idx, srcs in probes.items()
    ]
    result.sort(key=lambda x: (-x["provenance_count"], x["row_index"]))

    # Freeze: persist snapshot so all future fingerprints share one battery.
    try:
        snapshot_file.parent.mkdir(parents=True, exist_ok=True)
        snapshot_file.write_text(json.dumps(
            {"schema": "ztare.version_space_battery.v1",
             "episode_hash": episode_hash, "battery": result}))
    except Exception:  # noqa: BLE001
        pass  # best-effort persistence; in-memory battery is the truth

    return result


# ── fingerprint ───────────────────────────────────────────────────────────────

_FP_CACHE_SCHEMA = "ztare.version_space_fp_cache.v1"


def _fp_cache_path(project_dir: Path) -> Path:
    return project_dir / "workspace" / "version_space_fp_cache.jsonl"


def _battery_sha(battery: list[dict]) -> str:
    return hashlib.sha256(
        json.dumps(battery, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()[:32]


def _fp_cache_lookup(project_dir: Path, candidate_sha256: str, battery_sha256: str) -> "dict | None":
    """Return cached fingerprint dict or None. Last-write-wins on duplicate keys."""
    path = _fp_cache_path(project_dir)
    if not path.exists():
        return None
    result = None
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            if (row.get("candidate_sha256") == candidate_sha256
                    and row.get("battery_sha256") == battery_sha256):
                result = row.get("fingerprint")  # last write wins
    except Exception:  # noqa: BLE001
        pass
    return result


def _fp_cache_append(project_dir: Path, candidate_sha256: str, battery_sha256: str,
                     fp: dict) -> None:
    """Append a cache row. Best-effort; never raises."""
    try:
        path = _fp_cache_path(project_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "schema": _FP_CACHE_SCHEMA,
            "candidate_sha256": candidate_sha256,
            "battery_sha256": battery_sha256,
            "fingerprint": fp,
        }
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:  # noqa: BLE001
        pass


def fingerprint(
    candidate_path: "str | Path",
    battery: list[dict],
    project_dir: "str | Path",
) -> dict:
    """Fingerprint a candidate on the probe battery.

    Returns:
      {sha16: str, exact_count: int, vector_len: int,
       load_error: str|None, predictions_top20: list}

    sha16 = first 16 hex chars of sha256 of:
      (tuple of (predicted==s_next bools for all battery probes)
       + canonical JSON of predictions on top-20 highest-provenance probes)

    Two candidates wrong in DIFFERENT ways get different fingerprints because
    their prediction outputs differ even when both are wrong.

    On-disk memo: workspace/version_space_fp_cache.jsonl keyed by
    (candidate source sha256, battery sha256). Cache hit skips execution.
    Append-only ledger; last-write-wins on read (mirrors prune-ledger idiom).
    """
    candidate_path = Path(candidate_path).resolve()
    project_dir = Path(project_dir).resolve()

    ep = resolve_episode_paths(project_dir)
    visible_path = ep["visible"]
    if visible_path is None or not visible_path.exists():
        return {"sha16": "no_episode", "exact_count": 0, "vector_len": 0,
                "load_error": "no visible episode"}

    # Cache lookup: (candidate source sha256, battery sha256) → fingerprint dict.
    # ponytail: sha256 of source bytes + sha256 of battery JSON = stable content key.
    try:
        candidate_sha256 = hashlib.sha256(candidate_path.read_bytes()).hexdigest()
    except Exception:  # noqa: BLE001
        candidate_sha256 = ""
    battery_sha256 = _battery_sha(battery)
    if candidate_sha256:
        cached = _fp_cache_lookup(project_dir, candidate_sha256, battery_sha256)
        if cached is not None:
            return cached

    log = EpisodeLog.read_jsonl(visible_path)
    rows = list(log)

    try:
        source = candidate_path.read_text()
        program = _load_carrier_from_source(source, str(candidate_path), project_dir)
        load_error = None
    except Exception as exc:  # noqa: BLE001
        return {"sha16": "load_error", "exact_count": 0, "vector_len": len(battery),
                "load_error": str(exc)[:300]}

    predict = as_predictor(program)
    booleans: list[bool] = []
    preds_raw: list[Any] = []  # raw predictions for top-20

    # Sort battery by provenance_count desc to identify top-20
    sorted_battery = sorted(battery, key=lambda x: -x["provenance_count"])
    top20_indices = {b["row_index"] for b in sorted_battery[:20]}

    top20_preds: dict[int, Any] = {}

    for probe in battery:
        idx = probe["row_index"]
        if idx >= len(rows):
            booleans.append(False)
            continue
        tr = rows[idx]
        predicted = predict(tr.s, tr.a, tr.t)
        correct = predicted is not None and predicted == tr.s_next
        booleans.append(correct)
        if idx in top20_indices:
            # Serialize prediction for distinguishing-power
            top20_preds[idx] = _grid_to_json(predicted)

    # Canonical serialization: booleans tuple + top20 predictions keyed by index
    canonical_top20 = json.dumps(
        {str(k): v for k, v in sorted(top20_preds.items())},
        separators=(",", ":"), sort_keys=True
    )
    fingerprint_payload = json.dumps(
        [int(b) for b in booleans], separators=(",", ":")
    ) + "|" + canonical_top20

    sha16 = hashlib.sha256(fingerprint_payload.encode()).hexdigest()[:16]
    exact_count = sum(booleans)

    result = {
        "sha16": sha16,
        "exact_count": exact_count,
        "vector_len": len(booleans),
        "load_error": None,
    }
    if candidate_sha256:
        _fp_cache_append(project_dir, candidate_sha256, battery_sha256, result)
    return result


def _grid_to_json(grid: Any) -> Any:
    if grid is None:
        return None
    try:
        return [list(row) for row in grid]
    except Exception:  # noqa: BLE001
        return None


# ── version space ledger ──────────────────────────────────────────────────────

_LEDGER_SCHEMA = "ztare.version_space.v1"


def _ledger_path(project_dir: Path) -> Path:
    p = project_dir / "workspace" / "version_space.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load_prunes(project_dir: Path) -> tuple[set[str], set[str]]:
    """Return (pruned_refs, pruned_fps) from version_space_prunes.jsonl.

    Join keys: candidate_ref OR fingerprint — a prune row carries both.
    Either match is sufficient to exclude the candidate from load().
    """
    # ponytail: two sets so load() can join on whichever key is non-None
    pruned_refs: set[str] = set()
    pruned_fps: set[str] = set()
    p = project_dir / "workspace" / "version_space_prunes.jsonl"
    if not p.exists():
        return pruned_refs, pruned_fps
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        ref = row.get("candidate_ref")
        fp = row.get("fingerprint")
        if ref:
            pruned_refs.add(str(ref))
        if fp:
            pruned_fps.add(str(fp))
    return pruned_refs, pruned_fps


def load(project_dir: "str | Path") -> list[dict]:
    """Return current survivor set (admitted, not duplicate, rejected, or pruned).

    Keyed by candidate_ref (file path) so that:
      - A 'duplicate' record for path B doesn't cancel an 'admitted' record
        for path A, even if A and B share the same source content/sha.
      - The latest record for each path wins (append-only ledger).
    Deduplication by fingerprint is enforced at admit() time (TOCTOU race
    produces duplicate admitted records for the same fingerprint; load() returns
    both — callers that need strict behavioral dedup should filter by fingerprint).

    Prune join: candidates present in version_space_prunes.jsonl (written by
    distinguishing_play.prune()) are EXCLUDED — join on candidate_ref OR fingerprint.
    """
    project_dir = Path(project_dir).resolve()
    lp = _ledger_path(project_dir)
    if not lp.exists():
        return []
    pruned_refs, pruned_fps = _load_prunes(project_dir)
    # latest record per candidate_ref
    by_ref: dict[str, dict] = {}
    for line in lp.read_text().splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except Exception:  # noqa: BLE001
            continue
        if rec.get("schema") != _LEDGER_SCHEMA:
            continue
        ref = rec.get("candidate_ref")
        if ref:
            by_ref[ref] = rec  # last write wins per path
    # Only return admitted records; for distinct fingerprints only (take first per fp)
    # Exclude any candidate whose ref OR fingerprint appears in the prune ledger
    seen_fps: set[str] = set()
    survivors: list[dict] = []
    for rec in by_ref.values():
        if rec.get("status") != "admitted":
            continue
        ref = rec.get("candidate_ref")
        fp = rec.get("fingerprint")
        # Prune join: skip if ref or fingerprint was pruned by distinguishing play
        if ref and ref in pruned_refs:
            continue
        if fp and fp in pruned_fps:
            continue
        if fp and fp in seen_fps:
            continue
        seen_fps.add(fp)
        survivors.append(rec)
    return survivors


def admit(candidate_path: "str | Path", project_dir: "str | Path") -> dict:
    """Admit a candidate into the version space.

    Gate: visible-perfect (wrong_rows empty) via build_row_bitmap.
    Status: admitted | rejected | duplicate.
    Returns the ledger record appended.
    """
    candidate_path = Path(candidate_path).resolve()
    project_dir = Path(project_dir).resolve()

    ep = resolve_episode_paths(project_dir)
    visible_path = ep["visible"]

    # Can't admit without visible episode
    if visible_path is None or not visible_path.exists():
        return {"error": "no visible episode", "candidate": str(candidate_path)}

    # Build bitmap (uses cache if available)
    try:
        bm = build_row_bitmap(candidate_path, visible_path, project_dir=project_dir)
    except Exception as exc:  # noqa: BLE001
        rec = _make_record(candidate_path, None, None, 0, 0, "rejected",
                           note=f"bitmap_error:{str(exc)[:200]}")
        _append_record(project_dir, rec)
        return rec

    visible_exact = bm.get("exact_count", 0)
    visible_total = bm.get("total_rows", 0) - len(bm.get("env_frame_indices", []))
    wrong_rows = bm.get("wrong_rows", [])

    if wrong_rows:
        # Not visible-perfect
        rec = _make_record(candidate_path, None, None, visible_exact, visible_total,
                           "rejected", note=f"wrong_rows:{len(wrong_rows)}")
        _append_record(project_dir, rec)
        return rec

    # Compute fingerprint
    battery = probe_battery(project_dir)
    fp = fingerprint(candidate_path, battery, project_dir)

    if fp.get("load_error"):
        rec = _make_record(candidate_path, None, fp["sha16"], visible_exact, visible_total,
                           "rejected", note=f"fingerprint_load_error:{fp['load_error'][:100]}")
        _append_record(project_dir, rec)
        return rec

    sha16 = fp["sha16"]

    # Check for duplicate fingerprint in current survivors
    existing = load(project_dir)
    existing_fps = {s.get("fingerprint") for s in existing}
    candidate_sha = hashlib.sha256(candidate_path.read_bytes()).hexdigest()[:16]

    if sha16 in existing_fps:
        # Find who it duplicates
        dup_of = next((s["candidate_ref"] for s in existing if s.get("fingerprint") == sha16), None)
        rec = _make_record(candidate_path, candidate_sha, sha16, visible_exact, visible_total,
                           "duplicate", note=f"duplicate_of:{dup_of}")
        _append_record(project_dir, rec)
        return rec

    rec = _make_record(candidate_path, candidate_sha, sha16, visible_exact, visible_total,
                       "admitted")
    _append_record(project_dir, rec)
    return rec


def _make_record(
    candidate_path: Path,
    candidate_sha: "str | None",
    fp_sha16: "str | None",
    visible_exact: int,
    visible_total: int,
    status: str,
    note: "str | None" = None,
) -> dict:
    rec: dict = {
        "schema": _LEDGER_SCHEMA,
        "candidate_ref": str(candidate_path),
        "candidate_sha": candidate_sha or hashlib.sha256(candidate_path.read_bytes()).hexdigest()[:16],
        "fingerprint": fp_sha16,
        "visible_exact": visible_exact,
        "visible_total": visible_total,
        "status": status,
        # warrant: admission gate used; field exists so leanmill lift to S3 has somewhere to land
        "warrant": "S2_gate_checked",
    }
    if note:
        rec["note"] = note
    return rec


def _append_record(project_dir: Path, rec: dict) -> None:
    lp = _ledger_path(project_dir)
    with lp.open("a") as f:
        f.write(json.dumps(rec) + "\n")


# ── seed from history ─────────────────────────────────────────────────────────

def seed_from_history(project_dir: "str | Path") -> dict:
    """Scan candidate files in the project and admit each.

    Scans:
      - workspace/submissions/*.py
      - workspace/candidate_*.py
      - workspace/test_model_pre_materialization_*.py
      - test_model.py (project root)

    Returns summary dict.
    """
    project_dir = Path(project_dir).resolve()
    ws = project_dir / "workspace"

    candidate_files: list[Path] = []

    # workspace/submissions/*.py
    sub_dir = ws / "submissions"
    if sub_dir.is_dir():
        candidate_files.extend(sorted(sub_dir.glob("*.py")))

    # workspace/candidate_*.py
    candidate_files.extend(sorted(ws.glob("candidate_*.py")))

    # workspace/test_model_pre_materialization_*.py
    candidate_files.extend(sorted(ws.glob("test_model_pre_materialization_*.py")))

    # test_model.py at project root
    tm = project_dir / "test_model.py"
    if tm.exists():
        candidate_files.append(tm)

    results: dict[str, int] = {"admitted": 0, "rejected": 0, "duplicate": 0,
                                "error": 0, "total_scanned": 0}
    for p in candidate_files:
        if not p.exists():
            continue
        results["total_scanned"] += 1
        try:
            rec = admit(p, project_dir)
            status = rec.get("status", "error")
            if status in results:
                results[status] += 1
            else:
                results["error"] += 1
        except Exception:  # noqa: BLE001
            results["error"] += 1

    results["n_survivors"] = len(load(project_dir))
    return results


# ── disagreement report ───────────────────────────────────────────────────────

def disagreement_report(project_dir: "str | Path") -> dict:
    """Compute per-probe disagreements across surviving population.

    Writes workspace/version_space_disagreements.jsonl (append row).
    Returns the report dict.
    """
    project_dir = Path(project_dir).resolve()
    survivors = load(project_dir)
    ep = resolve_episode_paths(project_dir)
    visible_path = ep["visible"]

    if not survivors:
        report = {
            "schema": "ztare.vs_disagreements.v1",
            "n_survivors": 0,
            "n_distinct_fingerprints": 0,
            "note": "no survivors — admit candidates first",
        }
        _append_disagreement(project_dir, report)
        return report

    distinct_fps = len({s.get("fingerprint") for s in survivors})

    if visible_path is None or not visible_path.exists():
        report = {
            "schema": "ztare.vs_disagreements.v1",
            "n_survivors": len(survivors),
            "n_distinct_fingerprints": distinct_fps,
            "note": "no visible episode — cannot compute disagreements",
        }
        _append_disagreement(project_dir, report)
        return report

    log = EpisodeLog.read_jsonl(visible_path)
    rows = list(log)
    battery = probe_battery(project_dir)

    if not battery:
        report = {
            "schema": "ztare.vs_disagreements.v1",
            "n_survivors": len(survivors),
            "n_distinct_fingerprints": distinct_fps,
            "note": "empty battery — no rows to probe",
        }
        _append_disagreement(project_dir, report)
        return report

    # Load programs for all survivors
    programs: list[tuple[str, Any]] = []
    for s in survivors:
        ref = s["candidate_ref"]
        try:
            p = Path(ref)
            source = p.read_text()
            prog = _load_carrier_from_source(source, ref, project_dir)
            programs.append((ref, prog))
        except Exception:  # noqa: BLE001
            continue  # skip unloadable survivors — they were admitted but source gone

    if len(programs) < 2:
        report = {
            "schema": "ztare.vs_disagreements.v1",
            "n_survivors": len(survivors),
            "n_distinct_fingerprints": distinct_fps,
            "note": f"only {len(programs)} loadable survivors — need ≥2 for disagreements",
        }
        _append_disagreement(project_dir, report)
        return report

    # For each probe, collect predictions per survivor
    # prediction: (predicted_grid_canonical, correct_bool)
    probe_preds: list[dict] = []  # {row_index, t, action, preds_by_ref}

    for probe in battery:
        idx = probe["row_index"]
        if idx >= len(rows):
            continue
        tr = rows[idx]
        preds: dict[str, Any] = {}
        for ref, prog in programs:
            predict = as_predictor(prog)
            try:
                out = predict(tr.s, tr.a, tr.t)
            except Exception:  # noqa: BLE001
                out = None
            preds[ref] = _grid_to_json(out)
        # Check if any pair disagrees
        pred_values = list(preds.values())
        unique_preds = {json.dumps(v, separators=(",", ":"), default=str) for v in pred_values}
        if len(unique_preds) > 1:
            probe_preds.append({
                "row_index": idx,
                "t": tr.t,
                "action": tr.a,
                "provenance_count": probe["provenance_count"],
                "n_unique_predictions": len(unique_preds),
                "survivor_split": _survivor_split(preds),
            })

    if not probe_preds:
        # All survivors agree everywhere on the battery
        # Recommend frontier states as distinguishing experiments
        frontier_note = _frontier_note(project_dir)
        report = {
            "schema": "ztare.vs_disagreements.v1",
            "n_survivors": len(survivors),
            "n_distinct_fingerprints": distinct_fps,
            "disagreement_states": [],
            "note": (
                "population is behaviorally collapsed on battery — "
                "survivors are identical clones on visible; "
                "distinguishing evidence must come from NEW states. "
                + frontier_note
            ),
        }
        _append_disagreement(project_dir, report)
        return report

    # Rank by n_unique_predictions desc, then provenance_count desc
    probe_preds.sort(key=lambda x: (-x["n_unique_predictions"], -x["provenance_count"]))
    top10 = probe_preds[:10]

    # Aggregate per (t, action) — count how many probes disagree there
    ta_counts: dict[tuple, int] = {}
    for p in probe_preds:
        key = (p["t"], p["action"])
        ta_counts[key] = ta_counts.get(key, 0) + 1

    top_ta = sorted(ta_counts.items(), key=lambda x: -x[1])[:5]

    # Cell-region aggregation: find most-contested (row, col) cells across disagreements
    cell_counts: dict[tuple, int] = {}
    for p in probe_preds:
        for split_group in p["survivor_split"]:
            pred_grid = split_group.get("prediction")
            if pred_grid is None:
                continue
            # Count cells that are non-zero (active) in the prediction
            try:
                for r, row in enumerate(pred_grid):
                    for c, val in enumerate(row):
                        if val != 0:
                            cell_counts[(r, c)] = cell_counts.get((r, c), 0) + 1
            except Exception:  # noqa: BLE001
                pass

    top_cells = sorted(cell_counts.items(), key=lambda x: -x[1])[:5]

    report = {
        "schema": "ztare.vs_disagreements.v1",
        "n_survivors": len(survivors),
        "n_distinct_fingerprints": distinct_fps,
        "n_disagreement_probes": len(probe_preds),
        "disagreement_states": [
            {
                "t": p["t"],
                "action": p["action"],
                "row_index": p["row_index"],
                "n_unique_predictions": p["n_unique_predictions"],
                # raw survivor-split counts per target; price via pricing_hook below
                "survivor_split": [
                    {"n_survivors": len(g["survivors"]), "survivors": g["survivors"],
                     "prediction": g["prediction"]}
                    for g in p["survivor_split"]
                ],
                # pricing hook: score this target via residual_information_yield
                # using survivors as committee and this probe as the experiment
                "pricing_hook": "residual_information_yield",
            }
            for p in top10
        ],
        "top_ta_pairs": [
            {"t": t, "action": a, "n_probes": n} for (t, a), n in top_ta
        ],
        "top_contested_cells": [
            {"row": r, "col": c, "count": n} for (r, c), n in top_cells
        ],
        "note": "play targets — observing these states prunes survivors",
    }
    _append_disagreement(project_dir, report)
    return report


def _survivor_split(preds: dict[str, Any]) -> list[dict]:
    """Group survivors by identical prediction."""
    groups: dict[str, list] = {}
    for ref, pred in preds.items():
        key = json.dumps(pred, separators=(",", ":"), default=str)
        groups.setdefault(key, []).append(ref)
    result = []
    for key, refs in groups.items():
        try:
            pred_val = json.loads(key)
        except Exception:  # noqa: BLE001
            pred_val = None
        result.append({"prediction": pred_val, "survivors": refs})
    return result


def _frontier_note(project_dir: Path) -> str:
    """Point at visited_signatures.jsonl if it exists as a source of frontier states."""
    vs = project_dir / "workspace" / "visited_signatures.jsonl"
    if vs.exists():
        try:
            n = sum(1 for l in vs.read_text().splitlines() if l.strip())
            return f"recommend frontier states from visited_signatures.jsonl ({n} signatures available)"
        except Exception:  # noqa: BLE001
            pass
    return "recommend frontier states from the visited store (visited_signatures.jsonl)"


def _append_disagreement(project_dir: Path, report: dict) -> None:
    p = project_dir / "workspace" / "version_space_disagreements.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(report) + "\n")


# ── CLI ───────────────────────────────────────────────────────────────────────

def _cli() -> int:
    import argparse

    ap = argparse.ArgumentParser(
        description="Version-space ledger: population of surviving world-model programs."
    )
    ap.add_argument("--project", required=True, help="Project directory")
    ap.add_argument("--seed", action="store_true",
                    help="Seed from history (submissions + candidates + test_model)")
    ap.add_argument("--report", action="store_true",
                    help="Compute and print disagreement report")
    ap.add_argument("--admit", nargs="+", metavar="CANDIDATE",
                    help="Admit specific candidate file(s)")
    args = ap.parse_args()

    project_dir = Path(args.project).resolve()

    if args.admit:
        for cpath in args.admit:
            rec = admit(cpath, project_dir)
            print(json.dumps(rec, indent=2))

    if args.seed:
        summary = seed_from_history(project_dir)
        print(json.dumps(summary, indent=2))

    if args.report:
        report = disagreement_report(project_dir)
        print(json.dumps(report, indent=2))

    if not args.admit and not args.seed and not args.report:
        survivors = load(project_dir)
        print(f"survivors: {len(survivors)}")
        fps = {s.get('fingerprint') for s in survivors}
        print(f"distinct fingerprints: {len(fps)}")
        for s in survivors:
            print(f"  {s['fingerprint'][:12]}  {Path(s['candidate_ref']).name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
