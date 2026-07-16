from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ztare.common.patch_base_identity import (
    patch_base_fields_from_source,
    resolve_patch_base_ref,
    verify_patch_base_digest,
)
from ztare.common.worldmodel_carrier_purity import (
    carrier_contract_error,
    project_dynamics_assumption,
)


def load_candidate_memory(project: str | Path) -> list[dict[str, Any]]:
    path = Path(project) / "workspace" / "candidate_memory.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    records = payload.get("records") if isinstance(payload, dict) else None
    if not isinstance(records, list):
        return []
    return [rec for rec in records if isinstance(rec, dict)]


def admissible_candidate_memory_records(
    project: str | Path,
    records: list[dict[str, Any]] | None = None,
    *,
    source_types: set[str] | None = None,
    require_submission_source: bool = False,
    dynamics_assumption: str | None = None,
) -> list[dict[str, Any]]:
    """Candidate-memory records selectable by current worldmodel contracts.

    Historical candidate memory is an audit trail. Reader surfaces may only use
    a row as an active prior when the stored carrier source still satisfies the
    current transition-function contract.
    """
    root = Path(project)
    effective_dynamics = dynamics_assumption or project_dynamics_assumption(root)
    rows = records if records is not None else load_candidate_memory(root)
    allowed = source_types or {"full_survivor", "deterministic_near_miss"}
    invalidated = _selection_invalidated_shas(root)
    eligible: list[dict[str, Any]] = []
    for rec in rows:
        if rec.get("source_type") not in allowed:
            continue
        sha = str(rec.get("sha") or rec.get("candidate_sha") or "").strip()
        if sha and any(
            sha.startswith(prefix) or prefix.startswith(sha)
            for prefix in invalidated
        ):
            continue
        eligible.append(rec)

    # Collapse the append-only history before parsing carrier chains. Contract
    # validity belongs to the selected carrier bytes; validating every
    # superseded observation made current-epoch selection scale with the full
    # audit trail.
    active = _active_evidence_view(root, eligible)
    out: list[dict[str, Any]] = []
    contract_errors: dict[str, str | None] = {}
    for rec in active:
        if (
            require_submission_source
            and candidate_memory_submission_path(root, rec) is None
        ):
            continue
        sha = str(rec.get("sha") or rec.get("candidate_sha") or "").strip()
        source = candidate_memory_source(root, rec)
        cache_key = sha or hashlib.sha256(source.encode("utf-8")).hexdigest()
        if source and cache_key not in contract_errors:
            contract_errors[cache_key] = _carrier_chain_contract_error(
                root,
                source,
                dynamics_assumption=effective_dynamics,
            )
        if source and contract_errors.get(cache_key):
            continue
        out.append(rec)
    return out


def _selection_invalidated_shas(project: Path) -> set[str]:
    """Candidate identities explicitly barred from active selection.

    Candidate memory remains append-only evidence.  A later provenance audit
    may discover that an otherwise passing carrier was conductor-authored,
    contaminated, or tied to an invalid evidence contract.  The tombstone
    ledger removes selection authority without erasing the historical gate.
    """
    path = project / "workspace" / "candidate_invalidations.jsonl"
    latest: dict[str, bool] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return set()
    for line in lines:
        try:
            row = json.loads(line)
        except (TypeError, ValueError):
            continue
        if not isinstance(row, dict):
            continue
        sha = str(row.get("candidate_sha256") or row.get("candidate_sha") or "").strip()
        if not sha:
            continue
        latest[sha] = bool(row.get("selection_forbidden", True))
    return {sha for sha, forbidden in latest.items() if forbidden}


def _record_evidence_epoch(rec: dict[str, Any]) -> str:
    nested = rec.get("carrier_evidence_identity")
    if isinstance(nested, dict):
        value = nested.get("evidence_epoch_sha256")
    else:
        value = rec.get("evidence_epoch_sha256")
    digest = str(value or "").strip().lower()
    return digest if len(digest) == 64 and all(ch in "0123456789abcdef" for ch in digest) else ""


