from __future__ import annotations

import json
import hashlib
import logging
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ztare.common.candidate_memory import admissible_candidate_memory_records

_log = logging.getLogger(__name__)

# ZTARE_BATCH_GATE=1: use batch_gate in-process instead of subprocess harness.
# Default stays subprocess (engine-invariant: full-scan batch_gate is verdict-
# identical to gate_harness.py by design, proven in batch_gate module docstring).
_BATCH_GATE_ENABLED = os.environ.get("ZTARE_BATCH_GATE", "0") == "1"

# Gate result cache: keyed by (candidate_sha256, harness_sha256, episode_mtime_fingerprint,
# engine) → raw stdout bytes.  Bounded to newest 200 entries.
# ponytail: module-level dict + lru-eviction; no persistence needed (results are
# deterministic within a process run; the key covers all content-relevant surfaces).
# Engine is in the key because payload structure details differ across engines
# (though both now include grid_dsl_expressible — see FIX 1 parity proof).
_GATE_RESULT_CACHE: dict[str, str] = {}
_GATE_RESULT_CACHE_BOUND = 200
_GATE_CACHE_DIR_NAME = "gate_result_cache"


def _run_batch_gate_inprocess(
    project_dir: Path,
    candidate_path: "Path | None",
) -> "dict | None":
    """Run batch_gate in-process for a single candidate; return gate_payload dict.

    Returns None if batch_gate cannot run (no harness, no episodes). Attests
    engine: 'batch_inprocess' in the returned payload so receipts are traceable.
    """
    try:
        from ztare.worldmodel.batch_gate import batch_gate
    except Exception:  # noqa: BLE001
        return None
    cpath = candidate_path or (project_dir / "test_model.py")
    if not Path(cpath).exists():
        return None
    results = batch_gate(project_dir, [cpath], episodes=("visible", "holdout"))
    if not results:
        return None
    r = results[0]
    # translate batch_gate result dict → gate_harness gate_payload shape
    load_err = r.get("load_error")
    harness_ok = load_err is None
    visible_exact = int(r.get("visible_exact") or 0)
    visible_total = int(r.get("visible_total") or 0)
    env_excluded = int(r.get("visible_env_excluded") or 0)
    checked = visible_total - env_excluded
    wrong_rows = list(r.get("wrong_rows") or [])
    holdout_depth = int(r.get("holdout_depth") or -1)
    holdout_total = int(r.get("holdout_total") or 0)
    import hashlib as _hl
    try:
        ctext = Path(cpath).read_text()
        gated_sha = _hl.sha256(ctext.encode()).hexdigest()[:16]
    except Exception:  # noqa: BLE001
        gated_sha = "unreadable"
    visible_ok = (load_err is None and checked > 0 and len(wrong_rows) == 0)
    holdout_ok = (load_err is None and holdout_depth >= holdout_total and holdout_total > 0)
    # grid_dsl_expressible: now populated by batch_gate (FIX 1 parity).
    dsl_size = int(r.get("grid_dsl_size") or -1)
    dsl_pass = bool(r.get("grid_dsl_expressible", False)) if load_err is None else False
    gates: dict = {
        "grid_dsl_expressible": {
            "name": "grid_dsl_expressible",
            "value": dsl_size,
            "threshold": 1,
            "pass": dsl_pass,
            "detail": "python callable carrier (size -2; no AST certificate)" if dsl_size == -2 else "",
        },
        "visible_replay_exact": {
            "name": "visible_replay_exact",
            "tier": "observed",
            "value": 0 if visible_ok else 1,
            "threshold": 0,
            "pass": visible_ok,
            "detail": load_err or ("batch_inprocess replay" if visible_ok else f"{len(wrong_rows)} wrong rows"),
            "diagnostics": {
                "checked_rows": checked,
                "exact_rows": visible_exact,
                "wrong_rows": wrong_rows[:20],
                "wrong_cell_count": len(wrong_rows),
                "first_mismatch": str(wrong_rows[0]) if wrong_rows else "",
                "mismatch_classes": [],
                "first_mismatch_signature": {},
            },
        },
        "holdout_rollout_exact": {
            "name": "holdout_rollout_exact",
            "tier": "heldout",
            "value": holdout_depth,
            "threshold": holdout_total,
            "pass": holdout_ok,
            "holdout_witness": {},
        },
    }
    n_gates = len(gates)
    n_passed = sum(1 for g in gates.values() if g["pass"])
    return {
        "harness_ok": harness_ok,
        "gates": gates,
        "score": round(n_passed / n_gates, 4) if n_gates else 0,
        "gated_file": str(cpath),
        "gated_sha256": gated_sha,
        "engine": "batch_inprocess",
        **({"load_error": load_err} if load_err else {}),
        **({"carrier": r.get("carrier")} if r.get("carrier") else {}),
    }


def _episode_mtime_fingerprint(project_dir: Path) -> str:
    """Stable fingerprint of episode file mtimes for the gate cache key."""
    episodes_dir = project_dir / "raw" / "episodes"
    parts: list[str] = []
    try:
        for ep in sorted(episodes_dir.glob("*.jsonl")):
            try:
                parts.append(f"{ep.name}:{ep.stat().st_mtime}")
            except OSError:
                parts.append(ep.name)
    except OSError:
        pass
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]


def _gate_cache_key(
    project_dir: Path,
    candidate_path: "Path | None",
    harness_path: Path,
) -> "str | None":
    """Content-addressed cache key string, or None if any surface is unreadable."""
    try:
        cand_sha = hashlib.sha256(Path(candidate_path).read_bytes()).hexdigest()[:16] if candidate_path else "live"
        harness_sha = hashlib.sha256(harness_path.read_bytes()).hexdigest()[:16]
        ep_fp = _episode_mtime_fingerprint(project_dir)
        # Engine IS part of the key: the engines produce the same gate set
        # (grid_dsl_expressible now included in batch_inprocess) but payload
        # structure details may still differ; keying by engine remains correct.
        engine = "batch" if _BATCH_GATE_ENABLED else "subprocess"
        return f"{cand_sha}:{harness_sha}:{ep_fp}:{engine}"
    except Exception:
        return None


