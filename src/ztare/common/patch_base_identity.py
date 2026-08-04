from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


CURRENT_REPAIR_FRONTIER_REF = "workspace/latest_patch_base_regression.json"
TASK_HYPOTHESIS_COMPANION_SCHEMA = "ztare-task-hypothesis-companion-v1"


class StaleRepairFrontierError(ValueError):
    """The receipt is valid for an earlier evidence epoch and has expired."""


def repair_frontier_order(
    *,
    exact_rows: Any,
    holdout_depth: Any,
    gate_score: Any,
    wrong_cells: Any,
    description_length: Any = None,
) -> tuple[int, int, float, int, int]:
    """Return the evidence-first order for repair-carrier representatives.

    Description length selects a representative only when every behavioral
    coordinate ties. Missing description evidence loses to a measured value
    but never outranks replay, holdout, score, or residual evidence.
    """

    try:
        description = int(description_length)
    except (TypeError, ValueError):
        description = 0
    description_coordinate = -description if description > 0 else -(2**63)
    return (
        int(exact_rows or 0),
        int(holdout_depth or 0),
        float(gate_score or 0.0),
        -int(wrong_cells or 0),
        description_coordinate,
    )


def _repair_frontier_score(
    regression: Mapping[str, Any],
) -> tuple[int, int, float, int, int]:
    identity = repair_frontier_fields(regression)
    prefix = "best_prior" if identity["role"] == "best_admissible_prior" else "candidate"
    return repair_frontier_order(
        exact_rows=regression.get(f"{prefix}_exact_rows"),
        holdout_depth=regression.get(f"{prefix}_holdout_depth"),
        gate_score=regression.get(f"{prefix}_gate_score"),
        wrong_cells=regression.get(f"{prefix}_wrong_cells"),
        description_length=regression.get(f"{prefix}_description_length"),
    )


def _repair_receipt_information_score(regression: Mapping[str, Any]) -> int:
    comparison = regression.get("quotient_comparison")
    if not isinstance(comparison, Mapping):
        return 0
    score = 0
    for name in ("candidate_top_quotient", "best_prior_top_quotient"):
        quotient = comparison.get(name)
        if not isinstance(quotient, Mapping):
            continue
        score += sum(
            quotient.get(field) is not None
            for field in ("first_row", "t", "action", "bbox", "pair_counts")
        )
    score += sum(
        bool(regression.get(field))
        for field in ("candidate_submission", "candidate_sha", "best_prior_submission", "best_prior_sha")
    )
    return score


def persist_repair_frontier_if_dominant(
    project_dir: str | Path,
    payload: Mapping[str, Any],
    *,
    receipt_ref: str = CURRENT_REPAIR_FRONTIER_REF,
) -> bool:
    """Persist one monotone, epoch-scoped repair-frontier receipt.

    Candidate attempts remain plural observations.  This singleton role moves
    only when its carrier score improves, the evidence epoch changes, or the
    same carrier gains a strictly richer comparison witness.  A score-equivalent
    retry therefore cannot erase the counterexample pair the next consumer needs.
    """
    regression = payload.get("candidate_regression_receipt")
    if not isinstance(regression, Mapping):
        raise TypeError("repair-frontier payload lacks candidate_regression_receipt")
    project = Path(project_dir)
    path = project / receipt_ref
    replace = not path.is_file()
    prior_payload: Mapping[str, Any] = {}
    if not replace:
        try:
            loaded = json.loads(path.read_text(encoding="utf-8"))
            prior_payload = loaded if isinstance(loaded, Mapping) else {}
        except (OSError, json.JSONDecodeError):
            replace = True
    prior_regression = prior_payload.get("candidate_regression_receipt")
    if not replace and not isinstance(prior_regression, Mapping):
        replace = True
    if not replace and isinstance(prior_regression, Mapping):
        try:
            _resolve_repair_frontier_identity(
                project,
                repair_frontier_fields(prior_regression),
            )
        except (OSError, TypeError, ValueError):
            replace = True
    if not replace:
        new_epoch = payload.get("evidence_epoch")
        old_epoch = prior_payload.get("evidence_epoch")
        new_epoch_sha = str(new_epoch.get("epoch_sha256") or "") if isinstance(new_epoch, Mapping) else ""
        old_epoch_sha = str(old_epoch.get("epoch_sha256") or "") if isinstance(old_epoch, Mapping) else ""
        if new_epoch_sha != old_epoch_sha:
            replace = True
    if not replace:
        if str(payload.get("evaluation_policy_sha256") or "") != str(
            prior_payload.get("evaluation_policy_sha256") or ""
        ):
            replace = True
    if not replace and isinstance(prior_regression, Mapping):
        new_score = _repair_frontier_score(regression)
        old_score = _repair_frontier_score(prior_regression)
        if new_score > old_score:
            replace = True
        elif new_score == old_score:
            new_identity = repair_frontier_fields(regression)
            new_candidate_sha = str(regression.get("candidate_sha") or "")
            candidate_is_frontier = bool(
                new_candidate_sha
                and (
                    new_candidate_sha.startswith(new_identity["sha256"])
                    or new_identity["sha256"].startswith(new_candidate_sha)
                )
            )
            replace = bool(
                candidate_is_frontier
                and _repair_receipt_information_score(regression)
                > _repair_receipt_information_score(prior_regression)
            )
    if not replace:
        return False
    try:
        _resolve_repair_frontier_identity(
            project,
            repair_frontier_fields(regression),
        )
    except (OSError, TypeError, ValueError):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(dict(payload), sort_keys=True, indent=2, default=str),
        encoding="utf-8",
    )
    return True


