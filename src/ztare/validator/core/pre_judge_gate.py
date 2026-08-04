from __future__ import annotations

import json
import hashlib
import logging
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ztare.common.candidate_memory import admissible_candidate_memory_records
from ztare.common.observation_chart import (
    EvidenceEpochSnapshot,
    assert_project_evidence_epoch,
    capture_project_evidence_epoch,
)
from ztare.common.patch_base_identity import (
    StaleRepairFrontierError,
    load_current_repair_frontier,
)

_log = logging.getLogger(__name__)

# ZTARE_BATCH_GATE=1: use batch_gate in-process instead of subprocess harness.
# Default stays subprocess (engine-invariant: full-scan batch_gate is verdict-
# identical to gate_harness.py by design, proven in batch_gate module docstring).
_BATCH_GATE_ENABLED = os.environ.get("ZTARE_BATCH_GATE", "0") == "1"

# Gate result cache: keyed by full candidate/dependency bytes, verifier footprint,
# evidence epoch, rubric, Python version, and engine. Memory is bounded to the
# newest 200 process-local entries; a content-addressed workspace copy carries
# the same verdict across deterministic-producer and governed-worker processes.
# Engine is in the key because payload structure details differ across engines
# (though both now include grid_dsl_expressible — see FIX 1 parity proof).
_GATE_RESULT_CACHE: dict[str, str] = {}
_GATE_RESULT_CACHE_BOUND = 200
_GATE_CACHE_DIR_NAME = "gate_result_cache"
_BOUND_GATE_PAYLOAD_PATH_ENV = "ZTARE_CURRENT_PRE_JUDGE_GATE_PAYLOAD_PATH"
_BOUND_GATE_PAYLOAD_SHA_ENV = "ZTARE_CURRENT_PRE_JUDGE_GATE_PAYLOAD_SHA256"


@contextmanager
def bind_pre_judge_gate_payload(
    payload: dict[str, Any] | None,
    *,
    base_env: dict[str, str] | None = None,
):
    """Bind one gate receipt to one downstream evaluator process.

    The temporary file is only an authenticated transport edge.  It is removed
    when the evaluator returns, so callers cannot later confuse it with the
    mutable project-wide ``latest_eval_results.json`` surface.
    """

    env = dict(os.environ if base_env is None else base_env)
    if not isinstance(payload, dict) or not payload:
        yield env
        return
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    fd, raw_path = tempfile.mkstemp(prefix="ztare_pre_judge_", suffix=".json")
    path = Path(raw_path)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
        env[_BOUND_GATE_PAYLOAD_PATH_ENV] = str(path)
        env[_BOUND_GATE_PAYLOAD_SHA_ENV] = digest
        yield env
    finally:
        path.unlink(missing_ok=True)