def run_gate_harness_subprocess(
    *,
    project_dir: Path,
    python_executable: str,
    gate_harness_path: Path,
    candidate_path: "Path | None",
    timeout_seconds: int,
    workspace_cache_dir: "Path | None" = None,
) -> str:
    """Run gate_harness.py --emit-deterministic-gates, with a content-addressed
    result cache keyed on (candidate sha256, harness sha256, episode file mtimes).

    Returns raw stdout.  Raises RuntimeError on harness error.  On cache hit logs
    one line 'gate cache hit <sha8>' and skips the subprocess.
    """
    cache_key = _gate_cache_key(project_dir, candidate_path, gate_harness_path)

    if cache_key is not None and cache_key in _GATE_RESULT_CACHE:
        _log.info("gate cache hit %s", cache_key[:8])
        return _GATE_RESULT_CACHE[cache_key]

    gate_cmd = [
        python_executable,
        str(gate_harness_path.resolve()),
        "--emit-deterministic-gates",
    ]
    if candidate_path is not None:
        gate_cmd.extend(["--candidate-path", str(Path(candidate_path).resolve())])

    try:
        gate_res = subprocess.run(
            gate_cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=project_dir,
        )
    except subprocess.TimeoutExpired:
        cand_sha = (
            hashlib.sha256(Path(candidate_path).read_bytes()).hexdigest()[:16]
            if candidate_path is not None
            else None
        )
        receipt = {
            "schema": "ztare.gate_complexity_verdict.v1",
            "verdict": "timeout",
            "stage": "gate_harness_subprocess",
            "budget_seconds": timeout_seconds,
            "candidate_ref": str(candidate_path) if candidate_path is not None else None,
            "candidate_sha": cand_sha,
        }
        _append_gate_receipt(project_dir, receipt)
        raise RuntimeError(
            f"gate_harness.py timed out after {timeout_seconds}s "
            f"(computationally unusable under the rollout gate)"
        )
    if gate_res.returncode != 0:
        raise RuntimeError(
            "gate_harness.py exited nonzero "
            f"({gate_res.returncode}): {gate_res.stderr.strip()[:500]}"
        )
    if not gate_res.stdout.strip():
        raise RuntimeError(
            "gate_harness.py exited 0 with empty stdout; stderr="
            + gate_res.stderr[:300]
        )

    if cache_key is not None:
        if len(_GATE_RESULT_CACHE) >= _GATE_RESULT_CACHE_BOUND:
            # Evict oldest (first inserted) entry.
            _GATE_RESULT_CACHE.pop(next(iter(_GATE_RESULT_CACHE)), None)
        _GATE_RESULT_CACHE[cache_key] = gate_res.stdout

    return gate_res.stdout


@dataclass(frozen=True)
class PreJudgeGateResult:
    enabled: bool
    ran: bool
    should_skip_judge: bool
    message: str | None = None
    score_cap_reason: str | None = None
    payload: dict[str, Any] | None = None


@dataclass(frozen=True)
class PatchBaseRegressionPreflight:
    regression_receipt: dict[str, Any]
    failed_gates: list[str]
    counterexample_trace: dict[str, Any]
    gate_payload: dict[str, Any]


def _gate_passed(gate: Any) -> bool:
    if not isinstance(gate, dict):
        return False
    return bool(gate.get("passed", gate.get("pass", False)))


def _normalize_gate_iter(payload: dict[str, Any]) -> list[dict[str, Any]]:
    gate_iter = payload.get("gates", [])
    if isinstance(gate_iter, dict):
        gate_iter = list(gate_iter.values())
    if not isinstance(gate_iter, list):
        return []
    return [g for g in gate_iter if isinstance(g, dict)]


def _failed_gate_labels(gates: list[dict[str, Any]], *, harness_ok: bool = True) -> list[str]:
    labels: list[str] = []
    if not harness_ok:
        labels.append("harness_ok: false")
    for gate in gates:
        if not _gate_passed(gate):
            if "passed" not in gate and "pass" not in gate:
                labels.append(f"{gate.get('name', '?')}: missing 'passed' field")
            else:
                labels.append(f"{gate.get('name', '?')}: {gate.get('value', '?')}")
    if not labels and not gates:
        labels.append("?: no gates emitted")
    return labels


def _gate_tier(gate: dict[str, Any]) -> str:
    """Evidence tier of a gate. DEFAULT 'observed' so any untagged gate keeps
    must-pass semantics — nothing weakens silently."""
    tier = gate.get("tier", "observed")
    if tier not in ("observed", "heldout"):
        raise ValueError(f"gate {gate.get('name', '?')!r} has invalid tier {tier!r}")
    return tier


def _dominance_promotion_enabled() -> bool:
    # default ON: the champion-freeze is a confirmed bug. "0" restores the old
    # all-gates-pass path for A/B and regression tests.
    return os.environ.get("ZTARE_DOMINANCE_PROMOTION", "1") != "0"


def _all_gates_passed(gate_payload: dict[str, Any], gates: list[dict[str, Any]]) -> bool:
    return (
        bool(gate_payload.get("harness_ok"))
        and bool(gates)
        and all(_gate_passed(g) for g in gates)
    )