def persist_repair_frontier_observation(
    project_dir: str | Path,
    *,
    regression_receipt: Mapping[str, Any],
    counterexample_trace: Mapping[str, Any] | None,
    evidence_epoch: Mapping[str, Any],
    evaluation_policy_sha256: str = "",
) -> bool:
    """Single writer door from one gate observation to the frontier role.

    Gate evaluation and retry preflight are two producers of the same object:
    an epoch-bound comparison between a candidate and its admissible prior.
    Centralizing the envelope prevents one path from updating the role while
    the other leaves downstream control to reconstruct it from candidate
    properties.
    """

    return persist_repair_frontier_if_dominant(
        project_dir,
        {
            "schema": "ztare-latest-patch-base-regression-v1",
            "evidence_epoch": dict(evidence_epoch),
            "candidate_regression_receipt": dict(regression_receipt),
            "counterexample_trace": dict(counterexample_trace or {}),
            **(
                {"evaluation_policy_sha256": str(evaluation_policy_sha256)}
                if evaluation_policy_sha256
                else {}
            ),
        },
    )


def repair_frontier_fields(regression: Mapping[str, Any]) -> dict[str, str]:
    """Select the carrier identity that survives a comparison receipt."""

    relation = str(regression.get("candidate_relation") or "")
    best_ref = str(regression.get("best_prior_submission") or "").strip()
    try:
        candidate_exact = int(regression.get("candidate_exact_rows"))
        best_exact = int(regression.get("best_prior_exact_rows"))
    except (TypeError, ValueError):
        candidate_exact = best_exact = 0
    # Only a strict, gate-observed improvement transfers the repair-frontier
    # role to the candidate.  Every other comparison relation—including an
    # evidence/complexity Pareto branch—retains the prior identity.  A new
    # relation therefore fails toward the already-admissible carrier instead
    # of accidentally selecting an ephemeral probe file.
    use_best = bool(best_ref) and (
        relation != "improved_but_gate_failed" or candidate_exact < best_exact
    )
    return {
        "source_ref": (
            best_ref
            if use_best
            else str(regression.get("candidate_submission") or "").strip()
        ),
        "sha256": str(
            regression.get("best_prior_sha" if use_best else "candidate_sha") or ""
        ).strip(),
        "role": "best_admissible_prior" if use_best else "evaluated_candidate",
    }