def _normalized_carrier_sha(project: Path, rec: dict[str, Any]) -> str:
    """Recover a full carrier identity from its immutable bytes.

    Old producer rows stored a 12-hex display prefix.  The immutable submission
    lets the reader migrate that presentation without treating the prefix as
    equality.  Rows without either a full digest or recoverable bytes remain
    historical only.
    """

    declared = str(rec.get("sha") or rec.get("candidate_sha") or "").strip().lower()
    if len(declared) == 64 and all(ch in "0123456789abcdef" for ch in declared):
        return declared
    path = candidate_memory_submission_path(project, rec)
    if path is None:
        return ""
    try:
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""
    if (
        12 <= len(declared) < 64
        and all(ch in "0123456789abcdef" for ch in declared)
        and observed.startswith(declared)
    ):
        return observed
    return ""


def _active_evidence_view(
    project: Path,
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Return one active evidence epoch per carrier identity.

    Candidate memory retains every observation for audit.  Selection surfaces
    join epoch-bound rows to the current evidence digest.  Replay-row extent is
    measurement telemetry and never chooses an epoch.  The legacy fallback is
    limited to caches in which no producer row carries an evidence identity.
    """
    epoch_bound = [rec for rec in records if _record_evidence_epoch(rec)]
    if epoch_bound:
        from ztare.common.observation_chart import capture_project_evidence_epoch

        current_epoch = capture_project_evidence_epoch(project).epoch_sha256
        current: list[dict[str, Any]] = []
        for rec in epoch_bound:
            if _record_evidence_epoch(rec) != current_epoch:
                continue
            full_sha = _normalized_carrier_sha(project, rec)
            if not full_sha:
                continue
            normalized = dict(rec)
            normalized["sha"] = full_sha
            normalized["evidence_epoch_sha256"] = current_epoch
            binding = normalized.get("carrier_evidence_identity")
            if not isinstance(binding, dict):
                normalized["carrier_evidence_identity"] = {
                    "schema": "ztare-current-carrier-evidence-identity-v1",
                    "carrier_ref": str(normalized.get("submission") or ""),
                    "carrier_sha256": full_sha,
                    "evidence_epoch_sha256": current_epoch,
                    "carrier_role": "evaluated_candidate",
                }
            current.append(normalized)

        by_sha: dict[str, list[dict[str, Any]]] = {}
        for rec in current:
            by_sha.setdefault(str(rec["sha"]), []).append(rec)
        active: list[dict[str, Any]] = []
        for rows in by_sha.values():
            newest_at = max(str(row.get("observed_at_utc") or "") for row in rows)
            newest = [
                row for row in rows
                if str(row.get("observed_at_utc") or "") == newest_at
            ]
            refuted = [
                row for row in newest
                if row.get("source_type") == "deterministic_near_miss"
            ]
            active.append(_with_content_addressed_source((refuted or newest)[0], rows))
        return active

    # Compatibility for pre-identity caches.  These rows cannot exact-join to
    # current carrier/evidence consumers and disappear after the first new gate
    # observation writes an epoch-bound row.
    by_sha: dict[str, list[dict[str, Any]]] = {}
    unkeyed: list[dict[str, Any]] = []
    for rec in records:
        sha = str(rec.get("sha") or rec.get("candidate_sha") or "").strip()
        if not sha:
            unkeyed.append(rec)
            continue
        by_sha.setdefault(sha, []).append(rec)

    active = list(unkeyed)
    for rows in by_sha.values():
        newest_extent = max(int(row.get("visible_checked_rows") or 0) for row in rows)
        at_extent = [
            row for row in rows
            if int(row.get("visible_checked_rows") or 0) == newest_extent
        ]
        newest_observation = max(
            str(row.get("observed_at_utc") or "") for row in at_extent
        )
        newest = [
            row for row in at_extent
            if str(row.get("observed_at_utc") or "") == newest_observation
        ]
        # Legacy rows often have no observation time.  Prefer a refuting epoch
        # over a passing label when both describe the same bytes and extent.
        if len(newest) > 1:
            refuted = [
                row for row in newest
                if row.get("source_type") == "deterministic_near_miss"
            ]
            selected = refuted or newest[:1]
        else:
            selected = newest
        active.extend(
            _with_content_addressed_source(row, rows)
            for row in selected
        )
    return active


def _with_content_addressed_source(
    selected: dict[str, Any],
    same_identity_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Keep newest evidence while resolving carrier source by content identity."""

    if _is_submission_source_ref(selected):
        return selected
    immutable = [row for row in same_identity_rows if _is_submission_source_ref(row)]
    if not immutable:
        return selected
    source_row = max(
        immutable,
        key=lambda row: (
            int(row.get("visible_checked_rows") or 0),
            str(row.get("observed_at_utc") or ""),
        ),
    )
    projected = dict(selected)
    projected["submission"] = source_row["submission"]
    return projected


def candidate_memory_contract_error(project: str | Path, rec: dict[str, Any]) -> str | None:
    source = candidate_memory_source(project, rec)
    if not source:
        return "candidate memory source unavailable"
    root = Path(project)
    return _carrier_chain_contract_error(
        root,
        source,
        dynamics_assumption=project_dynamics_assumption(root),
    )


def candidate_memory_source(project: str | Path, rec: dict[str, Any]) -> str:
    root = Path(project)
    rel = str(rec.get("submission") or "").strip()
    candidates: list[Path] = []
    if rel:
        candidates.append(root / rel)
        candidates.append(root / "workspace" / rel)
    for path in candidates:
        try:
            if path.exists() and path.is_file():
                return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
    return str(rec.get("source_excerpt") or "")


def candidate_memory_submission_path(
    project: str | Path,
    rec: dict[str, Any],
) -> Path | None:
    """Resolve a selectable immutable submission and verify its carrier identity."""

    if not _is_submission_source_ref(rec):
        return None
    root = Path(project).resolve()
    path = (root / str(rec.get("submission"))).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        return None
    if not path.is_file():
        return None
    expected = str(rec.get("sha") or rec.get("candidate_sha") or "").strip().lower()
    if expected and len(expected) >= 12 and all(ch in "0123456789abcdef" for ch in expected):
        try:
            observed = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            return None
        if not (observed.startswith(expected) or expected.startswith(observed)):
            return None
    return path


def _is_submission_source_ref(rec: dict[str, Any]) -> bool:
    ref = str(rec.get("submission") or "").strip().replace("\\", "/")
    return ref.startswith("workspace/submissions/") and ".." not in Path(ref).parts


def _carrier_chain_contract_error(
    project: Path,
    source: str,
    *,
    dynamics_assumption: str | None = None,
    _seen: set[Path] | None = None,
) -> str | None:
    err = carrier_contract_error(source, dynamics_assumption=dynamics_assumption)
    if err:
        return err
    fields = patch_base_fields_from_source(source)
    if not fields:
        return None
    ref, expected_sha = fields
    try:
        path = resolve_patch_base_ref(project, ref)
    except ValueError as exc:
        return str(exc)
    if _seen is None:
        _seen = set()
    if path in _seen:
        return "PATCH_BASE chain cycle."
    _seen.add(path)
    try:
        data = path.read_bytes()
        nested = data.decode("utf-8", errors="ignore")
    except Exception as exc:  # noqa: BLE001
        return f"PATCH_BASE source_ref unreadable: {exc}"
    try:
        verify_patch_base_digest(path, expected_sha, allow_legacy_prefix=True)
    except ValueError as exc:
        return str(exc)
    return _carrier_chain_contract_error(
        project,
        nested,
        dynamics_assumption=dynamics_assumption,
        _seen=_seen,
    )