def _dominance_promotion_ok(
    gate_payload: dict[str, Any],
    gates: list[dict[str, Any]],
    *,
    champion_heldout: dict[str, float],
    strict_improved: bool,
) -> bool:
    """Tiered dominance promotion (SUBSTRATE-GENERAL, no game-specific logic).

    Promote iff: harness_ok AND every observed-tier gate passes absolutely AND
    every heldout-tier gate is non-regressing vs the champion's recorded value
    (>= champion, or >= 0 when no champion value is recorded) AND the candidate
    strictly improves something. You may not be required to solve what you have
    not observed before you are allowed to improve what you have.
    """
    if not bool(gate_payload.get("harness_ok")) or not gates:
        return False
    if not strict_improved:
        return False
    for gate in gates:
        if _gate_tier(gate) == "observed":
            if not _gate_passed(gate):
                return False
        else:  # heldout: non-regression, not must-pass
            try:
                value = float(gate.get("value"))
            except (TypeError, ValueError):
                return False  # unscored heldout gate cannot be shown non-regressing
            floor = champion_heldout.get(str(gate.get("name")), 0.0)
            if value < floor:
                return False
    return True


def _dominance_inputs(comparison: dict[str, Any] | None) -> "tuple[dict[str, float], bool]":
    """(champion_heldout, strict_improved) from a prior-comparison receipt.

    No prior champion (comparison None) => first candidate: no heldout floor
    and strict-improvement is vacuous. Strict improvement is PRODUCT-ORDER:
    at least one evidence component strictly better (observed exact rows,
    fewer wrong cells, OR held-out depth) while the observed non-regression
    is separately enforced by the observed-tier must-pass check. A candidate
    equal on visible but strictly deeper on held-out rollout is a strict
    improvement — the dual of the champion-freeze case."""
    if comparison is None:
        return {}, True
    champion_heldout = {
        "holdout_rollout_exact": float(comparison.get("best_prior_holdout_depth") or 0)
    }
    exact_delta = comparison.get("exact_rows_delta")
    wrong_delta = comparison.get("wrong_cells_delta")
    holdout_delta = comparison.get("holdout_depth_delta")
    strict_improved = bool(
        (exact_delta is not None and exact_delta > 0)
        or (exact_delta == 0 and wrong_delta is not None and wrong_delta < 0)
        or (
            (exact_delta == 0 or exact_delta is None)
            and (wrong_delta == 0 or wrong_delta is None)
            and holdout_delta is not None and holdout_delta > 0
        )
    )
    return champion_heldout, strict_improved


def _write_eval(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _append_gate_receipt(project_dir: Path, row: dict[str, Any]) -> None:
    ledger = project_dir / "workspace" / "pre_judge_gate_receipts.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with ledger.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_path(path: Path) -> str | None:
    try:
        if path.exists() and path.is_file():
            return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return None
    return None


def _json_sha(payload: Any) -> str:
    return _sha256_text(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str))


def _candidate_sha(candidate_path: str | Path | None, gate_payload: dict[str, Any]) -> str:
    if candidate_path is not None:
        try:
            return hashlib.sha256(Path(candidate_path).read_bytes()).hexdigest()[:12]
        except Exception:
            pass
    return str(gate_payload.get("gated_sha256") or "")[:12]


def _gates_dict(gate_payload: dict[str, Any]) -> dict[str, Any]:
    """Normalize the gates payload (dict- or list-form) to a name-keyed dict."""
    gates = gate_payload.get("gates") or {}
    if isinstance(gates, list):
        gates = {
            str(g.get("name") or i): g
            for i, g in enumerate(gates)
            if isinstance(g, dict)
        }
    return gates if isinstance(gates, dict) else {}


def _visible_diagnostics(gate_payload: dict[str, Any]) -> dict[str, Any]:
    gates = _gates_dict(gate_payload)
    visible = gates.get("visible_replay_exact") or {}
    if not isinstance(visible, dict):
        return {}
    diagnostics = visible.get("diagnostics") or {}
    return diagnostics if isinstance(diagnostics, dict) else {}


def _holdout_witness(gate_payload: dict[str, Any]) -> dict[str, Any] | None:
    gates = _gates_dict(gate_payload)
    holdout = gates.get("holdout_rollout_exact") or {}
    if not isinstance(holdout, dict):
        return None
    witness = holdout.get("holdout_witness")
    return witness if isinstance(witness, dict) else None


def _counterexample_trace(
    gate_payload: dict[str, Any],
    failed_gates: list[str],
) -> dict[str, Any]:
    diagnostics = _visible_diagnostics(gate_payload)
    signature = diagnostics.get("first_mismatch_signature")
    holdout_witness = _holdout_witness(gate_payload)
    return {
        "schema": "ztare-counterexample-trace-v1",
        "quotient": "first_visible_replay_mismatch",
        "coordinate_contract": {
            "cell_basis": "row_col",
            "bbox_basis": "row_min_col_min_row_max_col_max",
        },
        "failed_gates": list(failed_gates),
        "gated_file": gate_payload.get("gated_file"),
        "gated_sha256": gate_payload.get("gated_sha256"),
        "checked_rows": diagnostics.get("checked_rows"),
        "exact_rows": diagnostics.get("exact_rows"),
        "wrong_rows": diagnostics.get("wrong_rows"),
        "wrong_cell_count": diagnostics.get("wrong_cell_count"),
        "first_mismatch": diagnostics.get("first_mismatch") or "",
        "first_mismatch_signature": signature if isinstance(signature, dict) else {},
        "mismatch_classes": diagnostics.get("mismatch_classes")
        if isinstance(diagnostics.get("mismatch_classes"), list) else [],
        "residual_table": diagnostics.get("residual_table")
        if isinstance(diagnostics.get("residual_table"), list) else [],
        "holdout_witness": holdout_witness or {},
    }