def resolve_repair_frontier(
    project_dir: str | Path,
    regression: Mapping[str, Any],
) -> dict[str, Any]:
    """Resolve and digest-check the carrier observed by one repair receipt.

    Candidate-local scorer receipts may carry only the digest because their
    temporary source file is intentionally destroyed.  When that digest is the
    epoch-current repair carrier, join it back to the durable carrier identity
    through the current-frontier receipt instead of asking each consumer to
    reconstruct the role independently.
    """

    identity = repair_frontier_fields(regression)
    if not identity["source_ref"] and identity["sha256"]:
        current = load_current_repair_frontier(project_dir)
        declared = identity["sha256"].lower()
        current_sha = str(current["sha256"]).lower()
        if not current_sha.startswith(declared):
            raise ValueError(
                "candidate-local receipt digest does not identify the current "
                "repair frontier"
            )
        return {
            **identity,
            "source_ref": current["source_ref"],
            "sha256": current["sha256"],
            "path": current["path"],
            "identity_join_ref": current["receipt_ref"],
            "identity_join_sha256": current["receipt_sha256"],
        }
    return _resolve_repair_frontier_identity(project_dir, identity)


def _resolve_repair_frontier_identity(
    project_dir: str | Path,
    identity: Mapping[str, Any],
) -> dict[str, Any]:
    path = resolve_patch_base_ref(project_dir, identity["source_ref"])
    digest = verify_patch_base_digest(
        path,
        identity["sha256"],
        allow_legacy_prefix=True,
    )
    return {**identity, "sha256": digest, "path": path}


