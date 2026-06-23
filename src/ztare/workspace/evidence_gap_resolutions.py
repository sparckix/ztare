"""Write hash-bound evidence-gap resolution receipts."""
from __future__ import annotations

import argparse
import os
import json
import sys
import time
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile
from typing import Any

from ztare.common.paths import REPO_ROOT
from ztare.workspace.compile_evidence import (
    build_evidence_gap_action_contract,
    load_active_evidence_gaps,
    read_json,
    resolve_project_dir,
    sha256_file,
)
from ztare.workspace.evidence_gaps import (
    EVIDENCE_GAP_RESOLUTION_FILENAME,
    EVIDENCE_GAP_RESOLUTION_SCHEMA,
    evidence_gap_fingerprint,
    evidence_gap_recovery,
)


PRODUCER = "ztare.workspace.evidence_gap_resolutions::write_gap_resolution"
VALID_RESOLUTION_STATUSES = ("justified", "not_applicable", "waived")
LOCK_TIMEOUT_SECONDS = 10.0
LOCK_POLL_SECONDS = 0.05


def _rel(path: Path, repo: Path = REPO_ROOT) -> str:
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _load_gap_source(project_dir: Path, *, source: str = "latest") -> tuple[dict[str, Any], Path]:
    normalized = source.strip().lower()
    if normalized == "latest":
        path = project_dir / "workspace" / "latest_evidence_gaps.json"
    elif normalized == "champion":
        path = project_dir / "workspace" / "champion_evidence_gaps.json"
    elif normalized == "active":
        _active_payload, path, warnings = load_active_evidence_gaps(project_dir / "workspace")
        if _active_payload is None or path is None:
            warning_text = "; ".join(warnings) if warnings else "no active evidence gaps"
            raise SystemExit(f"no active evidence-gap source found: {warning_text}")
        payload = read_json(path)
        gaps = payload.get("evidence_gaps")
        if not isinstance(gaps, list):
            raise SystemExit(f"{_rel(path)} does not contain an evidence_gaps list")
        return payload, path
    else:
        raise SystemExit("source must be one of: latest, champion, active")
    payload = read_json(path)
    gaps = payload.get("evidence_gaps")
    if not isinstance(gaps, list):
        raise SystemExit(f"{_rel(path)} does not contain an evidence_gaps list")
    return payload, path


def _load_latest_gaps(project_dir: Path) -> tuple[dict[str, Any], Path]:
    return _load_gap_source(project_dir, source="latest")


def _find_gap(
    gaps: list[Any],
    *,
    gap_id: str | None = None,
    target: str | None = None,
    index: int | None = None,
) -> dict[str, Any]:
    if index is not None:
        if index < 0 or index >= len(gaps):
            raise SystemExit(f"gap index out of range: {index}")
        gap = gaps[index]
        if not isinstance(gap, dict):
            raise SystemExit(f"gap at index {index} is not an object")
        return gap
    matches: list[dict[str, Any]] = []
    for gap in gaps:
        if not isinstance(gap, dict):
            continue
        if gap_id is not None and str(gap.get("id") or "").strip() != gap_id:
            continue
        if target is not None and _gap_target(gap) != target:
            continue
        matches.append(gap)
    if not matches:
        raise SystemExit("no evidence gap matched the selector")
    if len(matches) > 1:
        raise SystemExit("evidence gap selector is ambiguous; use --index")
    return matches[0]


def _gap_target(gap: dict[str, Any]) -> str:
    return str(gap.get("target") or gap.get("applies_to") or "").strip()


def _normalize_project_ref(path: str, *, project_dir: Path) -> Path:
    raw = path.strip().replace("\\", "/")
    if not raw or "\n" in raw or "\r" in raw or "://" in raw:
        raise SystemExit(f"unsupported evidence ref: {path!r}")
    project_prefix = f"projects/{project_dir.name}/"
    if raw.startswith(project_prefix):
        raw = raw[len(project_prefix):]
    posix = PurePosixPath(raw)
    if posix.is_absolute() or any(part in {"", ".", ".."} for part in posix.parts):
        raise SystemExit(f"unsafe evidence ref: {path!r}")
    candidate = project_dir / posix.as_posix()
    project_root = project_dir.resolve()
    try:
        resolved = candidate.resolve()
        resolved.relative_to(project_root)
    except ValueError as exc:
        raise SystemExit(f"evidence ref escapes project: {path!r}") from exc
    if not resolved.is_file():
        raise SystemExit(f"evidence ref does not exist: {path!r}")
    return resolved