def evaluation_cache_key(
    *,
    project_dir: str | Path,
    candidate_path: str | Path | None,
    gate_payload: dict[str, Any],
    rubric_path: str | Path | None = None,
    extra_paths: list[str | Path] | None = None,
) -> dict[str, Any]:
    """Content-address a status verdict to the verifier footprint.

    The key intentionally includes verifier implementation surfaces, not only
    candidate text. A changed project harness or gate module invalidates cached
    status even when candidate bytes are unchanged.
    """
    project_path = Path(project_dir)
    candidate_full_sha = _sha256_path(Path(candidate_path)) if candidate_path is not None else None
    harness_hash = _sha256_path(project_path / "gate_harness.py")
    module_path = Path(__file__)
    validator_dir = module_path.parents[1]
    src_dir = module_path.parents[2]
    worldmodel_dir = src_dir / "worldmodel"
    gate_module_hash = _sha256_path(module_path)
    footprint: dict[str, Any] = {
        "schema": "ztare-evaluation-cache-key-v1",
        "candidate_sha256": candidate_full_sha or str(gate_payload.get("gated_sha256") or ""),
        "gated_sha256": gate_payload.get("gated_sha256"),
        "gate_payload_sha256": _json_sha(gate_payload),
        "project_gate_harness_sha256": harness_hash,
        "pre_judge_gate_module_sha256": gate_module_hash,
        "test_thesis_module_sha256": _sha256_path(validator_dir / "test_thesis.py"),
        "autoresearch_loop_module_sha256": _sha256_path(validator_dir / "autoresearch_loop.py"),
        "worldmodel_gates_module_sha256": _sha256_path(worldmodel_dir / "gates.py"),
        "patch_base_carrier_module_sha256": _sha256_path(worldmodel_dir / "patch_base_carrier.py"),
        "python_version": ".".join(map(str, sys.version_info[:3])),
        "rubric_sha256": _sha256_path(Path(rubric_path)) if rubric_path is not None else None,
        "extra_path_hashes": {},
    }
    for raw_path in extra_paths or []:
        path = Path(raw_path)
        digest = _sha256_path(path)
        if digest is not None:
            try:
                key = str(path.relative_to(project_path.parent))
            except Exception:
                key = str(path)
            footprint["extra_path_hashes"][key] = digest
    footprint["key_sha256"] = _json_sha(footprint)
    return footprint


def _evaluation_cache_path(project_dir: str | Path) -> Path:
    return Path(project_dir) / "workspace" / "evaluation_by_candidate_sha.json"


def load_cached_evaluation(project_dir: str | Path, cache_key: dict[str, Any]) -> dict[str, Any] | None:
    try:
        payload = json.loads(_evaluation_cache_path(project_dir).read_text(encoding="utf-8"))
    except Exception as exc:
        receipt = {
            "site": "pre_judge_gate.py:67",
            "fallback_taken": "corrupt_cache",
            "cause": f"cache read failed: {type(exc).__name__}",
            "cache_path": str(_evaluation_cache_path(project_dir)),
            "cache_key_sha256": cache_key.get("key_sha256"),
        }
        _append_gate_receipt(Path(project_dir), receipt)
        return {
            "cache_verdict": "corrupt_cache",
            "control_receipt": receipt,
        }
    entries = payload.get("entries") if isinstance(payload, dict) else None
    if not isinstance(entries, dict):
        return None
    entry = entries.get(str(cache_key.get("key_sha256") or ""))
    if not isinstance(entry, dict):
        return None
    evaluation = entry.get("evaluation")
    if not isinstance(evaluation, dict):
        return None
    result = dict(evaluation)
    result["evaluation_cache_hit"] = True
    result["evaluation_cache_key_sha256"] = cache_key.get("key_sha256")
    result["cache_verdict"] = "cache_hit"
    return result


def store_cached_evaluation(
    *,
    project_dir: str | Path,
    cache_key: dict[str, Any],
    evaluation: dict[str, Any],
) -> None:
    path = _evaluation_cache_path(project_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        payload = {"schema": "ztare-evaluation-by-candidate-sha-v1", "entries": {}}
    if not isinstance(payload, dict):
        payload = {"schema": "ztare-evaluation-by-candidate-sha-v1", "entries": {}}
    entries = payload.setdefault("entries", {})
    if not isinstance(entries, dict):
        entries = {}
        payload["entries"] = entries
    key = str(cache_key.get("key_sha256") or "")
    if not key:
        return
    eval_copy = dict(evaluation)
    eval_copy.pop("evaluation_cache_hit", None)
    entries[key] = {
        "schema": "ztare-evaluation-cache-entry-v1",
        "key": cache_key,
        "evaluation": eval_copy,
    }
    _write_eval(path, payload)


def _best_prior_candidate_record(project_dir: Path, *, exclude_sha: str) -> dict[str, Any] | None:
    path = project_dir / "workspace" / "candidate_memory.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        _append_gate_receipt(project_dir, {
            "site": "pre_judge_gate.py:_best_prior_candidate_record",
            "fallback_taken": "corrupt_candidate_memory",
            "cause": repr(exc),
            "path": str(path),
        })
        return None
    records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        return None
    usable = [
        rec for rec in admissible_candidate_memory_records(
            project_dir,
            [rec for rec in records if isinstance(rec, dict)],
            source_types={"deterministic_near_miss"},
            require_submission_source=True,
        )
        if str(rec.get("sha") or "") != exclude_sha
    ]
    if not usable:
        return None
    return max(
        usable,
        key=lambda rec: (
            int(rec.get("visible_exact_rows") or 0),
            int(rec.get("holdout_depth") or 0),
            float(rec.get("gate_score") or 0.0),
            -int(rec.get("visible_wrong_cells") or 0),
        ),
    )