def load_bound_pre_judge_gate_payload(
    *,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Read the receipt bound by :func:`bind_pre_judge_gate_payload`.

    Missing transport means the caller is outside a governed pre-judge edge.
    A present but altered transport is an apparatus error and fails closed.
    """

    env = os.environ if environ is None else environ
    raw_path = str(env.get(_BOUND_GATE_PAYLOAD_PATH_ENV) or "").strip()
    if not raw_path:
        return {}
    expected = str(env.get(_BOUND_GATE_PAYLOAD_SHA_ENV) or "").strip()
    if not expected:
        raise RuntimeError("bound pre-judge gate payload is missing its digest")
    raw = Path(raw_path).read_bytes()
    observed = hashlib.sha256(raw).hexdigest()
    if observed != expected:
        raise RuntimeError(
            "bound pre-judge gate payload digest mismatch: "
            f"expected={expected} observed={observed}"
        )
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise TypeError("bound pre-judge gate payload must be a JSON object")
    return payload


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
    # batch_gate.visible_total is already the checked (boundary-excluded)
    # population.  Subtracting visible_env_excluded again erased rows at this
    # producer→consumer seam.
    checked = visible_total
    wrong_rows = list(r.get("wrong_rows") or [])
    holdout_depth = int(r.get("holdout_depth") or -1)
    holdout_total = int(r.get("holdout_total") or 0)
    import hashlib as _hl
    try:
        ctext = Path(cpath).read_text()
        gated_sha = _hl.sha256(ctext.encode()).hexdigest()
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
        "description_length": r.get("description_length"),
        "description_length_unit": r.get("description_length_unit"),
        **({"load_error": load_err} if load_err else {}),
        **({"carrier": r.get("carrier")} if r.get("carrier") else {}),
    }


def _episode_evidence_fingerprint(project_dir: Path) -> str:
    """Content identity of the active episode bank and chart sidecars.

    File mtimes are properties of a storage presentation.  The gate cache owns
    evidence identity, so its key must bind the bytes that can change a verdict,
    including ``*.identity.json`` chart migrations.
    """
    return capture_project_evidence_epoch(project_dir).epoch_sha256


def _episode_mtime_fingerprint(project_dir: Path) -> str:
    """Compatibility alias; now returns content identity rather than mtimes."""
    return _episode_evidence_fingerprint(project_dir)


def _gate_cache_key(
    project_dir: Path,
    candidate_path: "Path | None",
    harness_path: Path,
) -> "str | None":
    """Content-addressed cache key string, or None if any surface is unreadable."""
    try:
        resolved_candidate = (
            Path(candidate_path) if candidate_path is not None else project_dir / "test_model.py"
        )
        candidate_source = resolved_candidate.read_text(encoding="utf-8")
        cand_sha = hashlib.sha256(candidate_source.encode("utf-8")).hexdigest()
        harness_sha = hashlib.sha256(harness_path.read_bytes()).hexdigest()
        ep_fp = _episode_evidence_fingerprint(project_dir)
        dependency_hashes: dict[str, str] = {}
        from ztare.common.patch_base_identity import (
            patch_base_fields_from_source,
            resolve_patch_base_ref,
        )

        nested_source = candidate_source
        seen: set[Path] = set()
        for _depth in range(8):
            fields = patch_base_fields_from_source(nested_source)
            if not fields:
                break
            base_path = resolve_patch_base_ref(project_dir, fields[0])
            if base_path in seen:
                raise ValueError("PATCH_BASE cache dependency cycle")
            seen.add(base_path)
            raw = base_path.read_bytes()
            dependency_hashes[str(base_path.relative_to(project_dir))] = hashlib.sha256(raw).hexdigest()
            nested_source = raw.decode("utf-8")
        from ztare.worldmodel.gates import evaluator_implementation_identity

        evaluator_identity = evaluator_implementation_identity()
        rubric_path = project_dir.parents[1] / "rubrics" / f"{project_dir.name}.json"
        rubric_sha = (
            hashlib.sha256(rubric_path.read_bytes()).hexdigest()
            if rubric_path.is_file()
            else ""
        )
        # Engine IS part of the key: the engines produce the same gate set
        # (grid_dsl_expressible now included in batch_inprocess) but payload
        # structure details may still differ; keying by engine remains correct.
        engine = "batch" if _BATCH_GATE_ENABLED else "subprocess"
        engine_path = (
            Path(__file__).parents[2] / "worldmodel" / "batch_gate.py"
            if _BATCH_GATE_ENABLED
            else harness_path
        )
        payload = {
            "schema": "ztare-gate-result-cache-key-v3",
            "candidate_sha256": cand_sha,
            "candidate_dependencies": dependency_hashes,
            "harness_sha256": harness_sha,
            "evidence_epoch_sha256": ep_fp,
            "pre_judge_gate_sha256": hashlib.sha256(
                Path(__file__).read_bytes()
            ).hexdigest(),
            "evaluator_implementation": evaluator_identity,
            "engine_implementation_sha256": hashlib.sha256(
                engine_path.read_bytes()
            ).hexdigest(),
            "rubric_sha256": rubric_sha,
            "python_version": ".".join(map(str, sys.version_info[:3])),
            "engine": engine,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    except Exception:
        return None


def _persistent_gate_cache_path(
    project_dir: Path,
    cache_key: str,
    *,
    workspace_cache_dir: "Path | None" = None,
) -> Path:
    root = (
        Path(workspace_cache_dir)
        if workspace_cache_dir is not None
        else project_dir / "workspace" / _GATE_CACHE_DIR_NAME
    )
    return root / f"{cache_key}.json"


def _load_persistent_gate_cache(
    project_dir: Path,
    cache_key: str,
    *,
    workspace_cache_dir: "Path | None" = None,
) -> str | None:
    path = _persistent_gate_cache_path(
        project_dir,
        cache_key,
        workspace_cache_dir=workspace_cache_dir,
    )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    stdout = payload.get("stdout") if isinstance(payload, dict) else None
    if (
        not isinstance(stdout, str)
        or payload.get("schema") != "ztare-gate-result-cache-entry-v1"
        or payload.get("cache_key") != cache_key
        or payload.get("stdout_sha256") != hashlib.sha256(stdout.encode("utf-8")).hexdigest()
    ):
        return None
    return stdout


def _store_persistent_gate_cache(
    project_dir: Path,
    cache_key: str,
    stdout: str,
    *,
    workspace_cache_dir: "Path | None" = None,
) -> None:
    path = _persistent_gate_cache_path(
        project_dir,
        cache_key,
        workspace_cache_dir=workspace_cache_dir,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "ztare-gate-result-cache-entry-v1",
        "cache_key": cache_key,
        "stdout_sha256": hashlib.sha256(stdout.encode("utf-8")).hexdigest(),
        "stdout": stdout,
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    temporary.replace(path)


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
    result cache keyed on candidate/dependency bytes, verifier footprint, and
    evidence-epoch identity.

    Returns raw stdout.  Raises RuntimeError on harness error.  On cache hit logs
    one line 'gate cache hit <sha8>' and skips the subprocess.
    """
    cache_key = _gate_cache_key(project_dir, candidate_path, gate_harness_path)

    if cache_key is not None and cache_key in _GATE_RESULT_CACHE:
        _log.info("gate cache hit %s", cache_key[:8])
        return _GATE_RESULT_CACHE[cache_key]
    if cache_key is not None:
        cached = _load_persistent_gate_cache(
            project_dir,
            cache_key,
            workspace_cache_dir=workspace_cache_dir,
        )
        if cached is not None:
            _GATE_RESULT_CACHE[cache_key] = cached
            _log.info("persistent gate cache hit %s", cache_key[:8])
            return cached

    executable = str(python_executable)
    if not Path(executable).is_absolute() and os.sep in executable:
        # subprocess changes cwd to the project.  A caller launched as
        # ``./venv/bin/python`` otherwise becomes a project-relative path and
        # the verifier is misclassified as unavailable.
        executable = str(Path(executable).resolve())
    gate_cmd = [
        executable,
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
            hashlib.sha256(Path(candidate_path).read_bytes()).hexdigest()
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
        _store_persistent_gate_cache(
            project_dir,
            cache_key,
            gate_res.stdout,
            workspace_cache_dir=workspace_cache_dir,
        )

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


def _deterministic_gate_contract_closed(gate_payload: dict[str, Any]) -> bool:
    gates = _normalize_gate_iter(gate_payload)
    return bool(
        gate_payload.get("harness_ok")
        and gates
        and all(_gate_passed(gate) for gate in gates)
    )


def _deterministic_gate_contract_eval(
    gate_payload: dict[str, Any],
) -> dict[str, Any]:
    """Lower a complete machine-owned score contract into the eval schema.

    A payload declaring ``deterministic_gates_only`` has already named the
    evaluator for every score-bearing dimension.  Asking a semantic judge to
    rescore those dimensions creates a second, contradictory authority edge.
    """

    gates = _normalize_gate_iter(gate_payload)
    failed = [
        str(gate.get("name") or f"gate_{index}")
        for index, gate in enumerate(gates)
        if not _gate_passed(gate)
    ]
    try:
        score = int(round(100.0 * float(gate_payload.get("score"))))
    except (TypeError, ValueError):
        score = int(round(100.0 * sum(_gate_passed(g) for g in gates) / len(gates)))
    score = max(0, min(100, score))
    closed = not failed
    status = "closed" if closed else "selected_frontier"
    weakest = (
        "DETERMINISTIC_GATE_CONTRACT_CLOSED: all registered gates passed."
        if closed
        else "DETERMINISTIC_GATE_FRONTIER_SELECTED: search-incumbent gates "
        f"authorized replacement with open verification dimensions={failed}."
    )
    return {
        "score": score,
        "raw_judge_score": score,
        "weakest_point": weakest,
        "verified_axioms": [],
        "retired_axioms_approved": [],
        "evidence_gaps": [],
        "derived_constraints": [],
        "logic_gaps": [],
        "debate_summary": (
            "Evaluation was completed by the candidate-bound deterministic "
            f"gate contract ({status}); no semantic rescore was requested."
        ),
        "adversarial_alignment": "",
        "friction_points": [],
        "probability_dag": {
            "outcome": {
                "label": f"deterministic_gate_contract_{status}",
                "probability": score / 100.0,
            },
            "nodes": [],
            "edges": [],
        },
        "holdout_hard_gate_fired": False,
        "holdout_hard_gate_detail": (
            "Consumed the candidate/evidence-bound deterministic gate contract."
        ),
        "score_contract": {
            "kind": "deterministic_gates_only",
            "source": "pre_judge_gate_payload",
            "gates": gates,
        },
        "pre_judge_gate_payload": gate_payload,
    }


def consume_pre_judge_gate_receipt(
    gate_payload: dict[str, Any],
    *,
    candidate_path: str | Path,
) -> dict[str, Any]:
    """Validate and normalize the one governed gate verdict for a candidate.

    The pre-judge result is the authority edge used by downstream evaluators.
    Consumers may render or score that verdict, but must not rerun the verifier
    with a different timeout or evidence view.  Candidate identity is checked
    here so a receipt cannot drift onto later bytes during transport.
    """

    if not isinstance(gate_payload, dict) or not gate_payload:
        raise ValueError("pre-judge gate receipt must be a non-empty object")
    path = Path(candidate_path)
    observed_sha = hashlib.sha256(path.read_bytes()).hexdigest()
    gate_payload = _bind_gate_candidate_identity(gate_payload, path)
    gated_sha = str(gate_payload.get("gated_sha256") or "").strip().lower()
    if gated_sha != observed_sha:
        raise RuntimeError(
            "pre-judge gate receipt candidate identity mismatch: "
            f"gated={gated_sha or '<missing>'} observed={observed_sha}"
        )

    gates = _normalize_gate_iter(gate_payload)
    harness_ok = bool(gate_payload.get("harness_ok"))
    failed_gates = [
        str(gate.get("name") or f"gate_{index}")
        for index, gate in enumerate(gates)
        if not _gate_passed(gate)
    ]
    decision = gate_payload.get("pre_judge_decision")
    decision = decision if isinstance(decision, dict) else {}
    authorized = decision.get("evaluator_authorized")
    if not isinstance(authorized, bool):
        # Compatibility for receipts minted before the decision field existed.
        authorized = bool(harness_ok and gates and not failed_gates)
    promotion_authorized = decision.get("candidate_promotion_authorized")
    if not isinstance(promotion_authorized, bool):
        # Older project harnesses used one gate edge for both operations.
        promotion_authorized = authorized
    return {
        "schema": "ztare-consumed-pre-judge-gate-receipt-v1",
        "candidate_sha256": observed_sha,
        "gated_sha256": gated_sha,
        "evidence_epoch": gate_payload.get("evidence_epoch"),
        "harness_ok": harness_ok,
        "gates_present": bool(gates),
        "failed_gates": failed_gates,
        "evaluator_authorized": authorized,
        "candidate_promotion_authorized": promotion_authorized,
        "authority_scope": str(
            decision.get("authority_scope") or "search_incumbent_selection"
        ),
        "task_discharge_authorized": bool(
            decision.get("task_discharge_authorized", False)
        ),
    }


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
    observed_row_dominance: dict[str, Any] | None = None,
) -> bool:
    """Tiered dominance promotion (SUBSTRATE-GENERAL, no game-specific logic).

    Promote iff: harness_ok AND every observed-tier gate passes absolutely —
    except that the row-scored observed gate may instead carry a row-bitmap
    dominance witness (candidate wrong-rows a STRICT SUBSET of the incumbent's,
    same episode bytes, same evaluator; see
    ``_observed_row_dominance_witness``) — AND every heldout-tier gate is
    non-regressing vs the champion's recorded value AND the candidate strictly
    improves something. You may not be required to solve what you have not
    observed before you are allowed to improve what you have; equally, you may
    not be required to out-perform perfection the incumbent itself no longer
    attains. With a visible-perfect incumbent the witness cannot dominate, so
    this reduces exactly to the old absolutist rule.
    """
    if not bool(gate_payload.get("harness_ok")) or not gates:
        return False
    if not strict_improved:
        return False
    row_dominates = bool(
        _observed_row_dominance_enabled()
        and isinstance(observed_row_dominance, dict)
        and observed_row_dominance.get("dominates") is True
    )
    for gate in gates:
        if _gate_tier(gate) == "observed":
            if not _gate_passed(gate):
                diag = gate.get("diagnostics")
                row_scored = isinstance(diag, dict) and "wrong_rows" in diag
                if row_scored and row_dominates:
                    continue
                return False
        else:  # heldout: non-regression, not must-pass
            try:
                value = float(gate.get("value"))
            except (TypeError, ValueError):
                # A boolean held-out certificate is sufficient when there is
                # no incumbent coordinate to compare.  Once an incumbent has
                # published a numeric coordinate, absence of that coordinate
                # cannot establish non-regression.
                gate_name = str(gate.get("name"))
                if gate_name not in champion_heldout and _gate_passed(gate):
                    continue
                return False
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
    improvement — the dual of the champion-freeze case.  Description length
    breaks behavioral ties; it does not overrule a deterministic evidence
    improvement.  Treating representation size as a hard evidence coordinate
    would prevent the system from acquiring any missing operation whose first
    expression costs source units."""
    if comparison is None:
        return {}, True
    champion_heldout = {
        "holdout_rollout_exact": float(comparison.get("best_prior_holdout_depth") or 0)
    }
    exact_delta = comparison.get("exact_rows_delta")
    wrong_delta = comparison.get("wrong_cells_delta")
    holdout_delta = comparison.get("holdout_depth_delta")
    description_delta = comparison.get("description_length_delta")
    evidence_improved = bool(
        (exact_delta is not None and exact_delta > 0)
        or (exact_delta == 0 and wrong_delta is not None and wrong_delta < 0)
        or (
            (exact_delta == 0 or exact_delta is None)
            and (wrong_delta == 0 or wrong_delta is None)
            and holdout_delta is not None and holdout_delta > 0
        )
    )
    compression_improved = bool(
        description_delta is not None
        and description_delta < 0
        and (exact_delta == 0 or exact_delta is None)
        and (wrong_delta == 0 or wrong_delta is None)
        and (holdout_delta == 0 or holdout_delta is None)
    )
    strict_improved = bool(evidence_improved or compression_improved)
    return champion_heldout, strict_improved


def _behavioral_coordinates_tied(comparison: dict[str, Any] | None) -> bool:
    """Whether candidate and incumbent identify the same observed behavior."""

    if comparison is None:
        return False
    return all(
        comparison.get(key) == 0
        for key in (
            "exact_rows_delta",
            "wrong_cells_delta",
            "holdout_depth_delta",
        )
    )


def _write_eval(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _append_gate_receipt(project_dir: Path, row: dict[str, Any]) -> bool:
    ledger = project_dir / "workspace" / "pre_judge_gate_receipts.jsonl"
    try:
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, sort_keys=True, default=str) + "\n")
    except OSError:
        # Diagnostic receipt persistence has no authority over the gate result.
        # Read-only staged scorers must preserve the verifier consequence even
        # when the authority workspace correctly rejects incidental writes.
        return False
    return True


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


def evaluation_policy_sha256() -> str:
    """Identify the policy that turns gate evidence into an adoption verdict.

    Candidate bytes and evidence bytes do not identify a verdict on their own:
    changing either the evaluator implementation or the selector creates a new
    decision object that must be allowed to fire once.
    """

    from ztare.worldmodel.gates import evaluator_implementation_identity

    return _json_sha({
        "schema": "ztare-evaluation-policy-identity-v1",
        "pre_judge_gate_sha256": _sha256_path(Path(__file__)),
        "evaluator_implementation": evaluator_implementation_identity(),
    })


def _candidate_sha(candidate_path: str | Path | None, gate_payload: dict[str, Any]) -> str:
    if candidate_path is not None:
        try:
            return hashlib.sha256(Path(candidate_path).read_bytes()).hexdigest()
        except Exception:
            pass
    return str(gate_payload.get("gated_sha256") or "")


def _bind_gate_candidate_identity(
    gate_payload: dict[str, Any],
    candidate_path: str | Path | None,
) -> dict[str, Any]:
    """Replace adapter display digests with the candidate's full content ID."""

    if candidate_path is None:
        return gate_payload
    observed = hashlib.sha256(Path(candidate_path).read_bytes()).hexdigest()
    claimed = str(gate_payload.get("gated_sha256") or "").strip().lower()
    if claimed and not observed.startswith(claimed):
        raise RuntimeError(
            "gate harness candidate identity mismatch: "
            f"gated={claimed} observed={observed}"
        )
    bound = dict(gate_payload)
    bound["gated_sha256"] = observed
    return bound


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
        "evidence_ref": diagnostics.get("evidence_ref") or "",
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
    gate_module_hash = _sha256_path(module_path)
    from ztare.worldmodel.gates import evaluator_implementation_identity

    footprint: dict[str, Any] = {
        "schema": "ztare-evaluation-cache-key-v2",
        "candidate_sha256": candidate_full_sha or str(gate_payload.get("gated_sha256") or ""),
        "gated_sha256": gate_payload.get("gated_sha256"),
        "gate_payload_sha256": _json_sha(gate_payload),
        "project_gate_harness_sha256": harness_hash,
        "pre_judge_gate_module_sha256": gate_module_hash,
        "test_thesis_module_sha256": _sha256_path(validator_dir / "test_thesis.py"),
        "autoresearch_loop_module_sha256": _sha256_path(validator_dir / "autoresearch_loop.py"),
        "evaluator_implementation": evaluator_implementation_identity(),
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


def _same_candidate_sha(left: object, right: object) -> bool:
    left_text = str(left or "").strip()
    right_text = str(right or "").strip()
    return bool(
        left_text
        and right_text
        and (
            left_text.startswith(right_text)
            or right_text.startswith(left_text)
        )
    )


def _best_prior_candidate_record(project_dir: Path, *, exclude_sha: str) -> dict[str, Any] | None:
    try:
        frontier = load_current_repair_frontier(project_dir)
    except StaleRepairFrontierError:
        frontier = None
    except FileNotFoundError:
        frontier = None
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        _append_gate_receipt(project_dir, {
            "site": "pre_judge_gate.py:_best_prior_candidate_record",
            "fallback_taken": "invalid_or_stale_repair_frontier",
            "cause": repr(exc),
        })
        frontier = None
    if frontier is not None and not _same_candidate_sha(
        frontier.get("sha256"),
        exclude_sha,
    ):
        regression = frontier.get("regression")
        regression = regression if isinstance(regression, dict) else {}
        quotient = regression.get("quotient_comparison")
        quotient = quotient if isinstance(quotient, dict) else {}
        quotient_key = (
            "best_prior_top_quotient"
            if frontier.get("role") == "best_admissible_prior"
            else "candidate_top_quotient"
        )
        top_quotient = quotient.get(quotient_key)
        top_quotient = top_quotient if isinstance(top_quotient, dict) else {}
        return {
            "source_type": "current_repair_frontier",
            "submission": frontier.get("source_ref"),
            "sha": frontier.get("sha256"),
            "visible_exact_rows": frontier.get("exact_rows", 0),
            "visible_wrong_cells": frontier.get("wrong_cells", 0),
            "holdout_depth": frontier.get("holdout_depth", 0),
            "gate_score": frontier.get("gate_score", 0.0),
            "mismatch_classes": ([{"signature": top_quotient}] if top_quotient else []),
            "repair_frontier_receipt_ref": frontier.get("receipt_ref"),
            "repair_frontier_receipt_sha256": frontier.get("receipt_sha256"),
            "evidence_epoch_sha256": frontier.get("evidence_epoch_sha256"),
        }

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
            source_types={"full_survivor", "deterministic_near_miss"},
            require_submission_source=True,
        )
        if not _same_candidate_sha(rec.get("sha"), exclude_sha)
    ]
    if not usable:
        return None
    from ztare.common.patch_base_identity import repair_frontier_order

    return max(
        usable,
        key=lambda rec: repair_frontier_order(
            exact_rows=rec.get("visible_exact_rows"),
            holdout_depth=rec.get("holdout_depth"),
            gate_score=rec.get("gate_score"),
            wrong_cells=rec.get("visible_wrong_cells"),
            description_length=rec.get("description_length"),
        ),
    )