def _evidence_ref_rows(refs: list[str], *, project_dir: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for ref in refs:
        path = _normalize_project_ref(ref, project_dir=project_dir)
        rows.append(
            {
                "path": path.relative_to(project_dir.resolve()).as_posix(),
                "sha256": sha256_file(path),
            }
        )
    return rows


def build_gap_resolution_row(
    *,
    project_dir: Path,
    gap: dict[str, Any],
    gap_source_path: Path,
    status: str,
    reason: str,
    evidence_refs: list[str] | None = None,
    repo: Path = REPO_ROOT,
) -> dict[str, Any]:
    normalized_status = status.strip().lower()
    if normalized_status not in VALID_RESOLUTION_STATUSES:
        raise SystemExit(
            "status must be one of: " + ", ".join(VALID_RESOLUTION_STATUSES)
        )
    normalized_reason = " ".join(reason.strip().split())
    if len(normalized_reason) < 16:
        raise SystemExit("resolution reason must be at least 16 characters")
    gap_sha = evidence_gap_fingerprint(gap)
    resolution_id = "egr_" + gap_sha[:16]
    return {
        "resolution_id": resolution_id,
        "project": project_dir.name,
        "gap_id": str(gap.get("id") or "").strip(),
        "target": _gap_target(gap),
        "gap_sha256": gap_sha,
        "gap_source_path": _rel(gap_source_path, repo),
        "status": normalized_status,
        "reason": normalized_reason,
        "resolved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "producer": PRODUCER,
        "llm_calls": False,
        "recovery_before_resolution": evidence_gap_recovery(
            gap,
            project_dir=project_dir,
        ),
        "evidence_refs": _evidence_ref_rows(evidence_refs or [], project_dir=project_dir),
    }


def _load_receipt(path: Path, *, project_dir: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "schema": EVIDENCE_GAP_RESOLUTION_SCHEMA,
            "project": project_dir.name,
            "resolutions": [],
        }
    payload = read_json(path)
    if payload.get("schema") != EVIDENCE_GAP_RESOLUTION_SCHEMA:
        raise SystemExit(f"unexpected evidence-gap resolution schema in {_rel(path)}")
    if str(payload.get("project") or "") != project_dir.name:
        raise SystemExit(f"evidence-gap resolution receipt belongs to another project: {_rel(path)}")
    if not isinstance(payload.get("resolutions"), list):
        raise SystemExit(f"evidence-gap resolution receipt has no resolutions list: {_rel(path)}")
    return payload


@contextmanager
def _receipt_lock(path: Path):
    lock_path = path.with_name(f"{path.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + LOCK_TIMEOUT_SECONDS
    fd: int | None = None
    while fd is None:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise SystemExit(f"timed out waiting for evidence-gap receipt lock: {_rel(lock_path)}")
            time.sleep(LOCK_POLL_SECONDS)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(f"pid={os.getpid()} acquired_at={time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n")
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def _write_receipt_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    with NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as handle:
        tmp_path = Path(handle.name)
        handle.write(serialized)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, path)


def write_gap_resolution(
    *,
    project_dir: Path,
    gap_id: str | None = None,
    target: str | None = None,
    index: int | None = None,
    source: str = "latest",
    status: str = "justified",
    reason: str,
    evidence_refs: list[str] | None = None,
    receipt_path: Path | None = None,
    repo: Path = REPO_ROOT,
) -> dict[str, Any]:
    payload, gap_source_path = _load_gap_source(project_dir, source=source)
    gaps = payload.get("evidence_gaps")
    assert isinstance(gaps, list)
    gap = _find_gap(gaps, gap_id=gap_id, target=target, index=index)
    row = build_gap_resolution_row(
        project_dir=project_dir,
        gap=gap,
        gap_source_path=gap_source_path,
        status=status,
        reason=reason,
        evidence_refs=evidence_refs or [],
        repo=repo,
    )
    output = receipt_path or project_dir / "workspace" / EVIDENCE_GAP_RESOLUTION_FILENAME
    with _receipt_lock(output):
        receipt = _load_receipt(output, project_dir=project_dir)
        existing = [
            item
            for item in receipt["resolutions"]
            if not (
                isinstance(item, dict)
                and item.get("gap_sha256") == row["gap_sha256"]
                and item.get("status") == row["status"]
            )
        ]
        receipt["resolutions"] = [*existing, row]
        receipt["updated_at"] = row["resolved_at"]
        receipt["producer"] = PRODUCER
        receipt["llm_calls"] = False
        receipt["resolution_count"] = len(receipt["resolutions"])
        _write_receipt_atomic(output, receipt)
    return {
        "path": _rel(output, repo),
        "resolution": row,
        "resolution_count": receipt["resolution_count"],
    }


def _cmd_justify(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Write a hash-bound resolution for a current evidence gap.",
    )
    parser.add_argument("--project", required=True)
    parser.add_argument(
        "--source",
        choices=("latest", "champion", "active"),
        default="latest",
        help=(
            "Evidence-gap source to resolve. 'latest' preserves historical "
            "behavior; 'active' resolves the same source selected by list/trace."
        ),
    )
    selector = parser.add_mutually_exclusive_group(required=True)
    selector.add_argument("--gap-id")
    selector.add_argument("--target")
    selector.add_argument("--index", type=int)
    parser.add_argument("--status", choices=VALID_RESOLUTION_STATUSES, default="justified")
    parser.add_argument("--reason", required=True)
    parser.add_argument("--evidence-ref", action="append", default=[])
    parser.add_argument("--receipt")
    parser.add_argument("--json", action="store_true")
    ns = parser.parse_args(args)

    project_dir = resolve_project_dir(ns.project)
    receipt_path = Path(ns.receipt) if ns.receipt else None
    result = write_gap_resolution(
        project_dir=project_dir,
        gap_id=ns.gap_id,
        target=ns.target,
        index=ns.index,
        source=ns.source,
        status=ns.status,
        reason=ns.reason,
        evidence_refs=ns.evidence_ref,
        receipt_path=receipt_path,
    )
    if ns.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Evidence-gap resolution receipt: {result['path']}")
        print(f"Resolution: {result['resolution']['resolution_id']}")
        print("LLM calls: false")
    return 0


def _cmd_list(args: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="List active evidence gaps and the next recovery action.",
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--json", action="store_true")
    ns = parser.parse_args(args)

    project_dir = resolve_project_dir(ns.project)
    payload, source_path, warnings = load_active_evidence_gaps(project_dir / "workspace")
    if payload is None:
        payload = {
            "schema": "ztare-evidence-gap-list-v1",
            "project": project_dir.name,
            "evidence_gaps": [],
            "active_evidence_gap_count": 0,
            "inactive_evidence_gap_count": 0,
        }
    else:
        payload = {
            **payload,
            "schema": "ztare-evidence-gap-list-v1",
            "project": project_dir.name,
        }
    result = {
        "schema": "ztare-evidence-gap-list-result-v1",
        "project": project_dir.name,
        "source_path": _rel(source_path) if source_path else None,
        "warnings": warnings,
        "active_evidence_gap_count": len(payload.get("evidence_gaps") or []),
        "evidence_gaps": payload.get("evidence_gaps") or [],
        "next_action": build_evidence_gap_action_contract(project_dir.name, payload),
    }
    if ns.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"Active evidence gaps: {result['active_evidence_gap_count']}")
        if result["source_path"]:
            print(f"Source: {result['source_path']}")
        next_action = result["next_action"].get("next_action", {})
        action_type = next_action.get("action_type", "none")
        print(f"Next action: {action_type}")
        command = next_action.get("command")
        if command:
            print(f"Command: {command}")
        for warning in warnings:
            print(f"Warning: {warning}")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in {"-h", "--help"}:
        print(
            "ztare project evidence-gap <verb> [args...]\n\n"
            "Verbs:\n"
            "  list     list active evidence gaps and the next recovery action\n"
            "  justify  write a hash-bound resolution for a current evidence gap\n\n"
            "Example:\n"
            "  ztare project evidence-gap list --project demo --json\n"
            "  ztare project evidence-gap justify --project demo --gap-id gap1 "
            "--reason 'Covered by source.md; no new public fetch needed.' --json"
        )
        return 0
    verb, *rest = argv
    if verb == "list":
        return _cmd_list(rest)
    if verb == "justify":
        return _cmd_justify(rest)
    print("unknown evidence-gap verb: " + verb)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