def _candidate_regression_receipt(
    *,
    project_dir: Path,
    candidate_path: str | Path | None,
    gate_payload: dict[str, Any],
    require_strict_improvement: bool = False,
) -> dict[str, Any] | None:
    comparison = _candidate_prior_comparison_receipt(
        project_dir=project_dir,
        candidate_path=candidate_path,
        gate_payload=gate_payload,
    )
    if comparison is None:
        return None
    cur_rank = comparison.pop("_candidate_rank")
    best_rank = comparison.pop("_best_prior_rank")
    regressed = cur_rank < best_rank
    no_strict_improvement = require_strict_improvement and cur_rank <= best_rank
    if not regressed and not no_strict_improvement:
        return None
    comparison["candidate_relation"] = "regression" if regressed else "no_strict_improvement"
    return comparison


def _candidate_prior_comparison_receipt(
    *,
    project_dir: Path,
    candidate_path: str | Path | None,
    gate_payload: dict[str, Any],
) -> dict[str, Any] | None:
    cur = _visible_diagnostics(gate_payload)
    if not cur:
        return None
    if "exact_rows" not in cur:
        # No visible exact-row count: comparison is not possible. Defaulting to
        # 0 would fabricate a regression verdict from absent evidence.
        return None
    cur_sha = _candidate_sha(candidate_path, gate_payload)
    best = _best_prior_candidate_record(project_dir, exclude_sha=cur_sha)
    if best is None:
        return None
    cur_exact = int(cur.get("exact_rows") or 0)
    best_exact = int(best.get("visible_exact_rows") or 0)
    cur_wrong = int(cur.get("wrong_cell_count") or 0)
    best_wrong = int(best.get("visible_wrong_cells") or 0)
    gates = _gates_dict(gate_payload)
    holdout_gate = gates.get("holdout_rollout_exact") if isinstance(gates, dict) else {}
    cur_holdout = int(holdout_gate.get("value") or 0) if isinstance(holdout_gate, dict) else 0
    best_holdout = int(best.get("holdout_depth") or 0)
    cur_score = float(gate_payload.get("score") or 0.0)
    best_score = float(best.get("gate_score") or 0.0)
    quotient_comparison = _regression_quotient_comparison(cur, best)
    holdout_witness = _holdout_witness(gate_payload)
    return {
        "schema": "ztare-candidate-regression-receipt-v1",
        "candidate_relation": "comparison_only",
        "candidate_sha": cur_sha,
        "candidate_exact_rows": cur_exact,
        "candidate_wrong_cells": cur_wrong,
        "candidate_holdout_depth": cur_holdout,
        "candidate_gate_score": cur_score,
        "best_prior_submission": best.get("submission"),
        "best_prior_sha": best.get("sha"),
        "best_prior_exact_rows": best_exact,
        "best_prior_wrong_cells": best_wrong,
        "best_prior_holdout_depth": best_holdout,
        "best_prior_gate_score": best_score,
        "exact_rows_delta": cur_exact - best_exact,
        "wrong_cells_delta": cur_wrong - best_wrong,
        "holdout_depth_delta": cur_holdout - best_holdout,
        "gate_score_delta": cur_score - best_score,
        "first_mismatch": str(cur.get("first_mismatch") or "")[:240],
        "holdout_witness": holdout_witness or {},
        "quotient_comparison": quotient_comparison,
        "_candidate_rank": (cur_exact, cur_holdout, cur_score, -cur_wrong),
        "_best_prior_rank": (best_exact, best_holdout, best_score, -best_wrong),
    }


def _first_mismatch_class(payload: dict[str, Any]) -> dict[str, Any]:
    classes = payload.get("mismatch_classes")
    if isinstance(classes, list):
        for row in classes:
            if isinstance(row, dict):
                return row
    sig = payload.get("first_mismatch_signature")
    if isinstance(sig, dict):
        return {"signature": sig}
    return {}


def _signature_shape(row: dict[str, Any]) -> dict[str, Any]:
    sig = row.get("signature") if isinstance(row.get("signature"), dict) else {}
    pairs = sig.get("pair_counts") if isinstance(sig.get("pair_counts"), list) else []
    pair_terms = []
    for pair in pairs:
        if not isinstance(pair, dict):
            continue
        pair_terms.append({
            "predicted": pair.get("predicted"),
            "real": pair.get("real"),
            "count": pair.get("count"),
        })
    return {
        "bbox": sig.get("bbox") if isinstance(sig.get("bbox"), list) else [],
        "coordinate_contract": {
            "cell_basis": "row_col",
            "bbox_basis": "row_min_col_min_row_max_col_max",
        },
        "pair_counts": pair_terms,
        "first_row": row.get("first_row"),
        "t": row.get("t"),
        "action": row.get("action"),
        "count": row.get("count"),
    }


def _regression_quotient_comparison(
    candidate_diagnostics: dict[str, Any],
    best_prior_record: dict[str, Any],
) -> dict[str, Any]:
    candidate_shape = _signature_shape(_first_mismatch_class(candidate_diagnostics))
    best_shape = _signature_shape(_first_mismatch_class(best_prior_record))
    relation = "unclassified"
    if candidate_shape.get("bbox") and candidate_shape.get("bbox") == best_shape.get("bbox"):
        if candidate_shape.get("pair_counts") == best_shape.get("pair_counts"):
            relation = "same_quotient_worse_frequency"
        else:
            relation = "same_support_changed_pairs"
    elif candidate_shape.get("bbox") and best_shape.get("bbox"):
        relation = "changed_support"
    return {
        "schema": "ztare-regression-quotient-comparison-v1",
        "relation": relation,
        "candidate_top_quotient": candidate_shape,
        "best_prior_top_quotient": best_shape,
        "use": (
            "Do not infer progress from a local delta until the next candidate "
            "explains why its changed quotient should beat the best prior under "
            "the same deterministic gate."
        ),
    }