def _candidate_seen_in_evidence_epoch(
    project_dir: Path,
    *,
    candidate_sha: str,
    evidence_epoch_sha256: str,
    evaluation_policy_sha256: str,
) -> bool:
    """Whether this carrier received a verdict under this bank and policy."""

    path = project_dir / "workspace" / "candidate_memory.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        return False
    return any(
        isinstance(record, dict)
        and _same_candidate_sha(record.get("sha"), candidate_sha)
        and str(record.get("evidence_epoch_sha256") or "")
        == evidence_epoch_sha256
        and str(record.get("evaluation_policy_sha256") or "")
        == evaluation_policy_sha256
        for record in records
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
    # Candidate selection already treats a shorter carrier as a strict
    # improvement when every behavioral coordinate ties.  Repair-frontier
    # selection must use the same order; otherwise the evaluator promotes the
    # compressed representative while the repair preflight silently restores a
    # larger behaviorally-equivalent presentation.
    _heldout_floor, comparison_strictly_improves = _dominance_inputs(comparison)
    strictly_improves = bool(
        cur_rank > best_rank
        or (cur_rank == best_rank and comparison_strictly_improves)
    )
    no_strict_improvement = require_strict_improvement and not strictly_improves
    if not regressed and not no_strict_improvement:
        return None
    comparison["candidate_relation"] = "regression" if regressed else "no_strict_improvement"
    return comparison


def _observed_row_dominance_enabled() -> bool:
    return os.environ.get("ZTARE_OBSERVED_ROW_DOMINANCE", "1") != "0"


def _observed_row_dominance_witness(
    project_dir: Path,
    candidate_path: str | Path | None,
    prior_submission: str | None,
) -> dict[str, Any] | None:
    """Row-bitmap dominance witness: candidate wrong-rows ⊂ prior wrong-rows.

    Rationale (substrate-general): observed-tier absolutism ("every visible row
    exact") was sound only under the invariant that the incumbent is itself
    visible-perfect — then "no regression + strict improvement" degenerates to
    exactness. Once evidence grows after promotion, the incumbent fails rows
    too, and absolutism blocks every strict improver forever (measured: an
    incumbent 617-wrong on the grown bank made the promotion door unpassable
    by construction — the gate-achievability failure class at the promotion
    door). Dominance strictly generalizes the old rule: with a visible-perfect
    incumbent it REQUIRES exactness; otherwise it requires no-regression plus
    strictly-fewer wrong rows.

    Identity safety: BOTH carriers are scored by the same shared evaluator
    (`build_row_bitmap`, content-addressed cache) over the same episode bytes;
    the witness is refused unless episode_hash and evaluator_sha256 match, so
    harness-local row spaces are never trusted or mixed. Fail-closed: any
    failure returns None and the caller keeps today's absolutist behavior.
    Promotion selects the SEARCH incumbent only; task discharge and terminal
    authority are untouched (determinism stays at the soundness boundary).
    """
    if candidate_path is None or not prior_submission:
        return None
    try:
        from ztare.worldmodel.evidence_consolidation import build_row_bitmap

        prior_path = Path(prior_submission)
        if not prior_path.is_absolute():
            if ".." in prior_path.parts:
                return None
            prior_path = project_dir / prior_path
        episode = project_dir / "raw" / "episodes" / "episode_001.jsonl"
        if not episode.is_file() or not prior_path.is_file():
            return None
        cand = build_row_bitmap(candidate_path, episode, project_dir=project_dir)
        prior = build_row_bitmap(prior_path, episode, project_dir=project_dir)
        if cand.get("load_error") or prior.get("load_error"):
            return None
        if cand.get("episode_hash") != prior.get("episode_hash"):
            return None
        if cand.get("evaluator_sha256") != prior.get("evaluator_sha256"):
            return None
        cand_wrong = set(int(i) for i in cand.get("wrong_rows") or [])
        prior_wrong = set(int(i) for i in prior.get("wrong_rows") or [])
        regressions = sorted(cand_wrong - prior_wrong)
        return {
            "schema": "ztare-observed-row-dominance-witness-v1",
            "episode_hash": cand.get("episode_hash"),
            "evaluator_sha256": cand.get("evaluator_sha256"),
            "candidate_wrong_row_count": len(cand_wrong),
            "prior_wrong_row_count": len(prior_wrong),
            "regressed_rows": regressions[:16],
            "regressed_row_count": len(regressions),
            "dominates": bool(
                not regressions and len(cand_wrong) < len(prior_wrong)
            ),
        }
    except Exception:  # noqa: BLE001
        # Fail-closed: no witness -> observed-tier absolutism stands.
        return None


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
    cur_description = gate_payload.get("description_length")
    cur_description = (
        int(cur_description)
        if isinstance(cur_description, int) and cur_description > 0
        else None
    )
    best_description = best.get("description_length")
    best_description = (
        int(best_description)
        if isinstance(best_description, int) and best_description > 0
        else None
    )
    if best_description is None:
        submission = str(best.get("submission") or "").strip()
        raw = Path(submission)
        if submission and not raw.is_absolute() and ".." not in raw.parts:
            try:
                from ztare.worldmodel.patch_base_carrier import (
                    composed_carrier_description_length,
                )

                best_description = composed_carrier_description_length(
                    project_dir / raw,
                    project_dir=project_dir,
                    # Migration tolerance for incumbents created before
                    # literal-prefix compaction. New carriers remain bounded
                    # by the normal execution gate; this only measures a
                    # banked representative so an equivalent compression can
                    # replace it.
                    max_depth=64,
                )
            except (OSError, TypeError, ValueError):
                best_description = None
    description_delta = (
        cur_description - best_description
        if cur_description is not None and best_description is not None
        else None
    )
    quotient_comparison = _regression_quotient_comparison(cur, best)
    holdout_witness = _holdout_witness(gate_payload)
    row_dominance: dict[str, Any] | None = None
    if _observed_row_dominance_enabled():
        gates_by_name = _gates_dict(gate_payload)
        visible_gate = gates_by_name.get("visible_replay_exact")
        visible_failed = isinstance(visible_gate, dict) and not _gate_passed(
            visible_gate
        )
        if visible_failed:
            # Computed only when absolutism would block: with a visible-perfect
            # incumbent the witness cannot dominate, so nothing changes there.
            row_dominance = _observed_row_dominance_witness(
                project_dir,
                candidate_path,
                str(best.get("submission") or "") or None,
            )
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
        "candidate_description_length": cur_description,
        "best_prior_description_length": best_description,
        "description_length_delta": description_delta,
        "description_length_unit": gate_payload.get("description_length_unit"),
        "first_mismatch": str(cur.get("first_mismatch") or "")[:240],
        "holdout_witness": holdout_witness or {},
        "quotient_comparison": quotient_comparison,
        "observed_row_dominance": row_dominance or {},
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
    artifact_role: str = "behavior_carrier",
) -> None:
    try:
        from ztare.orchestrator.briefing_providers.surviving_candidates import (
            record_candidate_gate_payload,
        )
        record_candidate_gate_payload(
            project_dir=project_dir,
            candidate_path=candidate_path,
            gate_payload=gate_payload,
            artifact_role=artifact_role,
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
        diagnostics = _visible_diagnostics(gate_payload)
        try:
            from ztare.worldmodel.residual_repair import (
                reject_cards_dominated_by_candidate_memory,
            )

            rejected = reject_cards_dominated_by_candidate_memory(
                project_dir,
                diagnostics,
                source_ref=source_ref,
            )
        except Exception:  # noqa: BLE001 — routing cleanup cannot alter the gate
            rejected = []
        return {
            "schema": "ztare-replay-residual-repair-sync-skipped-v1",
            "source_ref": source_ref,
            "reason": "candidate_regressed_against_best_prior",
            "candidate_sha": regression_receipt.get("candidate_sha"),
            "best_prior_sha": regression_receipt.get("best_prior_sha"),
            "rejected_candidate_dominated_cards": len(rejected),
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
    expected_evidence_epoch: EvidenceEpochSnapshot | None = None,
    run_role: str | None = None,
    withheld_refs: tuple[str, ...] = (),
    exposed_refs: tuple[str, ...] = (),
    artifact_role: str = "behavior_carrier",
) -> PreJudgeGateResult:
    """Run an opt-in project-local gate before paid judge evaluation.

    This is intentionally domain-agnostic. The kernel only requires a
    project-local `gate_harness.py --emit-deterministic-gates` JSON payload
    with `harness_ok` and at least one passing gate. Domain-specific gate
    semantics live in each project's harness.
    """
    project_path = Path(project_dir)
    latest_path = Path(latest_eval_results_path)
    artifact_role = str(artifact_role or "behavior_carrier").strip()
    if artifact_role not in {"behavior_carrier", "task_hypothesis"}:
        raise ValueError(f"unsupported pre-judge artifact role: {artifact_role!r}")
    if not enabled:
        return PreJudgeGateResult(enabled=False, ran=False, should_skip_judge=False, payload={"verdict": "disabled"})

    gate_harness_path = project_path / "gate_harness.py"
    if not gate_harness_path.exists():
        return PreJudgeGateResult(enabled=True, ran=False, should_skip_judge=False, payload={"verdict": "missing_harness"})

    try:
        evidence_epoch = (
            assert_project_evidence_epoch(project_path, expected_evidence_epoch)
            if expected_evidence_epoch is not None
            else capture_project_evidence_epoch(project_path)
        )
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
        gate_payload = _bind_gate_candidate_identity(gate_payload, candidate_path)
        gate_payload["evidence_epoch"] = evidence_epoch.to_dict()
        evaluation_policy_id = evaluation_policy_sha256()
        gate_payload["evaluation_policy_sha256"] = evaluation_policy_id
        if run_role:
            gate_payload["run_role"] = str(run_role)
        if withheld_refs:
            gate_payload["withheld_refs"] = list(withheld_refs)
        if exposed_refs:
            gate_payload["exposed_refs"] = list(exposed_refs)
        gate_iter = _normalize_gate_iter(gate_payload)
        # Compare against the incumbent set before publishing this observation.
        # Publishing first makes a candidate with an adapter-supplied/unknown
        # digest visible as its own prior, turning a temporal identity seam into
        # a fabricated "no improvement" verdict.
        candidate_sha = _candidate_sha(candidate_path, gate_payload)
        already_evaluated = _candidate_seen_in_evidence_epoch(
            project_path,
            candidate_sha=candidate_sha,
            evidence_epoch_sha256=evidence_epoch.epoch_sha256,
            evaluation_policy_sha256=evaluation_policy_id,
        )
        regression_receipt = _candidate_regression_receipt(
            project_dir=project_path,
            candidate_path=candidate_path,
            gate_payload=gate_payload,
        )
        comparison: dict[str, Any] | None = None
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
                observed_row_dominance=(
                    comparison.get("observed_row_dominance")
                    if isinstance(comparison, dict)
                    else None
                ),
            )
        else:
            promotable = _all_gates_passed(gate_payload, gate_iter)
        role_admissible = bool(promotable)
        if artifact_role == "task_hypothesis" and not role_admissible:
            if _dominance_promotion_enabled():
                role_admissible = bool(
                    regression_receipt is None
                    and _behavioral_coordinates_tied(comparison)
                    and _dominance_promotion_ok(
                        gate_payload,
                        gate_iter,
                        champion_heldout=champion_heldout,
                        strict_improved=True,
                    )
                )
            else:
                role_admissible = bool(
                    regression_receipt is None
                    and _behavioral_coordinates_tied(comparison)
                    and _all_gates_passed(gate_payload, gate_iter)
                )
        _record_candidate_memory(
            project_dir=project_path,
            candidate_path=candidate_path,
            gate_payload=gate_payload,
            artifact_role=artifact_role,
        )
        promotion_authorized = gate_payload.get("candidate_promotion_authorized")
        if not isinstance(promotion_authorized, bool):
            promotion_authorized = bool(promotable)
        evidence_delta = bool(
            comparison
            and (
                (comparison.get("exact_rows_delta") or 0) > 0
                or (comparison.get("wrong_cells_delta") or 0) < 0
                or (comparison.get("holdout_depth_delta") or 0) > 0
            )
        )
        complexity_regressed = bool(
            comparison
            and isinstance(comparison.get("description_length_delta"), int)
            and comparison["description_length_delta"] > 0
        )
        model_selection_relation = (
            "same_carrier_same_evidence"
            if already_evaluated
            else "behaviorally_equivalent_role_companion"
            if artifact_role == "task_hypothesis" and role_admissible and not promotable
            else
            "evidence_improvement_with_complexity_cost"
            if promotable and evidence_delta and complexity_regressed
            else "dominates_prior"
            if promotable
            else "no_strict_dominance"
            if comparison is not None
            else "uncompared_first_candidate"
        )
        gate_payload["pre_judge_decision"] = {
            "schema": "ztare-pre-judge-decision-v1",
            "evaluator_authorized": role_admissible,
            "candidate_promotion_authorized": bool(
                artifact_role == "behavior_carrier"
                and promotable
                and promotion_authorized
                and not already_evaluated
            ),
            "authority_scope": (
                "task_hypothesis_admissibility"
                if artifact_role == "task_hypothesis"
                else "search_incumbent_selection"
            ),
            "artifact_role": artifact_role,
            "task_discharge_authorized": bool(
                gate_payload.get("task_discharge_authorized", False)
            ),
            "evaluation_authority": (
                "deterministic_gate"
                if gate_payload.get("score_contract") == "deterministic_gates_only"
                else "semantic_evaluator"
            ),
            "gate_contract_closed": _deterministic_gate_contract_closed(
                gate_payload
            ),
            "model_selection_relation": model_selection_relation,
            "model_selection_deltas": ({
                key: comparison.get(key)
                for key in (
                    "exact_rows_delta",
                    "wrong_cells_delta",
                    "holdout_depth_delta",
                    "description_length_delta",
                )
            } if comparison is not None else {}),
            "candidate_sha": candidate_sha,
            "evidence_epoch_sha256": evidence_epoch.epoch_sha256,
        }
        if role_admissible:
            if gate_payload.get("score_contract") == "deterministic_gates_only":
                _write_eval(
                    latest_path,
                    _deterministic_gate_contract_eval(gate_payload),
                )
                return PreJudgeGateResult(
                    enabled=True,
                    ran=True,
                    should_skip_judge=True,
                    message=(
                        "✅ Deterministic pre-judge score contract completed "
                        "candidate evaluation."
                    ),
                    payload=gate_payload,
                )
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
        if not failed_gates:
            failed_gates = ["candidate_model_selection"]
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
        # A gate comparison is already the authoritative producer for the
        # epoch-scoped repair-frontier role.  Persist its consequence here so
        # play control and retry control consume one identity instead of
        # independently ranking candidate properties.  The shared writer also
        # serves the retry preflight path.
        if isinstance(regression_receipt, Mapping):
            try:
                from ztare.common.patch_base_identity import (
                    persist_repair_frontier_observation,
                )

                persist_repair_frontier_observation(
                    project_path,
                    regression_receipt=regression_receipt,
                    counterexample_trace=pre_judge_eval.get(
                        "counterexample_trace"
                    ),
                    evidence_epoch=gate_payload.get("evidence_epoch") or {},
                    evaluation_policy_sha256=str(
                        gate_payload.get("evaluation_policy_sha256") or ""
                    ),
                )
            except Exception:  # noqa: BLE001
                # A malformed comparison cannot move the role.  The gate block
                # still stands and its weakness receipt remains available.
                pass
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
    workspace_cache_dir: str | Path | None = None,
    require_strict_improvement: bool = True,
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
    evidence_epoch = capture_project_evidence_epoch(project_path)
    stdout = run_gate_harness_subprocess(
        project_dir=project_path,
        python_executable=python_executable,
        gate_harness_path=gate_harness_path,
        candidate_path=Path(candidate_path),
        timeout_seconds=timeout_seconds,
        workspace_cache_dir=(
            Path(workspace_cache_dir) if workspace_cache_dir is not None else None
        ),
    )
    gate_payload = json.loads(stdout)
    if not isinstance(gate_payload, dict):
        raise TypeError("gate_harness.py emitted non-object JSON")
    gate_payload = _bind_gate_candidate_identity(gate_payload, candidate_path)
    assert_project_evidence_epoch(project_path, evidence_epoch)
    gate_payload["evidence_epoch"] = evidence_epoch.to_dict()
    gate_payload["evaluation_policy_sha256"] = evaluation_policy_sha256()
    gate_payload.setdefault("engine", "subprocess")
    regression_receipt = _candidate_regression_receipt(
        project_dir=project_path,
        candidate_path=candidate_path,
        gate_payload=gate_payload,
        require_strict_improvement=require_strict_improvement,
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
        if require_strict_improvement:
            if _dominance_promotion_ok(
                gate_payload, gate_iter,
                champion_heldout=champion_heldout,
                strict_improved=strict_improved,
            ):
                return None
        elif (
            regression_receipt is None
            and _behavioral_coordinates_tied(comparison)
            and _dominance_promotion_ok(
                gate_payload,
                gate_iter,
                champion_heldout=champion_heldout,
                # Reuse the same tier/non-regression checks without granting
                # behavior-carrier promotion authority to this companion.
                strict_improved=True,
            )
        ):
            return None
    elif (
        regression_receipt is None
        and _all_gates_passed(gate_payload, gate_iter)
        and (
            require_strict_improvement
            or _behavioral_coordinates_tied(
                _candidate_prior_comparison_receipt(
                    project_dir=project_path,
                    candidate_path=candidate_path,
                    gate_payload=gate_payload,
                )
            )
        )
    ):
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
                    "The candidate improved the visible comparison surface but "
                    "still failed a deterministic gate; use the counterexample "
                    "quotient to repair the law, not to promote it."
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
    if not failed_gates:
        failed_gates = ["candidate_model_selection"]
    return PatchBaseRegressionPreflight(
        regression_receipt=regression_receipt,
        failed_gates=failed_gates,
        counterexample_trace=_counterexample_trace(gate_payload, failed_gates),
        gate_payload=gate_payload,
    )
