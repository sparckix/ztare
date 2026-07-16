"""Filesystem-backed intake ledger for project/data preparation.

This ledger is intentionally small. It is for prep artifacts that must exist
before a claim can enter the in-loop autoresearch validator: project surface
creation, source setup, minimal reproduction, replication-cost estimate, or an
explicit blocker. It is not RD out-of-loop execution and not a general
scheduler. Resolution consumes the next unresolved prep item from the
append-only ledger so handoff order stays auditable.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from ztare.scaffold.source_check import check_evidence_project
from ztare.scaffold.source_project import project_dir_for
from ztare.workspace.evidence_gaps import (
    LOCAL_VERIFICATION_RECOVERY_KIND,
    PUBLIC_EVIDENCE_RECOVERY_KIND,
    apply_evidence_gap_recovery_policy,
    canonicalize_evidence_gap_recovery_contract,
    normalize_evidence_gap_recovery_kind,
)


DEFAULT_QUEUE_DIR = Path("analytics/public/queues/project_prep")
ALLOWED_KINDS = {
    "substrate_creation",
    "project_prepare",
    "project_intake",
    "project_packet",
    "source_setup",
    "minimal_reproduction",
    "replication_cost_estimate",
    "inloop_blocker",
    "other",
}
ALLOWED_RESULTS = {"ready_for_autoresearch", "blocked_with_reason"}
PREP_ROUTE_DECISION = "prepare_autoresearch_surface"
PACKET_BOUNDARY = "in_loop_autoresearch_candidate"
PROJECT_PACKET_REQUIRED_SCALARS = (
    "project",
    "rubric",
    "task",
    "bounded_claim",
    "expected_command",
    "next_falsifier",
)
PROJECT_PACKET_REQUIRED_LISTS = ("source_refs", "evidence_refs", "non_claims")
PROJECT_PACKET_OPTIONAL_GAP_CONTRACTS = "evidence_gap_contracts"
PROJECT_PACKET_OPTIONAL_GAP_POLICY = "evidence_gap_recovery_policy"
EXTERNAL_REF_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://")
SHELL_CONTROL_RE = re.compile(r"(?:[;&|`<>]|\$\(|\n|\r)")
PACKET_REF_SELECTOR_RE = re.compile(r"^(source_refs|evidence_refs)\[(\d+)\]$")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _repo_root() -> Path:
    env_root = os.environ.get("ZTARE_REPO")
    if env_root:
        return Path(env_root).resolve()
    return Path.cwd()


def queue_dir_from_arg(value: str | None) -> Path:
    raw = (
        value
        or os.environ.get("ZTARE_PROJECT_PREP_QUEUE_DIR")
        or os.environ.get("ZTARE_SUBSTRATE_QUEUE_DIR")
        or str(DEFAULT_QUEUE_DIR)
    )
    path = Path(raw)
    if path.is_absolute():
        return path
    return _repo_root() / path


def queue_paths(queue_dir: Path) -> dict[str, Path]:
    return {
        "pending": queue_dir / "pending.jsonl",
        "completed": queue_dir / "completed.jsonl",
        "events": queue_dir / "events.jsonl",
    }


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"malformed JSONL in {path}:{lineno}: {exc}") from exc
        if not isinstance(payload, dict):
            raise SystemExit(f"malformed JSONL in {path}:{lineno}: row must be an object")
        rows.append(payload)
    return rows


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def stable_item_id(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "ppq_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def stable_packet_id(payload: dict[str, Any]) -> str:
    seed = {
        "bounded_claim": payload.get("bounded_claim") or "",
        "project": payload.get("project") or "",
        "rubric": payload.get("rubric") or "",
        "task": payload.get("task") or "",
    }
    raw = json.dumps(seed, sort_keys=True, separators=(",", ":"))
    return "pp_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def _string_list(values: list[str] | None) -> list[str]:
    return [str(value).strip() for value in (values or []) if str(value).strip()]


def _required_string(packet: dict[str, Any], key: str, errors: list[str]) -> str:
    value = packet.get(key)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"missing required field: {key}")
        return ""
    return value.strip()


def _required_string_list(packet: dict[str, Any], key: str, errors: list[str]) -> list[str]:
    value = packet.get(key)
    if not isinstance(value, list) or not value:
        errors.append(f"missing required non-empty list: {key}")
        return []
    result: list[str] = []
    for idx, item in enumerate(value, start=1):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{key}[{idx}] must be a non-empty string")
            continue
        result.append(item.strip())
    if not result:
        errors.append(f"missing required non-empty list: {key}")
    return result


def _flag_value(tokens: list[str], flag: str) -> str | None:
    for idx, token in enumerate(tokens):
        if token == flag and idx + 1 < len(tokens):
            return tokens[idx + 1]
        prefix = f"{flag}="
        if token.startswith(prefix):
            return token[len(prefix):]
    return None


def _make_assignment_value(tokens: list[str], key: str) -> str | None:
    prefix = f"{key}="
    for token in tokens:
        if token.startswith(prefix):
            return token[len(prefix):]
    return None


def _expected_command_errors(command: str, *, project: str, rubric: str) -> list[str]:
    errors: list[str] = []
    if SHELL_CONTROL_RE.search(command):
        return ["expected_command must be a single in-loop command without shell control operators"]
    try:
        tokens = shlex.split(command)
    except ValueError as exc:
        return [f"expected_command is not shell-parseable: {exc}"]
    if not tokens:
        return ["expected_command must be an in-loop autoresearch entry command"]

    if tokens[:3] == ["ztare", "autoresearch", "route"] or tokens[:3] == ["ztare", "autoresearch", "run"]:
        parsed_project = _flag_value(tokens, "--project")
        parsed_rubric = _flag_value(tokens, "--rubric")
        if parsed_project != project:
            errors.append("expected_command must name the intake project")
        if parsed_rubric != rubric:
            errors.append("expected_command must name the intake rubric")
        return errors

    if len(tokens) >= 2 and tokens[0] == "make" and tokens[1] == "experiment-loop":
        parsed_project = _make_assignment_value(tokens[2:], "PROJECT")
        parsed_rubric = _make_assignment_value(tokens[2:], "RUBRIC")
        if parsed_project != project:
            errors.append("expected_command must name the intake project")
        if parsed_rubric != rubric:
            errors.append("expected_command must name the intake rubric")
        return errors

    return ["expected_command must be an in-loop autoresearch entry command"]


def _unsafe_local_ref_reason(ref: str) -> str | None:
    raw = str(ref or "").strip().replace("\\", "/")
    if not raw:
        return "empty reference"
    path = PurePosixPath(raw)
    if path.is_absolute():
        return "absolute paths are not allowed"
    if any(part in {"", ".", ".."} for part in path.parts):
        return "path traversal or empty path segment is not allowed"
    return None


def _inside_any_root(path: Path, roots: list[Path]) -> bool:
    try:
        resolved = path.resolve()
    except OSError:
        return False
    for root in roots:
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def project_packet_path_safety_policy() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "absolute_local_refs_allowed": False,
        "parent_traversal_allowed": False,
        "symlink_escape_allowed": False,
        "external_url_refs_allowed": True,
        "rejection_error_prefix": "unsafe local path",
        "enforced_by": [
            "src/ztare/scaffold/substrate_queue.py::_unsafe_local_ref_reason",
            "src/ztare/scaffold/substrate_queue.py::_inside_any_root",
            "src/ztare/scaffold/substrate_queue.py::_resolve_local_ref",
            "tests/test_substrate_queue.py::test_project_packet_rejects_parent_traversal_local_ref",
            "tests/test_substrate_queue.py::test_project_packet_rejects_symlink_escape_local_ref",
        ],
    }


def _resolve_local_ref(
    ref: str,
    *,
    base_dir: Path | None,
    repo_root: Path | None,
) -> tuple[Path | None, str | None]:
    if EXTERNAL_REF_RE.match(ref):
        return None, None
    unsafe_reason = _unsafe_local_ref_reason(ref)
    if unsafe_reason is not None:
        return None, unsafe_reason
    raw = Path(ref)
    candidates: list[Path] = []
    if base_dir is not None:
        candidates.append(base_dir / raw)
    if repo_root is not None:
        candidates.append(repo_root / raw)
    if not candidates:
        candidates.append(raw)
    roots = [
        root.resolve()
        for root in (base_dir, repo_root)
        if root is not None
    ]
    for candidate in candidates:
        if candidate.exists():
            if not roots or _inside_any_root(candidate, roots):
                return candidate, None
            return candidate, "resolved path escapes allowed roots"
    return candidates[0], None


def _missing_local_ref_errors(
    refs: list[str],
    *,
    key: str,
    base_dir: Path | None,
    repo_root: Path | None,
) -> list[str]:
    errors: list[str] = []
    for idx, ref in enumerate(refs, start=1):
        if EXTERNAL_REF_RE.match(ref):
            continue
        resolved, unsafe_reason = _resolve_local_ref(ref, base_dir=base_dir, repo_root=repo_root)
        if unsafe_reason is not None:
            errors.append(f"{key}[{idx}] unsafe local path: {ref} ({unsafe_reason})")
            continue
        if resolved is None or not resolved.exists():
            errors.append(f"{key}[{idx}] local path does not exist: {ref}")
    return errors


def _project_source_preflight(
    *,
    project: str,
    rubric: str | None,
    repo_root: Path,
    require: bool | None,
) -> dict[str, Any]:
    if not project:
        return {
            "checked": False,
            "required": bool(require),
            "status": "skipped",
            "reason": "missing project",
        }
    try:
        project_dir = project_dir_for(repo_root, project)
    except ValueError as exc:
        return {
            "checked": False,
            "required": bool(require),
            "status": "blocked",
            "reason": str(exc),
            "blocking": [str(exc)],
        }
    should_check = bool(require) if require is not None else project_dir.exists()
    if not should_check:
        return {
            "checked": False,
            "required": False,
            "status": "skipped",
            "reason": "local project directory not found",
            "project_dir": str(project_dir),
            "next_command": f"ztare project source-init --project {project}",
        }
    report = check_evidence_project(
        project=project,
        repo=repo_root,
        rubric=rubric,
    )
    return {
        "checked": True,
        "required": bool(require),
        "ok": bool(report.get("ok")),
        "status": report.get("status"),
        "project": report.get("project_slug") or project,
        "project_dir": report.get("project_dir"),
        "raw_dir": report.get("raw_dir"),
        "source_count": report.get("source_count", 0),
        "source_evidence_count": report.get("source_evidence_count", 0),
        "untyped_source_count": report.get("untyped_source_count", 0),
        "blocking": list(report.get("blocking") or []),
        "warnings": list(report.get("warnings") or []),
        "next_commands": list(report.get("next_commands") or []),
    }


def _validate_packet_gap_contracts(packet: dict[str, Any]) -> tuple[list[dict[str, Any]], list[str]]:
    rows = packet.get(PROJECT_PACKET_OPTIONAL_GAP_CONTRACTS)
    if rows is None:
        return [], []
    errors: list[str] = []
    contracts: list[dict[str, Any]] = []
    if not isinstance(rows, list):
        return [], [f"{PROJECT_PACKET_OPTIONAL_GAP_CONTRACTS} must be a list when present"]
    for idx, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            errors.append(f"{PROJECT_PACKET_OPTIONAL_GAP_CONTRACTS}[{idx}] must be an object")
            continue
        target = str(row.get("target") or row.get("applies_to") or "").strip()
        description = str(row.get("description") or row.get("summary") or "").strip()
        if not target:
            errors.append(f"{PROJECT_PACKET_OPTIONAL_GAP_CONTRACTS}[{idx}].target is required")
        if len(description) < 16:
            errors.append(
                f"{PROJECT_PACKET_OPTIONAL_GAP_CONTRACTS}[{idx}].description must explain the gap"
            )
        canonical = canonicalize_evidence_gap_recovery_contract(row)
        kind = str(canonical.get("recovery_kind") or "")
        if kind not in {
            LOCAL_VERIFICATION_RECOVERY_KIND,
            PUBLIC_EVIDENCE_RECOVERY_KIND,
        }:
            errors.append(
                f"{PROJECT_PACKET_OPTIONAL_GAP_CONTRACTS}[{idx}].recovery_kind must be "
                f"{LOCAL_VERIFICATION_RECOVERY_KIND!r} or {PUBLIC_EVIDENCE_RECOVERY_KIND!r}"
            )
        if canonical.get("recovery_contract_warnings"):
            warnings = ", ".join(str(item) for item in canonical["recovery_contract_warnings"])
            errors.append(
                f"{PROJECT_PACKET_OPTIONAL_GAP_CONTRACTS}[{idx}] has contradictory recovery fields: {warnings}"
            )
        contract = dict(canonical.get("recovery_contract", {}))
        aliases = [
            str(item).strip()
            for item in row.get("target_aliases", [])
            if str(item).strip()
        ] if isinstance(row.get("target_aliases"), list) else []
        if aliases:
            contract["target_aliases"] = aliases
        contracts.append(contract)
    return contracts, errors


def _validate_packet_gap_policy(packet: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    policy = packet.get(PROJECT_PACKET_OPTIONAL_GAP_POLICY)
    if policy is None:
        return {}, []
    if not isinstance(policy, dict):
        return {}, [f"{PROJECT_PACKET_OPTIONAL_GAP_POLICY} must be an object when present"]
    errors: list[str] = []
    applies_to = str(policy.get("applies_to") or "").strip()
    if applies_to not in {"all_latest_gaps", "all_project_generated_gaps"}:
        errors.append(
            f"{PROJECT_PACKET_OPTIONAL_GAP_POLICY}.applies_to must be "
            "'all_latest_gaps' or 'all_project_generated_gaps'"
        )
    kind = normalize_evidence_gap_recovery_kind(
        str(policy.get("default_recovery_kind") or "")
    )
    if kind not in {LOCAL_VERIFICATION_RECOVERY_KIND, PUBLIC_EVIDENCE_RECOVERY_KIND}:
        errors.append(
            f"{PROJECT_PACKET_OPTIONAL_GAP_POLICY}.default_recovery_kind must be "
            f"{LOCAL_VERIFICATION_RECOVERY_KIND!r} or {PUBLIC_EVIDENCE_RECOVERY_KIND!r}"
        )
    probe = apply_evidence_gap_recovery_policy(
        {
            "target": "policy_probe",
            "description": "Policy probe row used to verify recovery policy shape.",
            "gap_type": "other",
        },
        policy,
    )
    contract = probe.get("recovery_contract")
    if policy and not isinstance(contract, dict):
        errors.append(f"{PROJECT_PACKET_OPTIONAL_GAP_POLICY} does not produce a recovery contract")
    elif isinstance(contract, dict) and not contract.get("contract_ok"):
        errors.append(
            f"{PROJECT_PACKET_OPTIONAL_GAP_POLICY} produces conflicting recovery fields: "
            + ", ".join(str(item) for item in contract.get("warnings") or [])
        )
    return dict(policy), errors


def build_project_packet(
    *,
    project: str,
    rubric: str,
    task: str,
    bounded_claim: str,
    source_refs: list[str] | None = None,
    evidence_refs: list[str] | None = None,
    non_claims: list[str] | None = None,
    next_falsifier: str,
    expected_command: str,
    notes: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    packet = {
        "schema_version": 1,
        "created_at": created_at or now_iso(),
        "execution_boundary": PACKET_BOUNDARY,
        "project": project.strip(),
        "rubric": rubric.strip(),
        "task": task.strip(),
        "bounded_claim": bounded_claim.strip(),
        "source_refs": _string_list(source_refs),
        "evidence_refs": _string_list(evidence_refs),
        "non_claims": _string_list(non_claims),
        "next_falsifier": next_falsifier.strip(),
        "expected_command": expected_command.strip(),
        "notes": notes.strip() if notes else None,
    }
    packet["packet_id"] = stable_packet_id(packet)
    return packet


def write_project_packet(path: Path, packet: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return packet


def validate_project_packet(
    packet: dict[str, Any],
    *,
    base_dir: Path | None = None,
    repo_root: Path | None = None,
    require_source_preflight: bool | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    if packet.get("schema_version") != 1:
        errors.append("schema_version must be 1")
    if packet.get("execution_boundary") != PACKET_BOUNDARY:
        errors.append(f"execution_boundary must be {PACKET_BOUNDARY!r}")
    strings = {
        key: _required_string(packet, key, errors)
        for key in PROJECT_PACKET_REQUIRED_SCALARS
    }
    lists = {
        key: _required_string_list(packet, key, errors)
        for key in PROJECT_PACKET_REQUIRED_LISTS
    }
    expected_command = strings["expected_command"]
    if expected_command:
        project = strings["project"]
        rubric = strings["rubric"]
        errors.extend(_expected_command_errors(expected_command, project=project, rubric=rubric))
    effective_repo_root = repo_root or _repo_root()
    errors.extend(
        _missing_local_ref_errors(
            lists["source_refs"],
            key="source_refs",
            base_dir=base_dir,
            repo_root=effective_repo_root,
        )
    )
    errors.extend(
        _missing_local_ref_errors(
            lists["evidence_refs"],
            key="evidence_refs",
            base_dir=base_dir,
            repo_root=effective_repo_root,
        )
    )
    source_preflight = _project_source_preflight(
        project=str(packet.get("project") or ""),
        rubric=str(packet.get("rubric") or "") or None,
        repo_root=effective_repo_root,
        require=require_source_preflight,
    )
    for item in source_preflight.get("blocking") or []:
        errors.append(f"source_preflight: {item}")
    for item in source_preflight.get("warnings") or []:
        warnings.append(f"source_preflight: {item}")
    if "out-of-loop" in json.dumps(packet, sort_keys=True).lower():
        warnings.append(
            "packet mentions out-of-loop; confirm this is not RD agent execution masquerading as queue intake"
        )
    evidence_gap_contracts, gap_contract_errors = _validate_packet_gap_contracts(packet)
    errors.extend(gap_contract_errors)
    evidence_gap_recovery_policy, gap_policy_errors = _validate_packet_gap_policy(packet)
    errors.extend(gap_policy_errors)
    return {
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
        "packet_id": packet.get("packet_id"),
        "project": packet.get("project"),
        "rubric": packet.get("rubric"),
        "source_preflight": source_preflight,
        "evidence_gap_contracts": evidence_gap_contracts,
        "evidence_gap_recovery_policy": evidence_gap_recovery_policy,
    }


def load_project_packet(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid project-intake JSON {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"invalid project-intake JSON {path}: top-level value must be an object")
    return payload


def _load_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise SystemExit(f"cannot read {label} {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid {label} JSON {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"invalid {label} JSON {path}: top-level value must be an object")
    return payload


def _rel_to_repo(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _compiled_candidate_claims(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = payload.get("candidate_claims_to_test")
    if isinstance(candidates, list):
        return [row for row in candidates if isinstance(row, dict)]
    claims = payload.get("claims")
    if isinstance(claims, list):
        return [row for row in claims if isinstance(row, dict)]
    return []


def _raw_ref_repair_candidates(
    *,
    missing_ref: str,
    project_root: Path,
    repo_root: Path,
) -> list[dict[str, str]]:
    raw_prefix = f"projects/{project_root.name}/raw/"
    if not missing_ref.startswith(raw_prefix):
        return []
    raw_dir = project_root / "raw"
    raw_rel = missing_ref[len(raw_prefix):]
    parts = PurePosixPath(raw_rel).parts
    candidates: list[dict[str, str]] = []
    seen: set[str] = set()

    for index in range(len(parts)):
        candidate_parts = [*parts[:index], *parts[index + 1 :]]
        if not candidate_parts:
            continue
        candidate_rel = PurePosixPath(*candidate_parts).as_posix()
        if candidate_rel in seen:
            continue
        seen.add(candidate_rel)
        candidate_path = raw_dir / Path(candidate_rel)
        if candidate_path.is_file():
            candidates.append(
                {
                    "to_ref": _rel_to_repo(candidate_path, repo_root),
                    "method": "drop_one_raw_path_segment",
                }
            )

    if not candidates and parts:
        filename = parts[-1]
        filename_matches = [
            path
            for path in raw_dir.rglob("*")
            if path.is_file() and path.name == filename
        ]
        if len(filename_matches) == 1:
            candidates.append(
                {
                    "to_ref": _rel_to_repo(filename_matches[0], repo_root),
                    "method": "unique_raw_filename",
                }
            )
    return candidates


def _source_id_map(
    provenance: dict[str, Any],
    *,
    raw_dir: Path,
    repo_root: Path,
    project_root: Path,
    repair_moved_sources: bool = False,
) -> tuple[dict[str, str], list[dict[str, str]], list[dict[str, Any]]]:
    rows = provenance.get("sources")
    if not isinstance(rows, list):
        return {}, [], []
    result: dict[str, str] = {}
    repairs: list[dict[str, str]] = []
    repair_blockers: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        source_id = str(row.get("source_id") or "").strip()
        source_path = str(row.get("path") or "").strip()
        if not source_id or not source_path:
            continue
        path = Path(source_path)
        if not path.is_absolute():
            path = raw_dir / path
        source_ref = _rel_to_repo(path, repo_root)
        if repair_moved_sources and not (repo_root / source_ref).exists():
            candidates = _raw_ref_repair_candidates(
                missing_ref=source_ref,
                project_root=project_root,
                repo_root=repo_root,
            )
            if len(candidates) == 1:
                repaired_ref = candidates[0]["to_ref"]
                repairs.append(
                    {
                        "source_id": source_id,
                        "from_ref": source_ref,
                        "to_ref": repaired_ref,
                        "method": candidates[0]["method"],
                    }
                )
                source_ref = repaired_ref
            elif candidates:
                repair_blockers.append(
                    {
                        "source_id": source_id,
                        "from_ref": source_ref,
                        "reason": "ambiguous_moved_source_alias",
                        "candidates": [candidate["to_ref"] for candidate in candidates],
                    }
                )
        result[source_id] = source_ref
    return result, repairs, repair_blockers


def _compiled_artifact_refs(
    *,
    compiled_path: Path,
    provenance_path: Path,
    repo_root: Path,
) -> list[str]:
    refs = [_rel_to_repo(compiled_path, repo_root)]
    for text_path in (
        compiled_path.with_name("compiled_evidence.txt"),
        compiled_path.with_suffix(".txt"),
    ):
        if text_path.exists():
            text_ref = _rel_to_repo(text_path, repo_root)
            if text_ref not in refs:
                refs.append(text_ref)
    if provenance_path.exists():
        refs.append(_rel_to_repo(provenance_path, repo_root))
    return refs


def build_project_packet_from_compiled(
    *,
    project: str,
    rubric: str,
    output_path: Path,
    compiled_path: Path,
    provenance_path: Path | None = None,
    claim_index: int = 1,
    task: str | None = None,
    bounded_claim: str | None = None,
    next_falsifier: str | None = None,
    non_claims: list[str] | None = None,
    repo_root: Path | None = None,
    repair_moved_sources: bool = False,
) -> dict[str, Any]:
    """Draft a normal project-intake file from an existing compiled evidence artifact."""

    repo = repo_root or _repo_root()
    project_root = project_dir_for(repo, project)
    compiled = compiled_path if compiled_path.is_absolute() else repo / compiled_path
    provenance = (
        provenance_path
        if provenance_path is not None
        else project_root / "compiled_evidence_provenance.json"
    )
    if not provenance.is_absolute():
        provenance = repo / provenance
    if claim_index < 1:
        raise SystemExit("--claim-index is 1-based and must be >= 1")

    compiled_payload = _load_json_object(compiled, label="compiled evidence artifact")
    provenance_payload = _load_json_object(provenance, label="compile provenance")
    raw_dir_value = str(provenance_payload.get("raw_dir") or "")
    raw_dir = Path(raw_dir_value) if raw_dir_value else project_root / "raw"
    if not raw_dir.is_absolute():
        repo_relative_raw_dir = repo / raw_dir
        raw_dir = repo_relative_raw_dir if repo_relative_raw_dir.exists() else project_root / raw_dir

    candidates = _compiled_candidate_claims(compiled_payload)
    if not candidates:
        raise SystemExit(
            "compiled artifact has no candidate_claims_to_test rows; use "
            "`ztare project intake create` with an explicit bounded claim"
        )
    if claim_index > len(candidates):
        raise SystemExit(
            f"--claim-index {claim_index} exceeds {len(candidates)} compiled claim row(s)"
        )
    candidate = candidates[claim_index - 1]
    claim = str(bounded_claim or candidate.get("claim") or "").strip()
    if not claim:
        raise SystemExit("selected compiled claim row has no claim text")

    source_map, source_ref_repairs, source_ref_repair_blockers = _source_id_map(
        provenance_payload,
        raw_dir=raw_dir,
        repo_root=repo,
        project_root=project_root,
        repair_moved_sources=repair_moved_sources,
    )
    candidate_source_ids = [
        str(value).strip()
        for value in candidate.get("source_ids") or []
        if str(value).strip()
    ]
    source_refs = [
        source_map[source_id]
        for source_id in candidate_source_ids
        if source_id in source_map
    ]
    if not source_refs:
        raise SystemExit(
            "selected compiled claim row has no source_ids that map to local "
            "compile provenance paths; use `ztare project intake create` explicitly"
        )
    missing_source_ids = [
        source_id for source_id in candidate_source_ids if source_id not in source_map
    ]
    evidence_refs = _compiled_artifact_refs(
        compiled_path=compiled,
        provenance_path=provenance,
        repo_root=repo,
    )
    missing_source_refs = [
        ref
        for ref in source_refs
        if not (repo / ref).exists()
    ]
    task_text = (
        task
        or f"test whether compiled claim {claim_index} remains supported under in-loop review"
    )
    out_rel = _rel_to_repo(output_path if output_path.is_absolute() else repo / output_path, repo)
    expected_command = shlex.join(
        [
            "ztare",
            "autoresearch",
            "route",
            "--task",
            task_text,
            "--project",
            project,
            "--rubric",
            rubric,
            "--packet",
            out_rel,
        ]
    )
    default_non_claims = non_claims or [
        "not evidence that the claim is true",
        "not a full replication",
        "not a live autoresearch run",
    ]
    if source_ref_repairs:
        default_non_claims = [
            *default_non_claims,
            "not evidence that compiled evidence was refreshed after raw source moves",
        ]

    repair_note = (
        f"; repaired_moved_source_refs={len(source_ref_repairs)}"
        if source_ref_repairs
        else ""
    )
    packet = build_project_packet(
        project=project,
        rubric=rubric,
        task=task_text,
        bounded_claim=claim,
        source_refs=source_refs,
        evidence_refs=evidence_refs,
        non_claims=default_non_claims,
        next_falsifier=next_falsifier
        or "remove one declared source or compiled artifact ref and validation must fail",
        expected_command=expected_command,
        notes=(
            f"Drafted from {_rel_to_repo(compiled, repo)} claim_index={claim_index}; "
            f"review before enqueueing for in-loop autoresearch{repair_note}."
        ),
    )
    packet["draft_source"] = {
        "kind": "compiled_evidence_artifact",
        "compiled_path": _rel_to_repo(compiled, repo),
        "provenance_path": _rel_to_repo(provenance, repo),
        "claim_index": claim_index,
        "candidate_source_ids": candidate_source_ids,
        "missing_source_ids": missing_source_ids,
        "missing_source_refs": missing_source_refs,
        "source_ref_repairs": source_ref_repairs,
        "source_ref_repair_blockers": source_ref_repair_blockers,
        "repair_moved_sources": repair_moved_sources,
    }
    packet["packet_id"] = stable_packet_id(packet)
    return packet


def validate_project_packet_path(
    path: Path,
    *,
    require_source_preflight: bool | None = None,
) -> dict[str, Any]:
    packet = load_project_packet(path)
    return {
        "path": str(path),
        **validate_project_packet(
            packet,
            base_dir=path.parent,
            require_source_preflight=require_source_preflight,
        ),
    }


def _parse_packet_ref_selector(selector: str) -> tuple[str, int]:
    match = PACKET_REF_SELECTOR_RE.match(str(selector or "").strip())
    if not match:
        raise SystemExit(
            "packet falsifier --remove-ref must use source_refs[N] or "
            "evidence_refs[N] with 1-based N"
        )
    return match.group(1), int(match.group(2)) - 1


def validate_project_packet_falsifier(
    path: Path,
    *,
    remove_ref: str,
    require_source_preflight: bool | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Validate that removing a declared local ref makes a packet fail.

    The falsifier is simulated in memory: the selected source/evidence ref is
    replaced by a guaranteed-missing local path, then the ordinary packet
    validator must reject it. The real checkout is not mutated.
    """
    packet = load_project_packet(path)
    baseline = validate_project_packet(
        packet,
        base_dir=path.parent,
        repo_root=repo_root,
        require_source_preflight=require_source_preflight,
    )
    path_safety = project_packet_path_safety_policy()
    list_key, idx = _parse_packet_ref_selector(remove_ref)
    refs = list(packet.get(list_key) or [])
    if idx < 0 or idx >= len(refs):
        return {
            "ok": False,
            "path": str(path),
            "remove_ref": remove_ref,
            "baseline": baseline,
            "falsified": None,
            "path_safety": path_safety,
            "reason": f"{remove_ref} is out of range",
        }
    original_ref = refs[idx]
    if not isinstance(original_ref, str) or not original_ref.strip():
        return {
            "ok": False,
            "path": str(path),
            "remove_ref": remove_ref,
            "baseline": baseline,
            "falsified": None,
            "path_safety": path_safety,
            "reason": f"{remove_ref} is not a non-empty string",
        }
    if EXTERNAL_REF_RE.match(original_ref):
        return {
            "ok": False,
            "path": str(path),
            "remove_ref": remove_ref,
            "baseline": baseline,
            "falsified": None,
            "path_safety": path_safety,
            "reason": f"{remove_ref} is external; local removal falsifier does not apply",
        }
    falsified_packet = dict(packet)
    falsified_refs = list(refs)
    falsified_refs[idx] = (
        "__ztare_missing_falsifier__/"
        + original_ref.strip().lstrip("/").replace("\\", "/")
    )
    falsified_packet[list_key] = falsified_refs
    falsified = validate_project_packet(
        falsified_packet,
        base_dir=path.parent,
        repo_root=repo_root,
        require_source_preflight=require_source_preflight,
    )
    expected_fragment = f"{list_key}[{idx + 1}] local path does not exist"
    falsifier_fired = any(expected_fragment in error for error in falsified["errors"])
    ok = bool(baseline["ok"]) and (not falsified["ok"]) and falsifier_fired
    return {
        "ok": ok,
        "path": str(path),
        "remove_ref": remove_ref,
        "removed_ref": original_ref,
        "removed_value": original_ref,
        "baseline": baseline,
        "falsified": falsified,
        "expected_error_fragment": expected_fragment,
        "path_safety": path_safety,
        "reason": (
            "intake validator rejects the simulated missing local ref"
            if ok
            else "baseline must pass and falsified intake must fail on the selected ref"
        ),
    }