def _record_candidate_memory(
    *,
    project_dir: Path,
    candidate_path: str | Path | None,
    gate_payload: dict[str, Any],
) -> None:
    try:
        from ztare.orchestrator.briefing_providers.surviving_candidates import (
            record_candidate_gate_payload,
        )
        record_candidate_gate_payload(
            project_dir=project_dir,
            candidate_path=candidate_path,
            gate_payload=gate_payload,
        )
    except Exception as exc:  # noqa: BLE001
        _append_gate_receipt(project_dir, {
            "site": "pre_judge_gate.py:_record_candidate_memory",
            "fallback_taken": "candidate_memory_record_failed",
            "cause": repr(exc),
        })


def _relative_ref(project_dir: Path, path: Path) -> str:
    try:
        return str(path.relative_to(project_dir))
    except Exception:
        return str(path)


def _sync_replay_residual_repair_from_gate(
    *,
    project_dir: Path,
    gate_payload: dict[str, Any],
    source_ref: str,
    candidate_path: str | Path | None = None,
    regression_receipt: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Best-effort Strategy Office sync from replay diagnostics.

    This is a reader-side routing update, not a candidate gate. It only uses
    diagnostics already emitted by the project-local harness, and it may not
    change the pass/fail result of the pre-judge gate.
    """
    if regression_receipt is not None:
        return {
            "schema": "ztare-replay-residual-repair-sync-skipped-v1",
            "source_ref": source_ref,
            "reason": "candidate_regressed_against_best_prior",
            "candidate_sha": regression_receipt.get("candidate_sha"),
            "best_prior_sha": regression_receipt.get("best_prior_sha"),
        }
    if candidate_path is not None:
        try:
            candidate_resolved = Path(candidate_path).resolve()
            current_resolved = (project_dir / "test_model.py").resolve()
        except Exception:
            candidate_resolved = Path(candidate_path)
            current_resolved = project_dir / "test_model.py"
        if candidate_resolved != current_resolved:
            return {
                "schema": "ztare-replay-residual-repair-sync-skipped-v1",
                "source_ref": source_ref,
                "reason": "unpromoted_candidate_pre_judge_diagnostic",
                "candidate_sha": _candidate_sha(candidate_path, gate_payload),
                "authority": (
                    "candidate-local counterexamples may enter candidate memory, "
                    "but canonical Strategy Office repair cards require current "
                    "project diagnostics or accepted replay receipts"
                ),
            }
    diagnostics = _visible_diagnostics(gate_payload)
    classes = diagnostics.get("mismatch_classes") if isinstance(diagnostics, dict) else None
    if not isinstance(classes, list) or not classes:
        return None
    try:
        from ztare.worldmodel.residual_repair import sync_replay_residual_repair_card

        return sync_replay_residual_repair_card(
            project_dir,
            diagnostics,
            source_ref=source_ref,
        )
    except Exception as exc:  # noqa: BLE001
        return {
            "schema": "ztare-replay-residual-repair-sync-error-v1",
            "source_ref": source_ref,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _blocked_eval(
    gate_payload: dict[str, Any],
    failed_gates: list[str],
    *,
    regression_receipt: dict[str, Any] | None = None,
    replay_residual_repair_sync: dict[str, Any] | None = None,
) -> dict[str, Any]:
    counterexample_trace = _counterexample_trace(gate_payload, failed_gates)
    weakest = (
        "PRE_JUDGE_HARD_GATE: candidate failed deterministic "
        f"gate before judge call. failed_gates={failed_gates}"
    )
    logic_gaps = [
        "Candidate failed project-local deterministic gate before judge evaluation."
    ]
    if regression_receipt is not None:
        weakest += (
            " REGRESSION_FROM_PATCH_BASE: "
            f"{regression_receipt.get('candidate_exact_rows')} exact rows vs "
            f"{regression_receipt.get('best_prior_exact_rows')} for "
            f"{regression_receipt.get('best_prior_submission')}."
        )
        logic_gaps.append(
            "Candidate regressed against the best cached deterministic near-miss; "
            "next mutation should preserve the patch base before adding mechanics."
        )
    payload = {
        "score": 0,
        "weakest_point": weakest,
        "verified_axioms": [],
        "retired_axioms_approved": [],
        "evidence_gaps": [],
        "derived_constraints": [],
        "logic_gaps": logic_gaps,
        "debate_summary": (
            "Pre-judge deterministic gate blocked evaluation to avoid spending "
            "judge tokens on a known invalid pattern."
        ),
        "adversarial_alignment": "",
        "friction_points": [],
        "probability_dag": {
            "outcome": {
                "label": "pre_judge_hard_gate_failed",
                "probability": 0.0,
            },
            "nodes": [],
            "edges": [],
        },
        "holdout_hard_gate_fired": True,
        "holdout_hard_gate_detail": (
            "Pre-judge gate harness failed before test_thesis/judge. "
            f"failed_gates={failed_gates}"
        ),
        "score_cap_reason": "pre_judge_gate_harness_failed",
        "pre_judge_gate_payload": gate_payload,
        "counterexample_trace": counterexample_trace,
    }
    if regression_receipt is not None:
        payload["candidate_regression_receipt"] = regression_receipt
    if replay_residual_repair_sync is not None:
        payload["replay_residual_repair_sync"] = replay_residual_repair_sync
    return payload


def _error_eval(exc: Exception) -> dict[str, Any]:
    return {
        "score": 0,
        "weakest_point": (
            "PRE_JUDGE_HARD_GATE_ERROR: gate harness errored before judge call: "
            f"{type(exc).__name__}: {exc}"
        ),
        "verified_axioms": [],
        "retired_axioms_approved": [],
        "evidence_gaps": [],
        "derived_constraints": [],
        "logic_gaps": ["Pre-judge gate harness error."],
        "debate_summary": (
            "Pre-judge deterministic gate failed closed to avoid spending judge tokens."
        ),
        "adversarial_alignment": "",
        "friction_points": [],
        "probability_dag": {
            "outcome": {
                "label": "pre_judge_hard_gate_error",
                "probability": 0.0,
            },
            "nodes": [],
            "edges": [],
        },
        "holdout_hard_gate_fired": True,
        "holdout_hard_gate_detail": str(exc),
        "score_cap_reason": "pre_judge_gate_harness_error",
    }


def run_pre_judge_gate_harness(
    *,
    enabled: bool,
    project_dir: str | Path,
    latest_eval_results_path: str | Path,
    python_executable: str = sys.executable,
    timeout_seconds: int = 120,
    candidate_path: str | Path | None = None,
) -> PreJudgeGateResult:
    """Run an opt-in project-local gate before paid judge evaluation.

    This is intentionally domain-agnostic. The kernel only requires a
    project-local `gate_harness.py --emit-deterministic-gates` JSON payload
    with `harness_ok` and at least one passing gate. Domain-specific gate
    semantics live in each project's harness.
    """
    project_path = Path(project_dir)
    latest_path = Path(latest_eval_results_path)
    if not enabled:
        return PreJudgeGateResult(enabled=False, ran=False, should_skip_judge=False, payload={"verdict": "disabled"})

    gate_harness_path = project_path / "gate_harness.py"
    if not gate_harness_path.exists():
        return PreJudgeGateResult(enabled=True, ran=False, should_skip_judge=False, payload={"verdict": "missing_harness"})

    try:
        if _BATCH_GATE_ENABLED:
            gate_payload = _run_batch_gate_inprocess(
                project_path,
                Path(candidate_path) if candidate_path is not None else None,
            )
            if gate_payload is None:
                # batch_gate not usable — fall through to subprocess
                stdout = run_gate_harness_subprocess(
                    project_dir=project_path,
                    python_executable=python_executable,
                    gate_harness_path=gate_harness_path,
                    candidate_path=Path(candidate_path) if candidate_path is not None else None,
                    timeout_seconds=timeout_seconds,
                )
                gate_payload = json.loads(stdout)
                if not isinstance(gate_payload, dict):
                    raise TypeError("gate_harness.py emitted non-object JSON")
                gate_payload.setdefault("engine", "subprocess")
            # engine already set by _run_batch_gate_inprocess or fallback above
        else:
            stdout = run_gate_harness_subprocess(
                project_dir=project_path,
                python_executable=python_executable,
                gate_harness_path=gate_harness_path,
                candidate_path=Path(candidate_path) if candidate_path is not None else None,
                timeout_seconds=timeout_seconds,
            )
            gate_payload = json.loads(stdout)
            if not isinstance(gate_payload, dict):
                raise TypeError("gate_harness.py emitted non-object JSON")
            gate_payload.setdefault("engine", "subprocess")
        gate_iter = _normalize_gate_iter(gate_payload)
        _record_candidate_memory(
            project_dir=project_path,
            candidate_path=candidate_path,
            gate_payload=gate_payload,
        )
        regression_receipt = _candidate_regression_receipt(
            project_dir=project_path,
            candidate_path=candidate_path,
            gate_payload=gate_payload,
        )
        if _dominance_promotion_enabled():
            comparison = _candidate_prior_comparison_receipt(
                project_dir=project_path,
                candidate_path=candidate_path,
                gate_payload=gate_payload,
            )
            champion_heldout, strict_improved = _dominance_inputs(comparison)
            promotable = _dominance_promotion_ok(
                gate_payload, gate_iter,
                champion_heldout=champion_heldout,
                strict_improved=strict_improved,
            )
        else:
            promotable = _all_gates_passed(gate_payload, gate_iter)
        if promotable:
            return PreJudgeGateResult(
                enabled=True,
                ran=True,
                should_skip_judge=False,
                message="✅ Pre-judge gate harness passed.",
                payload=gate_payload,
            )

        failed_gates = _failed_gate_labels(
            gate_iter, harness_ok=bool(gate_payload.get("harness_ok"))
        )
        replay_residual_repair_sync = _sync_replay_residual_repair_from_gate(
            project_dir=project_path,
            gate_payload=gate_payload,
            source_ref=f"{_relative_ref(project_path, latest_path)}:pre_judge_gate_payload",
            candidate_path=candidate_path,
            regression_receipt=regression_receipt,
        )
        pre_judge_eval = _blocked_eval(
            gate_payload,
            failed_gates,
            regression_receipt=regression_receipt,
            replay_residual_repair_sync=replay_residual_repair_sync,
        )
        _write_eval(latest_path, pre_judge_eval)
        # Feed the block's witness back to the leaf: without this, the
        # counterexample trace computed above dies here and the briefing's
        # tried_failed_digest renders STALE weakness receipts (observed
        # 2026-07-11: ledger frozen 2 days while every candidate was blocked
        # on a fresh post-boundary residual the leaf never saw — deterministic
        # rejection is richer feedback than a judge, but only if delivered).
        try:
            from ztare.common.harness_weakness import write_harness_weakness_receipt
            write_harness_weakness_receipt(
                project_dir=project_path,
                source_ref=f"{_relative_ref(project_path, latest_path)}:pre_judge_gate_block",
                regression_receipt=regression_receipt or {
                    "schema": "ztare-pre-judge-block-v1",
                    "failed_gates": list(failed_gates),
                    "gated_file": gate_payload.get("gated_file"),
                    "gated_sha256": gate_payload.get("gated_sha256"),
                },
                counterexample_trace=pre_judge_eval.get("counterexample_trace"),
            )
        except Exception:  # noqa: BLE001 — feedback must never block the block
            pass
        return PreJudgeGateResult(
            enabled=True,
            ran=True,
            should_skip_judge=True,
            message=(
                "🚫 Pre-judge gate harness blocked candidate before judge call: "
                f"{failed_gates}"
            ),
            score_cap_reason="pre_judge_gate_harness_failed",
            payload=gate_payload,
        )
    except Exception as exc:  # noqa: BLE001
        receipt = {
            "site": "pre_judge_gate.py:259",
            "fallback_taken": "harness_error",
            "cause": f"{type(exc).__name__}: {exc}",
            "latest_eval_results_path": str(latest_path),
        }
        _append_gate_receipt(project_path, receipt)
        pre_judge_eval = _error_eval(exc)
        _write_eval(latest_path, pre_judge_eval)
        return PreJudgeGateResult(
            enabled=True,
            ran=True,
            should_skip_judge=True,
            message=(
                "🚫 Pre-judge gate harness errored; failing closed before judge call: "
                f"{type(exc).__name__}: {exc}"
            ),
            score_cap_reason="pre_judge_gate_harness_error",
            payload={"verdict": "harness_error", "control_receipt": receipt},
        )


def detect_patch_base_regression_preflight(
    *,
    enabled: bool,
    project_dir: str | Path,
    candidate_path: str | Path,
    python_executable: str = sys.executable,
    timeout_seconds: int = 120,
) -> PatchBaseRegressionPreflight | None:
    """Pure preflight for repair loops with a persisted deterministic near-miss.

    Unlike ``run_pre_judge_gate_harness``, this function does not write
    ``latest_eval_results.json``, update candidate memory, or sync Strategy
    Office cards. It exists so the mutator retry loop can reject broad rewrites
    that lose an already-known near-closed executable carrier before consuming
    the iteration.
    """
    if not enabled:
        return None
    project_path = Path(project_dir)
    gate_harness_path = project_path / "gate_harness.py"
    if not gate_harness_path.exists():
        return None
    stdout = run_gate_harness_subprocess(
        project_dir=project_path,
        python_executable=python_executable,
        gate_harness_path=gate_harness_path,
        candidate_path=Path(candidate_path),
        timeout_seconds=timeout_seconds,
    )
    gate_payload = json.loads(stdout)
    if not isinstance(gate_payload, dict):
        raise TypeError("gate_harness.py emitted non-object JSON")
    gate_payload.setdefault("engine", "subprocess")
    regression_receipt = _candidate_regression_receipt(
        project_dir=project_path,
        candidate_path=candidate_path,
        gate_payload=gate_payload,
        require_strict_improvement=True,
    )
    gate_iter = _normalize_gate_iter(gate_payload)
    failed_gates = _failed_gate_labels(
        gate_iter, harness_ok=bool(gate_payload.get("harness_ok"))
    )
    if _dominance_promotion_enabled():
        comparison = _candidate_prior_comparison_receipt(
            project_dir=project_path,
            candidate_path=candidate_path,
            gate_payload=gate_payload,
        )
        champion_heldout, strict_improved = _dominance_inputs(comparison)
        if _dominance_promotion_ok(
            gate_payload, gate_iter,
            champion_heldout=champion_heldout,
            strict_improved=strict_improved,
        ):
            return None
    elif regression_receipt is None and _all_gates_passed(gate_payload, gate_iter):
        return None
    if regression_receipt is None:
        comparison_receipt = _candidate_prior_comparison_receipt(
            project_dir=project_path,
            candidate_path=candidate_path,
            gate_payload=gate_payload,
        )
        if comparison_receipt is not None:
            comparison_receipt.pop("_candidate_rank", None)
            comparison_receipt.pop("_best_prior_rank", None)
            comparison_receipt["candidate_relation"] = "improved_but_gate_failed"
            comparison_receipt["quotient_comparison"] = {
                **comparison_receipt.get("quotient_comparison", {}),
                "use": (
                    "The candidate improved the visible comparison surface but still "
                    "failed a deterministic gate; use the counterexample quotient to "
                    "repair the law, not to promote it."
                ),
            }
            regression_receipt = comparison_receipt
        else:
            regression_receipt = {
                "schema": "ztare-candidate-regression-receipt-v1",
                "candidate_relation": "hard_gate_failure",
                "candidate_sha": _candidate_sha(candidate_path, gate_payload),
                "candidate_exact_rows": None,
                "candidate_wrong_cells": None,
                "candidate_holdout_depth": None,
                "candidate_gate_score": float(gate_payload.get("score") or 0.0),
                "best_prior_submission": None,
                "best_prior_sha": None,
                "best_prior_exact_rows": None,
                "best_prior_wrong_cells": None,
                "best_prior_holdout_depth": None,
                "best_prior_gate_score": None,
                "exact_rows_delta": None,
                "wrong_cells_delta": None,
                "holdout_depth_delta": None,
                "gate_score_delta": None,
                "first_mismatch": "",
                "holdout_witness": _holdout_witness(gate_payload) or {},
                "quotient_comparison": {
                    "schema": "ztare-regression-quotient-comparison-v1",
                    "relation": "hard_gate_failure_without_visible_quotient",
                    "candidate_top_quotient": {},
                    "best_prior_top_quotient": {},
                    "use": (
                        "The deterministic gate failed before a comparable visible "
                        "quotient was available; repair the carrier contract or "
                        "request a typed workbench capability."
                    ),
                },
            }
    return PatchBaseRegressionPreflight(
        regression_receipt=regression_receipt,
        failed_gates=failed_gates,
        counterexample_trace=_counterexample_trace(gate_payload, failed_gates),
        gate_payload=gate_payload,
    )
