"""Champion Materialization From Memory.

Scans workspace candidate artifacts, runs the project's gate harness on each,
and promotes the best dominance-eligible candidate to test_model.py.

Entry point: materialize_champion_from_memory(project_dir)

Env gate: ZTARE_CHAMPION_MATERIALIZATION (default "1"; set "0" to disable).
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ztare.validator.core.pre_judge_gate import run_gate_harness_subprocess

_MAX_CANDIDATES = 8
_MAX_FILE_BYTES = 2 * 1024 * 1024  # 2 MB


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ts() -> str:
    return datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%S")


def _collect_candidates(project_dir: Path) -> list[Path]:
    """Gather candidate_*.py + submissions/*.py, dedupe by sha256, cap at N=8 most recent."""
    workspace = project_dir / "workspace"
    globs = list(workspace.glob("candidate_*.py")) + list(
        (workspace / "submissions").glob("*.py") if (workspace / "submissions").is_dir() else []
    )
    # filter size
    ok: list[Path] = [p for p in globs if p.is_file() and p.stat().st_size <= _MAX_FILE_BYTES]
    # dedupe by sha256
    seen: set[str] = set()
    deduped: list[Path] = []
    for p in sorted(ok, key=lambda p: p.stat().st_mtime, reverse=True):
        h = _sha256(p)
        if h not in seen:
            seen.add(h)
            deduped.append(p)
        if len(deduped) >= _MAX_CANDIDATES:
            break
    return deduped


def _run_harness(project_dir: Path, candidate_path: Path) -> dict[str, Any] | None:
    """Run gate_harness.py --emit-deterministic-gates --candidate-path X.

    Returns the JSON payload or None on error.
    """
    harness = project_dir / "gate_harness.py"
    if not harness.exists():
        return None
    try:
        stdout = run_gate_harness_subprocess(
            project_dir=project_dir,
            python_executable=sys.executable,
            gate_harness_path=harness,
            candidate_path=candidate_path,
            timeout_seconds=120,
        )
        payload = json.loads(stdout)
        return payload if isinstance(payload, dict) else None
    except Exception:  # noqa: BLE001
        return None


def _dominance_check(
    project_dir: Path,
    candidate_path: Path,
    gate_payload: dict[str, Any],
) -> bool:
    """Return True iff the candidate is dominance-promotable.

    Delegates entirely to the live pre_judge_gate functions — no reimplementation.
    """
    from ztare.validator.core.pre_judge_gate import (
        _candidate_prior_comparison_receipt,
        _dominance_inputs,
        _dominance_promotion_ok,
        _normalize_gate_iter,
    )

    gate_iter = _normalize_gate_iter(gate_payload)
    if not gate_iter or not gate_payload.get("harness_ok"):
        return False
    comparison = _candidate_prior_comparison_receipt(
        project_dir=project_dir,
        candidate_path=candidate_path,
        gate_payload=gate_payload,
    )
    champion_heldout, strict_improved = _dominance_inputs(comparison)
    return _dominance_promotion_ok(
        gate_payload,
        gate_iter,
        champion_heldout=champion_heldout,
        strict_improved=strict_improved,
    )


def _observed_tier_passes(gate_payload: dict[str, Any]) -> bool:
    """All observed-tier gates must pass — safety invariant."""
    from ztare.validator.core.pre_judge_gate import _gate_tier, _gate_passed, _normalize_gate_iter

    if not gate_payload.get("harness_ok"):
        return False
    for gate in _normalize_gate_iter(gate_payload):
        if _gate_tier(gate) == "observed" and not _gate_passed(gate):
            return False
    return True


def _rank_key(gate_payload: dict[str, Any]) -> tuple:
    """(observed exact rows, -wrong cells, heldout depth) — higher is better."""
    from ztare.validator.core.pre_judge_gate import _visible_diagnostics, _gates_dict

    diag = _visible_diagnostics(gate_payload)
    exact = int(diag.get("exact_rows") or 0)
    wrong = int(diag.get("wrong_cell_count") or 0)
    gates = _gates_dict(gate_payload)
    holdout = gates.get("holdout_rollout_exact") or {}
    depth = int(holdout.get("value") or 0) if isinstance(holdout, dict) else 0
    return (exact, -wrong, depth)


def _live_gate_result(project_dir: Path) -> dict[str, Any] | None:
    """Run the harness against the CURRENT test_model.py (no --candidate-path)."""
    harness = project_dir / "gate_harness.py"
    if not harness.exists():
        return None
    try:
        stdout = run_gate_harness_subprocess(
            project_dir=project_dir,
            python_executable=sys.executable,
            gate_harness_path=harness,
            candidate_path=None,  # live test_model.py
            timeout_seconds=120,
        )
        payload = json.loads(stdout)
        return payload if isinstance(payload, dict) else None
    except Exception:  # noqa: BLE001
        return None


def _write_receipt(workspace: Path, row: dict[str, Any]) -> None:
    ledger = workspace / "champion_materialization.jsonl"
    with ledger.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True, default=str) + "\n")


def materialize_champion_from_memory(project_dir: str | Path) -> dict[str, Any]:
    """Promote the best memory candidate to test_model.py if it dominates the live model.

    Returns the receipt dict (also appended to workspace/champion_materialization.jsonl).
    """
    if os.environ.get("ZTARE_CHAMPION_MATERIALIZATION", "1") == "0":
        return {"schema": "champion_materialization_v1", "result": "disabled", "ts": _ts()}

    project_dir = Path(project_dir).resolve()
    workspace = project_dir / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)

    candidates = _collect_candidates(project_dir)
    if not candidates:
        row: dict[str, Any] = {
            "schema": "champion_materialization_v1",
            "result": "no_op",
            "reason": "no candidate artifacts found",
            "ts": _ts(),
        }
        _write_receipt(workspace, row)
        return row

    # Evaluate candidates — keep only observed-safe + dominance-promotable ones
    promotable: list[tuple[tuple, Path, dict[str, Any]]] = []
    for cand in candidates:
        payload = _run_harness(project_dir, cand)
        if payload is None:
            continue
        if not _observed_tier_passes(payload):
            continue
        if not _dominance_check(project_dir, cand, payload):
            continue
        promotable.append((_rank_key(payload), cand, payload))

    if not promotable:
        row = {
            "schema": "champion_materialization_v1",
            "result": "no_op",
            "reason": f"no candidate among {len(candidates)} passed observed gates + dominance",
            "ts": _ts(),
        }
        _write_receipt(workspace, row)
        return row

    # Best candidate by rank key
    best_rank, best_path, best_payload = max(promotable, key=lambda t: t[0])

    # Compare against LIVE test_model.py
    live_payload = _live_gate_result(project_dir)
    if live_payload is not None:
        live_rank = _rank_key(live_payload)
        if best_rank <= live_rank:
            row = {
                "schema": "champion_materialization_v1",
                "result": "no_op",
                "reason": (
                    f"best candidate rank {best_rank} does not strictly dominate "
                    f"live test_model rank {live_rank}"
                ),
                "ts": _ts(),
            }
            _write_receipt(workspace, row)
            return row

    # Promote: backup + install
    test_model = project_dir / "test_model.py"
    ts = _ts()
    backup_path = workspace / f"test_model_pre_materialization_{ts}.py"

    gate_before: dict[str, Any] = live_payload or {}
    promoted_sha = _sha256(best_path)

    if test_model.exists():
        backup_path.write_bytes(test_model.read_bytes())

    test_model.write_bytes(best_path.read_bytes())

    # Gate result after install — quick verify
    gate_after = _live_gate_result(project_dir) or {}

    row = {
        "schema": "champion_materialization_v1",
        "result": "promoted",
        "promoted_sha": promoted_sha[:16],
        "from_ref": str(best_path.relative_to(project_dir)),
        "backup_ref": str(backup_path.relative_to(project_dir)),
        "gate_summary_before": {
            "harness_ok": gate_before.get("harness_ok"),
            "gated_sha256": gate_before.get("gated_sha256"),
            "score": gate_before.get("score"),
        },
        "gate_summary_after": {
            "harness_ok": gate_after.get("harness_ok"),
            "gated_sha256": gate_after.get("gated_sha256"),
            "score": gate_after.get("score"),
        },
        "dominance_receipt": {
            "rank_before": live_rank if live_payload else None,
            "rank_after": best_rank,
        },
        "ts": ts,
    }
    _write_receipt(workspace, row)
    return row