def project_packet_falsifier_receipt(
    payload: dict[str, Any],
    *,
    command: str,
) -> dict[str, Any]:
    """Return the compact receipt consumed by in-loop local verifier routing."""
    falsified = payload.get("falsified") if isinstance(payload.get("falsified"), dict) else {}
    falsified_errors = [
        str(error)
        for error in (falsified.get("errors") if isinstance(falsified, dict) else []) or []
    ]
    expected_fragment = str(payload.get("expected_error_fragment") or "").strip()
    expected_failure = next(
        (error for error in falsified_errors if expected_fragment and expected_fragment in error),
        expected_fragment,
    )
    return {
        "schema_version": 1,
        "receipt_type": "project_packet_falsifier",
        "status": "resolved" if payload.get("ok") else "failed",
        "command": command,
        "path": payload.get("path"),
        "remove_ref": payload.get("remove_ref"),
        "removed_ref": payload.get("removed_ref") or payload.get("removed_value"),
        "expected_error_fragment": expected_fragment,
        "expected_failure": expected_failure,
        "falsified_errors": falsified_errors,
        "path_safety": payload.get("path_safety") or project_packet_path_safety_policy(),
        "enforced_by": [
            "src/ztare/scaffold/substrate_queue.py::validate_project_packet_falsifier",
            "src/ztare/scaffold/substrate_queue.py::project_packet_falsifier_receipt",
            "src/ztare/cli.py::ztare project intake falsify",
            "scripts/public/control/hello_value_demo.py::main",
            "tests/test_substrate_queue.py::test_project_packet_falsifier_fails_when_declared_evidence_ref_is_removed",
            "tests/test_cli.py::test_project_alias_delegates_to_packet_falsifier",
            "tests/control/test_current_engine_demo.py::test_hello_value_demo_prints_bounded_nonpersistent_summary",
        ],
    }