def load_current_repair_frontier(
    project_dir: str | Path,
    *,
    receipt_ref: str = CURRENT_REPAIR_FRONTIER_REF,
) -> dict[str, Any]:
    """Load the epoch-current carrier occupying the repair-frontier role.

    Candidate memory remains plural evidence.  This receipt binds one carrier
    to the narrower lifecycle role "continue repair from here"; consumers must
    not independently reconstruct that role by ranking historical candidates.
    """

    project = Path(project_dir)
    receipt_path = project / receipt_ref
    payload = json.loads(receipt_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("repair-frontier receipt must be a JSON object")
    regression = payload.get("candidate_regression_receipt")
    if not isinstance(regression, dict):
        raise TypeError("repair-frontier receipt lacks candidate_regression_receipt")

    epoch = payload.get("evidence_epoch")
    epoch_sha = str(epoch.get("epoch_sha256") or "") if isinstance(epoch, dict) else ""
    if not epoch_sha:
        raise ValueError("repair-frontier receipt lacks evidence epoch identity")
    from ztare.common.observation_chart import capture_project_evidence_epoch

    current_epoch_sha = capture_project_evidence_epoch(project).epoch_sha256
    if epoch_sha != current_epoch_sha:
        raise StaleRepairFrontierError(
            "repair-frontier receipt belongs to a different evidence epoch: "
            f"receipt={epoch_sha} current={current_epoch_sha}"
        )
    from ztare.validator.core.pre_judge_gate import evaluation_policy_sha256

    receipt_policy_sha = str(payload.get("evaluation_policy_sha256") or "")
    current_policy_sha = evaluation_policy_sha256()
    if receipt_policy_sha != current_policy_sha:
        raise StaleRepairFrontierError(
            "repair-frontier receipt belongs to a different evaluation policy: "
            f"receipt={receipt_policy_sha or '<missing>'} current={current_policy_sha}"
        )

    resolved = _resolve_repair_frontier_identity(
        project,
        repair_frontier_fields(regression),
    )
    prefix = (
        "best_prior" if resolved["role"] == "best_admissible_prior" else "candidate"
    )
    return {
        **resolved,
        "receipt_ref": receipt_ref,
        "receipt_sha256": hashlib.sha256(receipt_path.read_bytes()).hexdigest(),
        "evidence_epoch_sha256": epoch_sha,
        "evaluation_policy_sha256": receipt_policy_sha,
        "regression": regression,
        "exact_rows": int(regression.get(f"{prefix}_exact_rows") or 0),
        "wrong_cells": int(regression.get(f"{prefix}_wrong_cells") or 0),
        "holdout_depth": int(regression.get(f"{prefix}_holdout_depth") or 0),
        "gate_score": float(regression.get(f"{prefix}_gate_score") or 0.0),
    }


def resolve_patch_base_ref(project_dir: str | Path, ref: object) -> Path:
    if not isinstance(ref, str) or not ref.strip():
        raise ValueError("PATCH_BASE requires non-empty source_ref/path.")
    raw = Path(ref)
    if raw.is_absolute() or ".." in raw.parts:
        raise ValueError("PATCH_BASE source_ref must be a project-relative path.")
    if len(raw.parts) < 3 or raw.parts[:2] != ("workspace", "submissions"):
        raise ValueError(
            "PATCH_BASE source_ref must point to an immutable "
            "workspace/submissions artifact."
        )
    project = Path(project_dir)
    path = (project / raw).resolve()
    root = project.resolve()
    if root != path and root not in path.parents:
        raise ValueError("PATCH_BASE source_ref escapes project_dir.")
    if not path.is_file():
        raise ValueError(f"PATCH_BASE source_ref not found: {ref}")
    return path


def verify_patch_base_digest(
    path: Path,
    expected: object,
    *,
    allow_legacy_prefix: bool = False,
) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if expected is None or not str(expected).strip():
        raise ValueError("PATCH_BASE requires full sha256 for referenced artifact.")
    declared = str(expected).strip().lower()
    if _is_full_digest(declared):
        if digest != declared:
            raise ValueError("PATCH_BASE sha256 does not match referenced artifact.")
        return digest
    if allow_legacy_prefix and _is_legacy_prefix(declared) and digest.startswith(declared):
        return digest
    raise ValueError("PATCH_BASE sha256 must be the full 64-hex digest.")


def patch_base_fields_from_source(source: str) -> tuple[str, object] | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        names = [target.id for target in node.targets if isinstance(target, ast.Name)]
        if "PATCH_BASE" in names and isinstance(node.value, ast.Dict):
            try:
                spec = ast.literal_eval(node.value)
            except Exception:  # noqa: BLE001
                return None
            if isinstance(spec, dict):
                return _fields_from_mapping(spec)
        if "PATCH_BASE_REF" in names or "PATCH_BASE_PATH" in names:
            try:
                ref = ast.literal_eval(node.value)
            except Exception:  # noqa: BLE001
                return None
            sha: object = None
            for sibling in tree.body:
                if not isinstance(sibling, ast.Assign):
                    continue
                sibling_names = [
                    target.id for target in sibling.targets if isinstance(target, ast.Name)
                ]
                if not (
                    "PATCH_BASE_SHA256" in sibling_names
                    or "PATCH_BASE_SHA" in sibling_names
                    or "PATCH_BASE_SHA256_PREFIX" in sibling_names
                ):
                    continue
                try:
                    sha = ast.literal_eval(sibling.value)
                except Exception:  # noqa: BLE001
                    sha = None
                break
            return (str(ref), sha) if ref else None
    return None


def task_hypothesis_companion_provenance_from_source(
    source: str,
) -> dict[str, Any] | None:
    """Read the typed role marker from a kernel-built task companion."""

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        names = [target.id for target in node.targets if isinstance(target, ast.Name)]
        if "TASK_HYPOTHESIS_PROVENANCE" not in names:
            continue
        try:
            value = ast.literal_eval(node.value)
        except Exception:  # noqa: BLE001
            return None
        if (
            isinstance(value, dict)
            and value.get("schema") == TASK_HYPOTHESIS_COMPANION_SCHEMA
        ):
            return value
        return None
    return None


def patch_base_fields_from_namespace(namespace: dict[str, Any]) -> tuple[str, object] | None:
    spec = namespace.get("PATCH_BASE")
    if isinstance(spec, dict):
        return _fields_from_mapping(spec)
    ref = namespace.get("PATCH_BASE_REF") or namespace.get("PATCH_BASE_PATH")
    if ref:
        return str(ref), (
            namespace.get("PATCH_BASE_SHA256")
            or namespace.get("PATCH_BASE_SHA256_PREFIX")
            or namespace.get("PATCH_BASE_SHA")
        )
    return None


def _fields_from_mapping(spec: dict[str, Any]) -> tuple[str, object] | None:
    ref = (
        spec.get("source_ref")
        or spec.get("path")
        or spec.get("submission")
        or spec.get("artifact")
    )
    sha = (
        spec.get("sha256")
        or spec.get("sha256_prefix")
        or spec.get("sha")
        or spec.get("source_sha")
    )
    return (str(ref), sha) if ref else None


def _is_full_digest(value: str) -> bool:
    return len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _is_legacy_prefix(value: str) -> bool:
    return 12 <= len(value) < 64 and all(ch in "0123456789abcdef" for ch in value)
