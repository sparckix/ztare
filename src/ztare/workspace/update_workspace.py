import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ztare.common import utils
from ztare.common.llm_runtime import MODEL_MAP
from ztare.workspace.compile_evidence import (
    DEFAULT_EVIDENCE_LLM_RETRIES,
    DEFAULT_EVIDENCE_LLM_TIMEOUT_SECONDS,
    LLMClient,
    PROMPTS_DIR,
    SOURCE_TYPE_MAP_FILENAME,
    SOURCE_TYPE_UNTYPED,
    TEXT_EXTENSIONS,
    annotate_provenance_source_types,
    filter_packet_by_source_types,
    load_source_type_map_with_warnings,
    positive_int,
    read_typed_source,
    read_json,
    read_text,
    repo_display_path,
    resolve_project_dir,
    validate_packet_shape,
    write_json,
    write_text,
)


DEBUG = False


def dbg(msg: str) -> None:
    if not DEBUG:
        return
    ts = time.strftime("%H:%M:%S")
    print(f"[update_workspace {ts}] {msg}", file=sys.stderr)


def load_prompt(name: str) -> str:
    return read_text(PROMPTS_DIR / name).strip()


def sha256_text(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def collect_raw_sources(
    raw_dir: Path,
    max_files: int,
    max_chars_per_file: int,
    max_total_chars: int,
    include_budget_exhausted: bool = False,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    warnings: List[str] = []
    sources: List[Dict[str, Any]] = []
    total_chars = 0

    source_type_overrides, type_map_warnings = load_source_type_map_with_warnings(raw_dir)
    warnings.extend(type_map_warnings)

    all_files = sorted(path for path in raw_dir.rglob("*") if path.is_file())
    supported = [
        path
        for path in all_files
        if path.suffix.lower() in TEXT_EXTENSIONS and path.name != SOURCE_TYPE_MAP_FILENAME
    ]
    skipped = [path for path in all_files if path.suffix.lower() not in TEXT_EXTENSIONS]

    if skipped:
        warnings.append(
            f"Skipped {len(skipped)} non-text files. Convert PDFs/images to markdown or text before updating workspace."
        )

    budget_warning_emitted = False
    for path in supported[:max_files]:
        raw_text, source_type, had_invalid_type = read_typed_source(path)
        raw_text = raw_text.strip()
        if not raw_text:
            warnings.append(f"Skipped empty file: {path.relative_to(raw_dir)}")
            continue
        relative = str(path.relative_to(raw_dir))
        if source_type == SOURCE_TYPE_UNTYPED:
            override = source_type_overrides.get(path.name) or source_type_overrides.get(relative)
            if override and override != SOURCE_TYPE_UNTYPED:
                source_type = override
            elif had_invalid_type:
                warnings.append(
                    f"Source {path.relative_to(raw_dir)} declared an invalid source_type; defaulting to untyped."
                )
            else:
                warnings.append(
                    f"Source {path.relative_to(raw_dir)} has no source_type frontmatter; defaulting to untyped."
                )
        elif had_invalid_type:
            warnings.append(
                f"Source {path.relative_to(raw_dir)} declared an invalid source_type; defaulting to untyped."
            )

        remaining = max_total_chars - total_chars
        if remaining <= 0:
            if not budget_warning_emitted:
                warnings.append("Stopped ingest because max_total_chars budget was reached.")
                budget_warning_emitted = True
            if not include_budget_exhausted:
                break
            trimmed = ""
            truncated = True
        else:
            trimmed = raw_text[: min(max_chars_per_file, remaining)]
            truncated = len(trimmed) < len(raw_text)
            if truncated:
                warnings.append(f"Truncated {path.relative_to(raw_dir)} to {len(trimmed)} characters for note extraction.")

        source_hash = sha256_text(raw_text)

        sources.append(
            {
                "path": str(path.relative_to(raw_dir)),
                "kind": path.suffix.lower().lstrip(".") or "text",
                "source_type": source_type,
                "full_sha256": source_hash,
                "chars_used": len(trimmed),
                "truncated": truncated,
                "content": trimmed,
            }
        )
        total_chars += len(trimmed)

    if len(supported) > max_files:
        warnings.append(f"Read only the first {max_files} supported files out of {len(supported)}.")

    return sources, warnings


def validate_source_note_shape(note: Dict[str, Any]) -> None:
    required_keys = [
        "source_id",
        "source_path",
        "source_kind",
        "source_type",
        "source_summary",
        "immutable_ground_truth",
        "numerical_ranges_and_constraints",
        "potentially_conflicting_assertions",
        "epistemic_voids",
        "candidate_claims_to_test",
    ]
    missing = [key for key in required_keys if key not in note]
    if missing:
        raise ValueError(f"Source note is missing required keys: {', '.join(missing)}")


def build_extract_prompt(project_name: str, source: Dict[str, Any], source_id: str, compiler_date: str) -> str:
    return "\n\n".join(
        [
            load_prompt("extract_source_note.md"),
            f"Project name: {project_name}",
            f"Compiler date: {compiler_date}",
            f"Source id: {source_id}",
            f"Relative source path: {source['path']}",
            f"Source kind: {source['kind']}",
            f"Source type: {source['source_type']}",
            f"Truncated: {'yes' if source['truncated'] else 'no'}",
            "Raw source contents:",
            source["content"],
        ]
    )


def build_merge_prompt(project_name: str, compiler_date: str, notes: List[Dict[str, Any]]) -> str:
    sections = [
        load_prompt("merge_workspace.md"),
        f"Project name: {project_name}",
        f"Compiler date: {compiler_date}",
        "Structured source notes:",
    ]
    for note in notes:
        sections.extend(
            [
                f"### SOURCE NOTE {note.get('source_id', '')}",
                json.dumps(note, indent=2, sort_keys=True),
            ]
        )
    return "\n\n".join(sections)


def next_source_id(existing_ids: List[str]) -> str:
    numeric_ids = []
    for source_id in existing_ids:
        if source_id.startswith("S") and source_id[1:].isdigit():
            numeric_ids.append(int(source_id[1:]))
    nxt = max(numeric_ids, default=0) + 1
    return f"S{nxt:03d}"


def load_source_index(index_path: Path) -> Dict[str, Any]:
    if not index_path.exists():
        return {"sources": []}
    try:
        payload = read_json(index_path)
    except Exception:  # noqa: BLE001
        return {"sources": []}
    if "sources" not in payload or not isinstance(payload["sources"], list):
        return {"sources": []}
    return payload


def assign_source_ids(raw_sources: List[Dict[str, Any]], previous_index: Dict[str, Any]) -> List[Dict[str, Any]]:
    by_path = {entry.get("path"): entry for entry in previous_index.get("sources", []) if entry.get("path")}
    existing_ids = [entry.get("source_id", "") for entry in previous_index.get("sources", [])]
    assigned: List[Dict[str, Any]] = []
    for source in raw_sources:
        prior = by_path.get(source["path"])
        source_id = prior.get("source_id") if prior else next_source_id(existing_ids)
        if source_id not in existing_ids:
            existing_ids.append(source_id)
        enriched = dict(source)
        enriched["source_id"] = source_id
        assigned.append(enriched)
    return assigned


def build_source_index_payload(project_name: str, compiler_date: str, assigned_sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "project": project_name,
        "generated_on": compiler_date,
        "sources": [
            {
                "source_id": source["source_id"],
                "path": source["path"],
                "kind": source["kind"],
                "source_type": source["source_type"],
                "sha256": source["full_sha256"],
                "chars_used": source["chars_used"],
                "truncated": source["truncated"],
                "note_path": f"source_notes/{source['source_id']}.json",
            }
            for source in assigned_sources
        ],
    }


def build_workspace_meta_payload(
    *,
    project_name: str,
    compiler_date: str,
    model_family: str,
    raw_dir: Path,
    workspace_dir: Path,
    assigned_sources: List[Dict[str, Any]],
    changed_sources: int,
    reused_sources: int,
    deleted_sources: List[str],
    warnings: List[str],
    merge_status: str,
    merge_only: bool,
    merge_error: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "project": project_name,
        "generated_on": compiler_date,
        "model_family": model_family,
        "model_id": MODEL_MAP[model_family],
        "raw_dir": repo_display_path(raw_dir),
        "workspace_dir": repo_display_path(workspace_dir),
        "source_count": len(assigned_sources),
        "changed_sources": changed_sources,
        "reused_sources": reused_sources,
        "deleted_sources": deleted_sources,
        "warnings": warnings,
        "merge_status": merge_status,
        "merge_only": merge_only,
        "prompts": {
            "extract_source_note": repo_display_path(PROMPTS_DIR / "extract_source_note.md"),
            "merge_workspace": repo_display_path(PROMPTS_DIR / "merge_workspace.md"),
        },
    }
    if merge_error:
        payload["merge_error"] = merge_error
    return payload


def write_merge_failure_artifact(
    *,
    workspace_dir: Path,
    project_name: str,
    compiler_date: str,
    model_family: str,
    source_count: int,
    changed_sources: int,
    reused_sources: int,
    deleted_sources: List[str],
    warnings: List[str],
    merge_only: bool,
    error: Exception,
) -> Path:
    artifact_path = workspace_dir / "merge_failure.json"
    payload = {
        "project": project_name,
        "generated_on": compiler_date,
        "model_family": model_family,
        "model_id": MODEL_MAP[model_family],
        "source_count": source_count,
        "changed_sources": changed_sources,
        "reused_sources": reused_sources,
        "deleted_sources": deleted_sources,
        "warnings": warnings,
        "merge_only": merge_only,
        "stage": "merge_workspace",
        "error_type": type(error).__name__,
        "error_message": str(error),
        "retry_hint": "Retry later, rerun with --merge-only, or rerun with another model family.",
    }
    write_json(artifact_path, payload)
    return artifact_path


def write_workspace_views(workspace_dir: Path, snapshot: Dict[str, Any]) -> None:
    facts_lines = ["# Facts", ""]
    for item in snapshot.get("immutable_ground_truth", []):
        facts_lines.append(f"- {item.get('statement', '').strip()} [Sources: {', '.join(item.get('source_ids', []))}]")
    if len(facts_lines) == 2:
        facts_lines.append("- None identified.")

    ranges_lines = ["# Ranges And Constraints", ""]
    for item in snapshot.get("numerical_ranges_and_constraints", []):
        ranges_lines.append(
            f"- {item.get('name', '').strip()}: {item.get('value_or_range', '').strip()} {item.get('units', '').strip()} | "
            f"Kind: {item.get('kind', '').strip()} | Sources: {', '.join(item.get('source_ids', []))}"
        )
    if len(ranges_lines) == 2:
        ranges_lines.append("- None identified.")

    contradictions_lines = ["# Contradictions", ""]
    for item in snapshot.get("identified_contradictions", []):
        contradictions_lines.append(f"- {item.get('topic', '').strip()}")
        contradictions_lines.append(f"  - A: {item.get('claim_a', '').strip()} [Sources: {', '.join(item.get('source_ids_a', []))}]")
        contradictions_lines.append(f"  - B: {item.get('claim_b', '').strip()} [Sources: {', '.join(item.get('source_ids_b', []))}]")
    if len(contradictions_lines) == 2:
        contradictions_lines.append("- None identified.")

    voids_lines = ["# Open Questions", ""]
    for item in snapshot.get("epistemic_voids", []):
        voids_lines.append(f"- {item.get('unknown', '').strip()}")
        why = item.get("why_it_matters", "").strip()
        blocking = item.get("blocking", "").strip()
        if why:
            voids_lines.append(f"  - Why it matters: {why}")
        if blocking:
            voids_lines.append(f"  - Blocking effect: {blocking}")
    if len(voids_lines) == 2:
        voids_lines.append("- None identified.")

    claims_lines = ["# Candidate Claims", ""]
    for item in snapshot.get("candidate_claims_to_test", []):
        claims_lines.append(f"- {item.get('claim', '').strip()} [Priority: {item.get('priority', '').strip()}]")
        if item.get("why_testable", "").strip():
            claims_lines.append(f"  - Why testable: {item.get('why_testable', '').strip()}")
    if len(claims_lines) == 2:
        claims_lines.append("- None identified.")

    write_text(workspace_dir / "facts.md", "\n".join(facts_lines).strip() + "\n")
    write_text(workspace_dir / "ranges.md", "\n".join(ranges_lines).strip() + "\n")
    write_text(workspace_dir / "contradictions.md", "\n".join(contradictions_lines).strip() + "\n")
    write_text(workspace_dir / "open_questions.md", "\n".join(voids_lines).strip() + "\n")
    write_text(workspace_dir / "candidate_claims.md", "\n".join(claims_lines).strip() + "\n")


def checkpoint_source_index(
    *,
    project_dir: Path,
    raw_dir: Path,
    workspace_dir: Path,
    model_family: str,
    max_files: int,
    max_chars_per_file: int,
    max_total_chars: int,
    force_reextract: bool = False,
) -> Dict[str, Any]:
    """Write deterministic source-index metadata without calling an LLM."""

    compiler_date = time.strftime("%B %d, %Y")
    raw_sources, warnings = collect_raw_sources(
        raw_dir=raw_dir,
        max_files=max_files,
        max_chars_per_file=max_chars_per_file,
        max_total_chars=max_total_chars,
        include_budget_exhausted=True,
    )
    if not raw_sources:
        raise RuntimeError(f"No supported text-like source files found in {raw_dir}")

    index_path = workspace_dir / "source_index.json"
    previous_index = load_source_index(index_path)
    assigned_sources = assign_source_ids(raw_sources, previous_index)
    previous_by_id = {
        entry.get("source_id"): entry
        for entry in previous_index.get("sources", [])
        if entry.get("source_id")
    }
    current_ids = {source["source_id"] for source in assigned_sources}
    previous_ids = set(previous_by_id)
    deleted_ids = sorted(previous_ids - current_ids)
    changed_sources = 0
    reused_sources = 0
    for source in assigned_sources:
        prior = previous_by_id.get(source["source_id"], {})
        if force_reextract or source["full_sha256"] != prior.get("sha256"):
            changed_sources += 1
        else:
            reused_sources += 1

    source_index_payload = build_source_index_payload(
        project_dir.name,
        compiler_date,
        assigned_sources,
    )
    workspace_meta = build_workspace_meta_payload(
        project_name=project_dir.name,
        compiler_date=compiler_date,
        model_family=model_family,
        raw_dir=raw_dir,
        workspace_dir=workspace_dir,
        assigned_sources=assigned_sources,
        changed_sources=changed_sources,
        reused_sources=reused_sources,
        deleted_sources=deleted_ids,
        warnings=warnings,
        merge_status="index_only",
        merge_only=False,
    )
    write_json(index_path, source_index_payload)
    workspace_meta_path = workspace_dir / "workspace_meta.json"
    write_json(workspace_meta_path, workspace_meta)
    receipt_path = workspace_dir / "source_index_receipt.json"
    receipt = {
        "schema": "ztare-source-index-receipt-v1",
        "status": "indexed",
        "producer": "ztare.workspace.update_workspace::checkpoint_source_index",
        "project": project_dir.name,
        "source_count": len(assigned_sources),
        "changed_sources": changed_sources,
        "reused_sources": reused_sources,
        "deleted_sources": deleted_ids,
        "warnings": warnings,
        "merge_status": "index_only",
        "llm_calls": False,
        "source_index": repo_display_path(index_path),
        "workspace_meta": repo_display_path(workspace_meta_path),
        "source_index_sha256": sha256_file(index_path),
        "sources": [
            {
                "path": source["path"],
                "source_type": source["source_type"],
                "sha256": source["full_sha256"],
                "chars_used": source["chars_used"],
                "truncated": source["truncated"],
            }
            for source in assigned_sources
        ],
        "next_steps": [
            "Run make evidence-prepare before treating compiled evidence as current.",
            "Run ztare autoresearch trace to inspect kernel-entry blockers.",
        ],
    }
    write_json(receipt_path, receipt)
    return {
        "schema": "ztare-workspace-source-index-checkpoint-v1",
        "project": project_dir.name,
        "workspace_dir": str(workspace_dir),
        "source_index": str(index_path),
        "workspace_meta": str(workspace_meta_path),
        "source_index_receipt": str(receipt_path),
        "source_count": len(assigned_sources),
        "changed_sources": changed_sources,
        "reused_sources": reused_sources,
        "deleted_sources": deleted_ids,
        "warnings": warnings,
        "merge_status": "index_only",
        "llm_calls": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Incrementally update a project workspace from raw sources.")
    parser.add_argument("--project", required=True, help="Project name under projects/ or an explicit project path.")
    parser.add_argument("--raw-dir", help="Optional explicit raw source directory. Defaults to <project>/raw.")
    parser.add_argument("--workspace-dir", help="Optional explicit workspace directory. Defaults to <project>/workspace.")
    parser.add_argument("--model", default="gemini", choices=sorted(MODEL_MAP.keys()))
    parser.add_argument("--max-files", type=int, default=25, help="Maximum number of raw files to ingest.")
    parser.add_argument("--max-chars-per-file", type=int, default=12000, help="Maximum characters per file for note extraction.")
    parser.add_argument("--max-total-chars", type=int, default=100000, help="Maximum total character budget across ingested raw files.")
    parser.add_argument("--force-reextract", action="store_true", help="Re-extract all source notes even if hashes are unchanged.")
    parser.add_argument(
        "--llm-timeout-seconds",
        type=positive_int,
        default=DEFAULT_EVIDENCE_LLM_TIMEOUT_SECONDS,
        help="Per-call LLM timeout for note extraction and workspace merge.",
    )
    parser.add_argument(
        "--llm-retries",
        type=positive_int,
        default=DEFAULT_EVIDENCE_LLM_RETRIES,
        help="Per-call retry budget for note extraction and workspace merge.",
    )
    parser.add_argument(
        "--merge-only",
        action="store_true",
        help="Skip source-note extraction and rebuild the merged workspace snapshot from existing source notes only.",
    )
    parser.add_argument(
        "--index-only",
        action="store_true",
        help="Write source_index.json and workspace_meta.json from raw sources without LLM calls.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON summary.")
    parser.add_argument("--debug", action="store_true", help="Print debug details to stderr.")
    args = parser.parse_args()

    global DEBUG
    DEBUG = args.debug

    project_dir = resolve_project_dir(args.project)
    raw_dir = Path(args.raw_dir).resolve() if args.raw_dir else project_dir / "raw"
    workspace_dir = Path(args.workspace_dir).resolve() if args.workspace_dir else project_dir / "workspace"
    if not raw_dir.exists():
        raise FileNotFoundError(f"Raw source directory not found: {raw_dir}")

    if args.index_only:
        checkpoint = checkpoint_source_index(
            project_dir=project_dir,
            raw_dir=raw_dir,
            workspace_dir=workspace_dir,
            model_family=args.model,
            max_files=args.max_files,
            max_chars_per_file=args.max_chars_per_file,
            max_total_chars=args.max_total_chars,
            force_reextract=args.force_reextract,
        )
        if args.json:
            print(json.dumps(checkpoint, indent=2, sort_keys=True))
            return 0
        print(f"Workspace source index: {checkpoint['source_index']}")
        print(f"Workspace metadata: {checkpoint['workspace_meta']}")
        print(f"Source index receipt: {checkpoint['source_index_receipt']}")
        print(f"Source count: {checkpoint['source_count']}")
        print("LLM calls: false")
        if checkpoint["warnings"]:
            print("Warnings:")
            for warning in checkpoint["warnings"]:
                print(f"- {warning}")
        return 0

    compiler_date = time.strftime("%B %d, %Y")
    source_notes_dir = workspace_dir / "source_notes"
    source_notes_dir.mkdir(parents=True, exist_ok=True)

    raw_sources, warnings = collect_raw_sources(
        raw_dir=raw_dir,
        max_files=args.max_files,
        max_chars_per_file=args.max_chars_per_file,
        max_total_chars=args.max_total_chars,
    )
    if not raw_sources:
        raise RuntimeError(f"No supported text-like source files found in {raw_dir}")

    index_path = workspace_dir / "source_index.json"
    previous_index = load_source_index(index_path)
    assigned_sources = assign_source_ids(raw_sources, previous_index)

    previous_by_id = {entry.get("source_id"): entry for entry in previous_index.get("sources", [])}

    notes: List[Dict[str, Any]] = []
    changed_sources = 0
    reused_sources = 0
    missing_note_paths: List[str] = []
    llm: Optional[LLMClient] = None

    for source in assigned_sources:
        source_id = source["source_id"]
        note_path = source_notes_dir / f"{source_id}.json"
        prior_entry = previous_by_id.get(source_id, {})
        prior_hash = prior_entry.get("sha256")
        should_refresh = args.force_reextract or source["full_sha256"] != prior_hash or not note_path.exists()

        if args.merge_only:
            if not note_path.exists():
                missing_note_paths.append(str(note_path))
                continue
            note = read_json(note_path)
            note["source_type"] = source["source_type"]
            validate_source_note_shape(note)
            write_json(note_path, note)
            reused_sources += 1
        elif should_refresh:
            if llm is None:
                llm = LLMClient(
                    args.model,
                    timeout_seconds=args.llm_timeout_seconds,
                    retries=args.llm_retries,
                )
            prompt = build_extract_prompt(project_dir.name, source, source_id, compiler_date)
            dbg(f"Extracting note for {source_id} {source['path']} prompt_chars={len(prompt)}")
            raw_response = llm.call(prompt)
            note = utils.parse_llm_json(raw_response)
            note["source_type"] = source["source_type"]
            validate_source_note_shape(note)
            write_json(note_path, note)
            changed_sources += 1
        else:
            note = read_json(note_path)
            note["source_type"] = source["source_type"]
            validate_source_note_shape(note)
            write_json(note_path, note)
            reused_sources += 1

        notes.append(note)

    if missing_note_paths:
        raise RuntimeError(
            "Merge-only requested but source notes are missing for one or more raw files. "
            "Rerun without --merge-only first.\nMissing notes:\n- " + "\n- ".join(missing_note_paths)
        )

    current_ids = {source["source_id"] for source in assigned_sources}
    previous_ids = {entry.get("source_id") for entry in previous_index.get("sources", []) if entry.get("source_id")}
    deleted_ids = sorted(previous_ids - current_ids)
    for source_id in deleted_ids:
        stale_path = source_notes_dir / f"{source_id}.json"
        if stale_path.exists():
            stale_path.unlink()

    source_index_payload = build_source_index_payload(project_dir.name, compiler_date, assigned_sources)
    pending_workspace_meta = build_workspace_meta_payload(
        project_name=project_dir.name,
        compiler_date=compiler_date,
        model_family=args.model,
        raw_dir=raw_dir,
        workspace_dir=workspace_dir,
        assigned_sources=assigned_sources,
        changed_sources=changed_sources,
        reused_sources=reused_sources,
        deleted_sources=deleted_ids,
        warnings=warnings,
        merge_status="pending",
        merge_only=args.merge_only,
    )
    write_json(index_path, source_index_payload)
    write_json(workspace_dir / "workspace_meta.json", pending_workspace_meta)
    dbg("Checkpointed source index and workspace meta before merge.")

    merge_prompt = build_merge_prompt(project_dir.name, compiler_date, notes)
    dbg(f"Merging workspace notes count={len(notes)} prompt_chars={len(merge_prompt)}")
    if llm is None:
        llm = LLMClient(
            args.model,
            timeout_seconds=args.llm_timeout_seconds,
            retries=args.llm_retries,
        )
    try:
        merged_snapshot = utils.parse_llm_json(llm.call(merge_prompt))
        validate_packet_shape(merged_snapshot)
        source_type_by_id = {source["source_id"]: source["source_type"] for source in assigned_sources}
        annotate_provenance_source_types(merged_snapshot, source_type_by_id)
        warnings.extend(filter_packet_by_source_types(merged_snapshot, source_type_by_id))
    except Exception as exc:  # noqa: BLE001
        failure_artifact = write_merge_failure_artifact(
            workspace_dir=workspace_dir,
            project_name=project_dir.name,
            compiler_date=compiler_date,
            model_family=args.model,
            source_count=len(assigned_sources),
            changed_sources=changed_sources,
            reused_sources=reused_sources,
            deleted_sources=deleted_ids,
            warnings=warnings,
            merge_only=args.merge_only,
            error=exc,
        )
        failed_workspace_meta = build_workspace_meta_payload(
            project_name=project_dir.name,
            compiler_date=compiler_date,
            model_family=args.model,
            raw_dir=raw_dir,
            workspace_dir=workspace_dir,
            assigned_sources=assigned_sources,
            changed_sources=changed_sources,
            reused_sources=reused_sources,
            deleted_sources=deleted_ids,
            warnings=warnings,
            merge_status="failed",
            merge_only=args.merge_only,
            merge_error={"type": type(exc).__name__, "message": str(exc)},
        )
        write_json(workspace_dir / "workspace_meta.json", failed_workspace_meta)
        print("ERROR: Workspace merge failed after checkpointing source notes and source index.", file=sys.stderr)
        print(f"Merge failure artifact: {failure_artifact}", file=sys.stderr)
        print("Retry options:", file=sys.stderr)
        print("- rerun the same command later", file=sys.stderr)
        print("- rerun with --merge-only to reuse extracted source notes", file=sys.stderr)
        print("- rerun with --model claude if another provider is available", file=sys.stderr)
        return 2

    success_workspace_meta = build_workspace_meta_payload(
        project_name=project_dir.name,
        compiler_date=compiler_date,
        model_family=args.model,
        raw_dir=raw_dir,
        workspace_dir=workspace_dir,
        assigned_sources=assigned_sources,
        changed_sources=changed_sources,
        reused_sources=reused_sources,
        deleted_sources=deleted_ids,
        warnings=warnings,
        merge_status="success",
        merge_only=args.merge_only,
    )

    write_json(workspace_dir / "workspace_snapshot.json", merged_snapshot)
    write_json(workspace_dir / "workspace_meta.json", success_workspace_meta)
    merge_failure_path = workspace_dir / "merge_failure.json"
    if merge_failure_path.exists():
        merge_failure_path.unlink()
    write_workspace_views(workspace_dir, merged_snapshot)

    print(f"Workspace: {workspace_dir}")
    print(f"Snapshot: {workspace_dir / 'workspace_snapshot.json'}")
    print(f"Source index: {index_path}")
    print(f"Changed sources: {changed_sources}")
    print(f"Reused sources: {reused_sources}")
    if deleted_ids:
        print(f"Deleted sources: {', '.join(deleted_ids)}")
    if warnings:
        print(f"Warnings: {len(warnings)}")
        for warning in warnings:
            print(f"- {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