def project_packet_workspace_receipt_path(
    payload: dict[str, Any],
    *,
    repo_root: Path | None = None,
) -> Path:
    baseline = payload.get("baseline") if isinstance(payload.get("baseline"), dict) else {}
    project = str(baseline.get("project") or "").strip()
    if not project:
        raise SystemExit("cannot derive workspace receipt path: intake project is missing")
    return (
        project_dir_for(repo_root or _repo_root(), project)
        / "workspace"
        / "packet_falsifier_receipt.json"
    )


def write_project_packet_falsifier_receipt(
    path: Path,
    payload: dict[str, Any],
    *,
    command: str,
) -> dict[str, Any]:
    receipt = project_packet_falsifier_receipt(payload, command=command)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def enqueue_item(
    *,
    queue_dir: Path,
    task: str,
    kind: str = "other",
    project: str | None = None,
    rubric: str | None = None,
    source_route_json: str | None = None,
    source_action_impact_id: str | None = None,
    decision_id: str | None = None,
    requested_artifact: str | None = None,
    readiness_criteria: list[str] | None = None,
    claim_boundary: str | None = None,
    notes: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    if not task.strip():
        raise SystemExit("project prep ledger add requires --task <text>")
    if kind not in ALLOWED_KINDS:
        raise SystemExit(f"unknown project prep kind {kind!r}; known: {', '.join(sorted(ALLOWED_KINDS))}")
    created = created_at or now_iso()
    seed = {
        "created_at": created,
        "kind": kind,
        "project": project or "",
        "rubric": rubric or "",
        "task": task,
    }
    item = {
        "schema_version": 1,
        "item_id": stable_item_id(seed),
        "created_at": created,
        "status": "pending",
        "kind": kind,
        "task": task,
        "project": project or None,
        "rubric": rubric or None,
        "source_route_json": source_route_json or None,
        "source_action_impact_id": source_action_impact_id or None,
        "decision_id": decision_id or None,
        "requested_artifact": requested_artifact or None,
        "readiness_criteria": _string_list(readiness_criteria),
        "claim_boundary": claim_boundary or None,
        "notes": notes or None,
    }
    paths = queue_paths(queue_dir)
    append_jsonl(paths["pending"], item)
    append_jsonl(paths["events"], {"event": "enqueued", **item})
    return item


def _load_route_payload(route_json: Path) -> tuple[dict[str, Any], dict[str, Any] | None]:
    try:
        payload = json.loads(route_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid route JSON {route_json}: {exc}") from exc
    if not isinstance(payload, dict):
        raise SystemExit(f"invalid route JSON {route_json}: top-level value must be an object")
    route = payload.get("route") if isinstance(payload.get("route"), dict) else payload
    action = payload.get("action_impact") if isinstance(payload.get("action_impact"), dict) else None
    if not isinstance(route, dict):
        raise SystemExit(f"invalid route JSON {route_json}: missing route object")
    return route, action


def enqueue_from_route(
    *,
    queue_dir: Path,
    route_json: Path,
    decision_id: str | None = None,
    source_action_impact_id: str | None = None,
    notes: str | None = None,
    created_at: str | None = None,
) -> list[dict[str, Any]]:
    route, action = _load_route_payload(route_json)
    decision = str(route.get("decision") or "")
    if decision == "invoke_autoresearch":
        raise SystemExit("route is ready for in-loop autoresearch; no project-prep item needed")
    if decision == "stay_out_of_loop":
        raise SystemExit(
            "route chose stay_out_of_loop: use RD out-of-loop agent execution to define the "
            "bounded claim/evaluator first; do not enqueue it as project/data prep"
        )
    if decision != PREP_ROUTE_DECISION:
        raise SystemExit(
            f"route decision {decision!r} is not supported by the project/data prep "
            "ledger command `ztare project prep-ledger add-from-route`"
        )

    route_action_impact_id = (
        str(action.get("action_impact_id"))
        if action and action.get("action_impact_id")
        else None
    )
    source_decision_id = (
        decision_id
        or (str(action.get("decision_id")) if action and action.get("decision_id") else None)
    )
    task = str(route.get("task") or "prepare autoresearch surface")
    project = str(route.get("project") or "") or None
    rubric = str(route.get("rubric") or "") or None
    scaffolds = route.get("surface_scaffold")
    if not isinstance(scaffolds, list) or not scaffolds:
        missing = route.get("missing")
        scaffolds = [
            {
                "missing": str(item),
                "surface": "autoresearch_surface",
                "artifact": None,
                "required_fields": [],
                "acceptance_check": "missing autoresearch surface is present",
            }
            for item in (missing if isinstance(missing, list) and missing else ["autoresearch surface"])
        ]

    items: list[dict[str, Any]] = []
    for scaffold in scaffolds:
        if not isinstance(scaffold, dict):
            continue
        missing = str(scaffold.get("missing") or scaffold.get("surface") or "autoresearch surface")
        required_fields = scaffold.get("required_fields")
        readiness = [f"required_field:{field}" for field in required_fields] if isinstance(required_fields, list) else []
        acceptance = scaffold.get("acceptance_check")
        if acceptance:
            readiness.append(f"acceptance_check:{acceptance}")
        requested_artifact = scaffold.get("artifact")
        items.append(enqueue_item(
            queue_dir=queue_dir,
            task=f"prepare autoresearch surface: {missing} for {task}",
            kind="project_prepare",
            project=project,
            rubric=rubric,
            source_route_json=str(route_json),
            source_action_impact_id=source_action_impact_id or route_action_impact_id,
            decision_id=source_decision_id,
            requested_artifact=str(requested_artifact) if requested_artifact else None,
            readiness_criteria=readiness,
            claim_boundary="surface preparation only; no research-result claim",
            notes=notes,
            created_at=created_at,
        ))
    return items


def enqueue_project_packet(
    *,
    queue_dir: Path,
    packet_path: Path,
    decision_id: str | None = None,
    notes: str | None = None,
    created_at: str | None = None,
) -> dict[str, Any]:
    packet = load_project_packet(packet_path)
    validation = validate_project_packet(
        packet,
        base_dir=packet_path.parent,
        require_source_preflight=True,
    )
    if not validation["ok"]:
        raise SystemExit("project intake is not ready: " + "; ".join(validation["errors"]))
    project = str(packet.get("project") or "")
    rubric = str(packet.get("rubric") or "")
    task = str(packet.get("task") or "")
    return enqueue_item(
        queue_dir=queue_dir,
        task=f"review project intake for in-loop autoresearch: {task}",
        kind="project_intake",
        project=project,
        rubric=rubric,
        decision_id=decision_id,
        requested_artifact=str(packet_path),
        readiness_criteria=[
            "intake_validates",
            "source_refs_present",
            "evidence_refs_present",
            "non_claims_present",
            "next_falsifier_present",
        ],
        claim_boundary=(
            "project intake only; no research-result claim and no RD "
            "out-of-loop execution"
        ),
        notes=notes,
        created_at=created_at,
    )


def pending_items(queue_dir: Path) -> list[dict[str, Any]]:
    return read_jsonl(queue_paths(queue_dir)["pending"])


def completed_items(queue_dir: Path) -> list[dict[str, Any]]:
    return read_jsonl(queue_paths(queue_dir)["completed"])


def resolve_next_item(
    *,
    queue_dir: Path,
    result: str,
    reason: str | None = None,
    artifact_refs: list[str] | None = None,
    resolved_by: str | None = None,
    resolved_at: str | None = None,
) -> dict[str, Any]:
    if result not in ALLOWED_RESULTS:
        raise SystemExit(f"unknown project prep result {result!r}; known: {', '.join(sorted(ALLOWED_RESULTS))}")
    if result == "blocked_with_reason" and not (reason or "").strip():
        raise SystemExit("project prep ledger resolve-next --result blocked_with_reason requires --reason <text>")
    pending = pending_items(queue_dir)
    if not pending:
        raise SystemExit("project prep ledger is empty")
    item = pending[0]
    remaining = pending[1:]
    resolved = {
        **item,
        "status": result,
        "resolved_at": resolved_at or now_iso(),
        "resolved_by": resolved_by or None,
        "result_reason": reason or None,
        "artifact_refs": _string_list(artifact_refs),
    }
    paths = queue_paths(queue_dir)
    write_jsonl(paths["pending"], remaining)
    append_jsonl(paths["completed"], resolved)
    append_jsonl(paths["events"], {"event": "resolved", **resolved})
    return resolved


def summarize(queue_dir: Path) -> dict[str, Any]:
    pending = pending_items(queue_dir)
    completed = completed_items(queue_dir)
    return {
        "schema_version": 1,
        "queue_dir": str(queue_dir),
        "pending_count": len(pending),
        "completed_count": len(completed),
        "next_item": pending[0] if pending else None,
        "pending": pending,
        "recent_completed": completed[-5:],
    }


def print_summary(payload: dict[str, Any]) -> None:
    print("ztare project prep-ledger  (project/data prep ledger)")
    print(f"  queue_dir: {payload['queue_dir']}")
    print(f"  pending: {payload['pending_count']}")
    print(f"  completed: {payload['completed_count']}")
    next_item = payload.get("next_item")
    if next_item:
        print()
        print("  next:")
        print(f"    {next_item['item_id']}  {next_item['kind']}  {next_item['task']}")
        if next_item.get("project") or next_item.get("rubric"):
            print(f"    project={next_item.get('project') or '-'} rubric={next_item.get('rubric') or '-'}")
        if next_item.get("requested_artifact"):
            print(f"    requested_artifact={next_item['requested_artifact']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ztare project prep-ledger",
        description=__doc__,
        epilog="Compatibility: ztare project queue and ztare substrate queue delegate to the same ledger.",
    )
    parser.add_argument(
        "--queue-dir",
        help="prep-ledger directory; defaults to analytics/public/queues/project_prep",
    )
    sub = parser.add_subparsers(dest="cmd")

    add = sub.add_parser("add", help="enqueue one project/data prep item")
    add.add_argument("--task", required=True)
    add.add_argument("--kind", default="other", choices=sorted(ALLOWED_KINDS))
    add.add_argument("--project")
    add.add_argument("--rubric")
    add.add_argument("--source-route-json")
    add.add_argument("--source-action-impact-id")
    add.add_argument("--decision-id")
    add.add_argument("--requested-artifact")
    add.add_argument("--readiness-criteria", action="append", default=[])
    add.add_argument("--claim-boundary")
    add.add_argument("--notes")
    add.add_argument("--json", action="store_true")

    add_from_route = sub.add_parser(
        "add-from-route",
        help="enqueue missing surface prep from a prepare_autoresearch_surface route JSON",
    )
    add_from_route.add_argument("--route-json", required=True)
    add_from_route.add_argument("--decision-id")
    add_from_route.add_argument("--notes")
    add_from_route.add_argument("--json", action="store_true")

    create_packet = sub.add_parser(
        "create-packet",
        help="write bounded project intake for later in-loop autoresearch entry",
    )
    create_packet.add_argument("--path", required=True)
    create_packet.add_argument("--project", required=True)
    create_packet.add_argument("--rubric", required=True)
    create_packet.add_argument("--task", required=True)
    create_packet.add_argument("--bounded-claim", required=True)
    create_packet.add_argument("--source-ref", action="append", default=[])
    create_packet.add_argument("--evidence-ref", action="append", default=[])
    create_packet.add_argument("--non-claim", action="append", default=[])
    create_packet.add_argument("--next-falsifier", required=True)
    create_packet.add_argument("--expected-command", required=True)
    create_packet.add_argument("--notes")
    create_packet.add_argument("--json", action="store_true")

    draft_from_compiled = sub.add_parser(
        "draft-from-compiled",
        help="draft project intake from a compiled evidence artifact and provenance",
    )
    draft_from_compiled.add_argument("--path", required=True)
    draft_from_compiled.add_argument("--project", required=True)
    draft_from_compiled.add_argument("--rubric")
    draft_from_compiled.add_argument("--compiled")
    draft_from_compiled.add_argument("--provenance")
    draft_from_compiled.add_argument("--claim-index", type=int, default=1)
    draft_from_compiled.add_argument("--task")
    draft_from_compiled.add_argument("--bounded-claim")
    draft_from_compiled.add_argument("--next-falsifier")
    draft_from_compiled.add_argument("--non-claim", action="append", default=[])
    draft_from_compiled.add_argument(
        "--repair-moved-sources",
        action="store_true",
        help="Use deterministic raw-path aliases for moved source refs and record the substitutions.",
    )
    draft_from_compiled.add_argument("--json", action="store_true")

    validate_packet = sub.add_parser(
        "validate-packet",
        help="validate project intake without mutating the ledger",
    )
    validate_packet.add_argument("--path", required=True)
    validate_packet.add_argument("--json", action="store_true")
    validate_packet.add_argument("--strict", action="store_true", help="exit non-zero on warnings")
    validate_packet.add_argument(
        "--source-preflight",
        action="store_true",
        help="require raw/source typing preflight even if the local project directory is missing",
    )
    validate_packet.add_argument(
        "--no-source-preflight",
        action="store_true",
        help="validate only the intake JSON and referenced paths",
    )

    falsify_packet = sub.add_parser(
        "falsify-packet",
        help="check that removing a declared local packet ref makes validation fail",
    )
    falsify_packet.add_argument("--path", required=True)
    falsify_packet.add_argument(
        "--remove-ref",
        default="evidence_refs[1]",
        help="1-based packet ref selector, e.g. evidence_refs[1] or source_refs[1]",
    )
    falsify_packet.add_argument("--json", action="store_true")
    falsify_packet.add_argument(
        "--source-preflight",
        action="store_true",
        help="require raw/source typing preflight even if the local project directory is missing",
    )
    falsify_packet.add_argument(
        "--no-source-preflight",
        action="store_true",
        help="validate only the intake JSON and referenced paths",
    )
    falsify_packet.add_argument(
        "--write-receipt",
        help="write the compact falsifier receipt to this JSON path",
    )
    falsify_packet.add_argument(
        "--write-workspace-receipt",
        action="store_true",
        help=(
            "write the compact receipt to "
            "projects/<packet.project>/workspace/packet_falsifier_receipt.json"
        ),
    )

    enqueue_packet = sub.add_parser(
        "enqueue-packet",
        help="validate and enqueue project intake into the intake ledger",
    )
    enqueue_packet.add_argument("--path", required=True)
    enqueue_packet.add_argument("--decision-id")
    enqueue_packet.add_argument("--notes")
    enqueue_packet.add_argument("--json", action="store_true")

    list_cmd = sub.add_parser("list", help="show pending and completed prep-ledger state")
    list_cmd.add_argument("--json", action="store_true")

    next_cmd = sub.add_parser(
        "next",
        help="show the next pending prep-ledger item without mutating the ledger",
    )
    next_cmd.add_argument("--json", action="store_true")

    resolve = sub.add_parser(
        "resolve-next",
        help="mark the next prep-ledger item ready or blocked, then remove it from pending",
    )
    resolve.add_argument("--result", required=True, choices=sorted(ALLOWED_RESULTS))
    resolve.add_argument("--reason")
    resolve.add_argument("--artifact-ref", action="append", default=[])
    resolve.add_argument("--resolved-by")
    resolve.add_argument("--json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.cmd:
        parser.print_help()
        return 0
    qdir = queue_dir_from_arg(args.queue_dir)
    if args.cmd == "add":
        item = enqueue_item(
            queue_dir=qdir,
            task=args.task,
            kind=args.kind,
            project=args.project,
            rubric=args.rubric,
            source_route_json=args.source_route_json,
            source_action_impact_id=args.source_action_impact_id,
            decision_id=args.decision_id,
            requested_artifact=args.requested_artifact,
            readiness_criteria=args.readiness_criteria,
            claim_boundary=args.claim_boundary,
            notes=args.notes,
        )
        if args.json:
            print(json.dumps(item, indent=2, sort_keys=True))
        else:
            print(f"enqueued {item['item_id']}: {item['kind']} :: {item['task']}")
        return 0
    if args.cmd == "add-from-route":
        items = enqueue_from_route(
            queue_dir=qdir,
            route_json=Path(args.route_json),
            decision_id=args.decision_id,
            notes=args.notes,
        )
        if args.json:
            print(json.dumps({"enqueued": items, "count": len(items)}, indent=2, sort_keys=True))
        else:
            for item in items:
                print(f"enqueued {item['item_id']}: {item['kind']} :: {item['task']}")
        return 0
    if args.cmd == "create-packet":
        packet = build_project_packet(
            project=args.project,
            rubric=args.rubric,
            task=args.task,
            bounded_claim=args.bounded_claim,
            source_refs=args.source_ref,
            evidence_refs=args.evidence_ref,
            non_claims=args.non_claim,
            next_falsifier=args.next_falsifier,
            expected_command=args.expected_command,
            notes=args.notes,
        )
        write_project_packet(Path(args.path), packet)
        validation = validate_project_packet(packet, base_dir=Path(args.path).parent)
        payload = {"path": args.path, "packet": packet, "validation": validation}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            status = "valid" if validation["ok"] else "invalid"
            print(f"wrote {packet['packet_id']} to {args.path}: {status}")
        return 0 if validation["ok"] else 1
    if args.cmd == "draft-from-compiled":
        project_root = project_dir_for(_repo_root(), args.project)
        compiled = Path(args.compiled) if args.compiled else project_root / "compiled_evidence_packet.json"
        provenance = Path(args.provenance) if args.provenance else None
        packet = build_project_packet_from_compiled(
            project=args.project,
            rubric=args.rubric or args.project,
            output_path=Path(args.path),
            compiled_path=compiled,
            provenance_path=provenance,
            claim_index=args.claim_index,
            task=args.task,
            bounded_claim=args.bounded_claim,
            next_falsifier=args.next_falsifier,
            non_claims=args.non_claim,
            repair_moved_sources=args.repair_moved_sources,
        )
        write_project_packet(Path(args.path), packet)
        validation = validate_project_packet(packet, base_dir=Path(args.path).parent)
        payload = {"path": args.path, "packet": packet, "validation": validation}
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            status = "valid" if validation["ok"] else "invalid"
            print(f"drafted {packet['packet_id']} to {args.path}: {status}")
        return 0 if validation["ok"] else 1
    if args.cmd == "validate-packet":
        require_source_preflight = None
        if args.source_preflight:
            require_source_preflight = True
        if args.no_source_preflight:
            require_source_preflight = False
        payload = validate_project_packet_path(
            Path(args.path),
            require_source_preflight=require_source_preflight,
        )
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            status = "valid" if payload["ok"] else "invalid"
            print(f"{status}: {args.path}")
            for warning in payload["warnings"]:
                print(f"  warning: {warning}")
            for error in payload["errors"]:
                print(f"  error: {error}")
        if not payload["ok"] or (args.strict and payload["warnings"]):
            return 1
        return 0
    if args.cmd == "falsify-packet":
        require_source_preflight = None
        if args.source_preflight:
            require_source_preflight = True
        if args.no_source_preflight:
            require_source_preflight = False
        payload = validate_project_packet_falsifier(
            Path(args.path),
            remove_ref=args.remove_ref,
            require_source_preflight=require_source_preflight,
        )
        command_tokens = [
            "ztare",
            "project",
            "packet",
            "falsify",
            "--path",
            args.path,
            "--remove-ref",
            args.remove_ref,
        ]
        if args.source_preflight:
            command_tokens.append("--source-preflight")
        if args.no_source_preflight:
            command_tokens.append("--no-source-preflight")
        receipt_paths: list[Path] = []
        if args.write_workspace_receipt:
            receipt_paths.append(project_packet_workspace_receipt_path(payload))
            command_tokens.append("--write-workspace-receipt")
        if args.write_receipt:
            receipt_paths.append(Path(args.write_receipt))
            command_tokens.extend(["--write-receipt", args.write_receipt])
        written_receipts: list[str] = []
        command = shlex.join(command_tokens)
        for receipt_path in receipt_paths:
            write_project_packet_falsifier_receipt(receipt_path, payload, command=command)
            written_receipts.append(str(receipt_path))
        if written_receipts:
            payload["receipt_paths"] = written_receipts
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            status = "passed" if payload["ok"] else "failed"
            print(f"{status}: {args.path} falsifier {args.remove_ref}")
            print(f"  {payload['reason']}")
            for receipt_path in written_receipts:
                print(f"  receipt: {receipt_path}")
        return 0 if payload["ok"] else 1
    if args.cmd == "enqueue-packet":
        item = enqueue_project_packet(
            queue_dir=qdir,
            packet_path=Path(args.path),
            decision_id=args.decision_id,
            notes=args.notes,
        )
        if args.json:
            print(json.dumps(item, indent=2, sort_keys=True))
        else:
            print(f"enqueued {item['item_id']}: {item['kind']} :: {item['task']}")
        return 0
    if args.cmd == "list":
        payload = summarize(qdir)
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print_summary(payload)
        return 0
    if args.cmd == "next":
        payload = summarize(qdir)
        item = payload["next_item"]
        if args.json:
            print(json.dumps(item or {}, indent=2, sort_keys=True))
        elif item:
            print(f"{item['item_id']}  {item['kind']}  {item['task']}")
        else:
            print("project prep ledger empty")
        return 0
    if args.cmd == "resolve-next":
        item = resolve_next_item(
            queue_dir=qdir,
            result=args.result,
            reason=args.reason,
            artifact_refs=args.artifact_ref,
            resolved_by=args.resolved_by,
        )
        if args.json:
            print(json.dumps(item, indent=2, sort_keys=True))
        else:
            print(f"resolved {item['item_id']}: {item['status']}")
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
