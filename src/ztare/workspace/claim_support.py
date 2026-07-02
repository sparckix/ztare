"""Audit compiled-evidence claim support against source rows."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

from ztare.common.paths import PROJECTS_DIR
from ztare.workspace.compile_evidence import (
    SOURCE_TYPE_EVIDENCE,
    SOURCE_TYPE_QUESTION,
    SOURCE_TYPE_SEED,
    read_typed_source,
)

CLAIM_SUPPORT_SCHEMA = "ztare-claim-support-audit-v1"
SUPPORTED_PACKET_FIELDS = {
    "immutable_ground_truth": "statement",
    "numerical_ranges_and_constraints": "name",
    "candidate_claims_to_test": "claim",
}
SOURCE_CONTEXT_PREVIEW_LINES = 8
SOURCE_CONTEXT_PREVIEW_CHARS = 800


def _identity(value: Any) -> str:
    return str(value or "")


def display_value(value: Any) -> str:
    text = str(value or "").strip()
    return re.sub(r"[_-]+", " ", text).strip().capitalize() if text else ""


def claim_support_row_is_weak(row: dict[str, Any]) -> bool:
    text = f"{row.get('support_status') or row.get('status') or ''} {row.get('issue') or row.get('reason') or ''}"
    return bool(re.search(r"weak|missing|unsourced|blocked|unsupported", text, flags=re.IGNORECASE))


def compact_claim_support_row(
    row: dict[str, Any],
    *,
    path_display: Callable[[Any], str] = _identity,
) -> dict[str, Any]:
    source_paths = row.get("source_paths") if isinstance(row.get("source_paths"), list) else []
    source_ids = row.get("source_ids") if isinstance(row.get("source_ids"), list) else []
    return {
        "claim_id": str(row.get("claim_id") or row.get("id") or ""),
        "claim": str(row.get("claim") or "")[:600],
        "field": str(row.get("field") or ""),
        "status": str(row.get("status") or ""),
        "support_status": str(row.get("support_status") or row.get("status") or ""),
        "source_id": str(row.get("source_id") or ""),
        "source_ids": [str(item) for item in source_ids if item],
        "source_paths": [path_display(item) for item in source_paths if item],
        "support_level": str(row.get("support_level") or ""),
        "issue": str(row.get("issue") or row.get("reason") or ""),
    }


def claim_card_payload(
    row: dict[str, Any],
    index: int,
    *,
    path_display: Callable[[Any], str] = _identity,
    value_display: Callable[[Any], str] = display_value,
) -> dict[str, Any]:
    weak = claim_support_row_is_weak(row)
    status = str(row.get("support_status") or row.get("status") or "")
    source_paths = row.get("source_paths") if isinstance(row.get("source_paths"), list) else []
    source_ids = row.get("source_ids") if isinstance(row.get("source_ids"), list) else []
    return {
        "card_id": str(row.get("claim_id") or f"claim_card_{index}"),
        "claim": str(row.get("claim") or "")[:600],
        "kind": "weak_or_open" if weak else "supported",
        "status": status,
        "display_status": "Needs support" if weak else "Supported",
        "evidence_level": value_display(row.get("support_level") or status or ("open" if weak else "supported")),
        "source_ids": [str(item) for item in source_ids if item],
        "source_paths": [path_display(item) for item in source_paths if item],
        "issue": str(row.get("issue") or "")[:300],
        "next_action": "Add or justify source support." if weak else "Preview the backing source files.",
    }


def claim_card_audit(thesis_support: dict[str, Any] | None) -> dict[str, Any]:
    support = thesis_support if isinstance(thesis_support, dict) else {}
    cards = [row for row in support.get("claim_cards") or [] if isinstance(row, dict)]
    try:
        target = min(int(support.get("claim_count") or 0), 8)
    except (TypeError, ValueError):
        target = 0
    usable = [
        row
        for row in cards
        if str(row.get("claim") or "").strip()
        and str(row.get("kind") or "").strip()
        and (
            [path for path in row.get("source_paths") or [] if path]
            or str(row.get("issue") or row.get("next_action") or "").strip()
        )
    ]
    ok = target == 0 or (len(cards) >= target and len(usable) == len(cards))
    return {
        "ok": ok,
        "target": target,
        "card_count": len(cards),
        "usable_count": len(usable),
        "detail": "Thesis support exposes inspectable claim cards with source files or a next action."
        if ok
        else f"Thesis support has {target} claim(s), but only {len(cards)} usable claim card(s).",
    }


def compact_thesis_support_payload(
    claim_support: dict[str, Any] | None,
    *,
    path_display: Callable[[Any], str] = _identity,
    value_display: Callable[[Any], str] = display_value,
) -> dict[str, Any]:
    support = claim_support if isinstance(claim_support, dict) else {}
    rows = support.get("rows") if isinstance(support.get("rows"), list) else []
    sources = support.get("source_context") if isinstance(support.get("source_context"), list) else []

    def safe_int(value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    def compact_point(row: dict[str, Any]) -> dict[str, Any]:
        return {
            "claim_id": str(row.get("claim_id") or ""),
            "claim": str(row.get("claim") or "")[:300],
            "status": str(row.get("support_status") or row.get("status") or ""),
            "source_paths": [path_display(path) for path in row.get("source_paths") or [] if path][:4],
            "issue": str(row.get("issue") or "")[:300],
        }

    supported = [row for row in rows if isinstance(row, dict) and not claim_support_row_is_weak(row)]
    weak_or_open = [row for row in rows if isinstance(row, dict) and claim_support_row_is_weak(row)]
    claim_cards = [
        claim_card_payload(row, index, path_display=path_display, value_display=value_display)
        for index, row in enumerate([*supported, *weak_or_open], start=1)
    ]
    backing_files = [
        str(path)
        for path in [
            support.get("evidence_support_file_path"),
            support.get("source_index_path"),
            *[source.get("path") for source in sources[:6] if isinstance(source, dict)],
        ]
        if path
    ]
    status = str(support.get("status") or "not loaded")
    return {
        "schema": "ztare-project-thesis-support-v1",
        "project": str(support.get("project") or ""),
        "status": status,
        "display_status": str(support.get("display_status") or value_display(status)),
        "claim_count": safe_int(support.get("claim_count")),
        "supported_count": len(supported),
        "weak_or_open_count": len(weak_or_open),
        "source_count": len(sources),
        "evidence_support_file_path": str(support.get("evidence_support_file_path") or ""),
        "source_index_path": str(support.get("source_index_path") or ""),
        "supported_points": [compact_point(row) for row in supported[:4]],
        "weak_or_open_points": [compact_point(row) for row in weak_or_open[:4]],
        "claim_cards": claim_cards[:8],
        "backing_files": sorted({path for path in backing_files})[:10],
    }


def read_json(path: Path) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except Exception as exc:  # noqa: BLE001
        return {"_read_error": f"{type(exc).__name__}: {exc}"}
    return raw if isinstance(raw, dict) else {"_read_error": "expected JSON object"}


def resolve_project_dir(project: str) -> Path:
    candidate = Path(project)
    if candidate.exists():
        return candidate.resolve()
    fallback = PROJECTS_DIR / project
    if fallback.exists():
        return fallback.resolve()
    raise SystemExit(f"project not found: {project}")


def _source_rows(project_dir: Path) -> dict[str, dict[str, Any]]:
    source_index = read_json(project_dir / "workspace" / "source_index.json")
    rows = source_index.get("sources")
    if not isinstance(rows, list):
        rows = []
    by_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        source_id = str(row.get("source_id") or "").strip()
        if source_id:
            by_id[source_id] = row
    return by_id


def _sha256_text(text: str) -> str:
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _raw_relative_path(source: dict[str, Any], *, project_dir: Path) -> str:
    raw = str(source.get("relative_raw_path") or source.get("path") or "").strip()
    raw = raw.replace("\\", "/")
    project_raw_prefix = f"projects/{project_dir.name}/raw/"
    if raw.startswith(project_raw_prefix):
        raw = raw[len(project_raw_prefix):]
    if raw.startswith("raw/"):
        raw = raw[len("raw/"):]
    return raw


def _raw_source_path(source: dict[str, Any], *, project_dir: Path) -> Path | None:
    raw = _raw_relative_path(source, project_dir=project_dir)
    if not raw or "://" in raw:
        return None
    candidate = project_dir / "raw" / raw
    try:
        candidate.resolve().relative_to((project_dir / "raw").resolve())
    except ValueError:
        return None
    return candidate


def _preview_lines(text: str) -> dict[str, Any]:
    lines = text.splitlines()
    selected = lines[:SOURCE_CONTEXT_PREVIEW_LINES]
    preview = "\n".join(selected)
    truncated = len(lines) > SOURCE_CONTEXT_PREVIEW_LINES or len(preview) > SOURCE_CONTEXT_PREVIEW_CHARS
    if len(preview) > SOURCE_CONTEXT_PREVIEW_CHARS:
        preview = preview[:SOURCE_CONTEXT_PREVIEW_CHARS].rstrip()
    return {
        "line_start": 1 if lines else None,
        "line_end": len(selected) if selected else None,
        "text": preview,
        "truncated": truncated,
    }


def _source_context_row(
    source_id: str,
    source: dict[str, Any],
    *,
    project_dir: Path,
) -> dict[str, Any]:
    relative_raw_path = _raw_relative_path(source, project_dir=project_dir)
    path = _raw_source_path(source, project_dir=project_dir)
    context: dict[str, Any] = {
        "source_id": source_id,
        "source_type": str(source.get("source_type") or "").strip() or "untyped",
        "relative_raw_path": relative_raw_path,
        "path": str(path) if path is not None else "",
        "exists": bool(path and path.is_file()),
        "index_sha256": str(source.get("sha256") or source.get("full_sha256") or "").strip(),
        "current_sha256": None,
        "hash_matches_index": None,
        "line_count": None,
        "preview": None,
        "status": "missing_source_file",
    }
    if path is None:
        context["status"] = "unsafe_or_unresolved_path"
        return context
    if not path.is_file():
        return context
    try:
        text, _source_type, _had_invalid_type = read_typed_source(path)
    except Exception as exc:  # noqa: BLE001
        context["status"] = f"read_error:{type(exc).__name__}"
        return context
    text = text.strip()
    current_sha = _sha256_text(text)
    index_sha = context["index_sha256"]
    context.update(
        {
            "current_sha256": current_sha,
            "hash_matches_index": bool(index_sha and index_sha == current_sha),
            "line_count": len(text.splitlines()),
            "preview": _preview_lines(text),
            "status": "verified" if index_sha and index_sha == current_sha else "hash_mismatch",
        }
    )
    if not index_sha:
        context["status"] = "unverified_missing_index_hash"
    return context


def _source_context(
    source_by_id: dict[str, dict[str, Any]],
    *,
    project_dir: Path,
) -> dict[str, dict[str, Any]]:
    return {
        source_id: _source_context_row(source_id, source, project_dir=project_dir)
        for source_id, source in sorted(source_by_id.items())
    }


def _source_ids(row: dict[str, Any]) -> list[str]:
    raw = row.get("source_ids")
    if not isinstance(raw, list):
        return []
    return [str(item).strip() for item in raw if str(item).strip()]


def _claim_text(field: str, row: dict[str, Any]) -> str:
    key = SUPPORTED_PACKET_FIELDS[field]
    if field == "numerical_ranges_and_constraints":
        name = str(row.get("name") or "").strip()
        value = str(row.get("value_or_range") or "").strip()
        return f"{name}: {value}".strip(": ")
    return str(row.get(key) or "").strip()


def _claim_rows(packet: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for field in SUPPORTED_PACKET_FIELDS:
        values = packet.get(field)
        if not isinstance(values, list):
            continue
        for index, row in enumerate(values, start=1):
            if not isinstance(row, dict):
                continue
            rows.append(
                {
                    "claim_id": f"{field}:{index}",
                    "field": field,
                    "claim": _claim_text(field, row),
                    "source_ids": _source_ids(row),
                    "raw": row,
                }
            )
    return rows


def _classify_claim(
    row: dict[str, Any],
    *,
    source_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    source_ids = list(row.get("source_ids") or [])
    missing = [source_id for source_id in source_ids if source_id not in source_by_id]
    source_rows = [source_by_id[source_id] for source_id in source_ids if source_id in source_by_id]
    source_types = [
        str(source.get("source_type") or "").strip() or "untyped"
        for source in source_rows
    ]
    evidence_ids = [
        source_id
        for source_id in source_ids
        if source_by_id.get(source_id, {}).get("source_type") == SOURCE_TYPE_EVIDENCE
    ]
    local_or_seed_ids = [
        source_id
        for source_id in source_ids
        if source_by_id.get(source_id, {}).get("source_type")
        in {SOURCE_TYPE_SEED, SOURCE_TYPE_QUESTION}
    ]

    if not source_ids:
        status = "unsupported_no_sources"
        reason = "claim row has no source_ids"
    elif missing:
        status = "unsupported_missing_sources"
        reason = "claim row references source ids absent from workspace/source_index.json"
    elif not evidence_ids:
        status = "local_or_seed_support"
        reason = "claim is grounded only in seed/question/local-planning source rows"
    elif len(evidence_ids) == 1 and not local_or_seed_ids:
        status = "direct_source_support"
        reason = "claim is bound to one source_evidence row"
    elif len(evidence_ids) > 1 and not local_or_seed_ids:
        status = "synthesized_across_sources"
        reason = "claim is bound to multiple source_evidence rows"
    else:
        status = "mixed_source_support"
        reason = "claim mixes source_evidence rows with seed/question rows"

    return {
        "claim_id": row.get("claim_id"),
        "field": row.get("field"),
        "claim": row.get("claim"),
        "support_status": status,
        "reason": reason,
        "source_ids": source_ids,
        "missing_source_ids": missing,
        "source_types": source_types,
        "source_paths": [
            str(source.get("relative_raw_path") or source.get("path") or "")
            for source in source_rows
        ],
    }


def _evidence_readiness_status(
    *,
    evidence_readiness: dict[str, Any] | None,
) -> str:
    if not isinstance(evidence_readiness, dict):
        return "not_checked"
    status = str(evidence_readiness.get("status") or "").strip()
    return status or "not_checked"


def reliability_verdict(
    status_counts: dict[str, int], claim_count: int
) -> dict[str, Any]:
    """A substantive "can I rely on this" verdict from the per-claim support mix.

    This is the master judgment (CLI owns it; the workbench only renders it) — it replaces the
    coarse `report_status` -> "Almost there" mapping that gave the reader no affordance. The tier
    answers the eigenquestion; the breakdown gives the WHY (how many claims are directly sourced
    vs cross-source inference vs unsupported).
    """
    def c(key: str) -> int:
        return int(status_counts.get(key, 0) or 0)

    direct = c("direct_source_support")
    synth = c("synthesized_across_sources") + c("mixed_source_support")
    seed = c("local_or_seed_support")
    unsupported = c("unsupported_no_sources") + c("unsupported_missing_sources")
    total = int(claim_count or 0)

    breakdown: list[dict[str, Any]] = []
    if direct:
        breakdown.append({"count": direct, "label": "directly sourced"})
    if synth:
        breakdown.append({"count": synth, "label": "synthesized across sources"})
    if seed:
        breakdown.append({"count": seed, "label": "on local or seed evidence"})
    breakdown.append({"count": unsupported, "label": "unsupported"})

    if total == 0:
        tier, headline = "not_checked", "Not checked yet"
    elif unsupported > 0:
        tier, headline = "do_not_rely", "Don't rely on it yet"
    elif synth + seed == 0:
        tier, headline = "rely", "Holds up — every claim directly sourced"
    else:
        tier, headline = "verify_inference", "Usable — verify the inferences"

    if total == 0:
        summary = "Run a backing check to see how each claim is supported."
    else:
        parts = [f"{b['count']} {b['label']}" if b["count"] else "none unsupported" for b in breakdown]
        summary = f"{' · '.join(parts)} of {total}"

    return {
        "tier": tier,
        "headline": headline,
        "summary": summary,
        "total_claims": total,
        "breakdown": breakdown,
        "directly_sourced": direct,
        "synthesized": synth,
        "seed_support": seed,
        "unsupported": unsupported,
    }


def build_claim_support_audit(
    project_dir: Path,
    *,
    evidence_readiness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    packet_path = project_dir / "compiled_evidence_packet.json"
    packet = read_json(packet_path)
    source_by_id = _source_rows(project_dir)
    source_context = _source_context(source_by_id, project_dir=project_dir)
    errors: list[str] = []
    if packet.get("_read_error"):
        errors.append(f"compiled_evidence_packet.json: {packet['_read_error']}")
    if not packet_path.exists():
        errors.append(f"missing compiled evidence packet: {packet_path}")

    claim_rows = _claim_rows(packet)
    rows = [
        _classify_claim(row, source_by_id=source_by_id)
        for row in claim_rows
    ]
    status_counts: dict[str, int] = {}
    for row in rows:
        status = str(row.get("support_status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    weak_statuses = {
        "unsupported_no_sources",
        "unsupported_missing_sources",
        "local_or_seed_support",
        "mixed_source_support",
    }
    weak_count = sum(status_counts.get(status, 0) for status in weak_statuses)
    source_context_status_counts: dict[str, int] = {}
    for context in source_context.values():
        status = str(context.get("status") or "unknown")
        source_context_status_counts[status] = source_context_status_counts.get(status, 0) + 1
    source_context_blocked_count = sum(
        count
        for status, count in source_context_status_counts.items()
        if status != "verified"
    )
    readiness_status = _evidence_readiness_status(evidence_readiness=evidence_readiness)
    audit_status = "ready"
    if errors:
        audit_status = "missing_packet"
    elif readiness_status not in {"fresh", "not_checked"}:
        audit_status = "blocked_by_evidence_readiness"
    elif source_context_blocked_count:
        audit_status = "blocked_by_source_context"
    elif weak_count:
        audit_status = "has_demotions"

    return {
        "schema": CLAIM_SUPPORT_SCHEMA,
        "project": project_dir.name,
        "status": audit_status,
        "ok": not errors and source_context_blocked_count == 0,
        "packet_path": str(packet_path),
        "source_index_path": str(project_dir / "workspace" / "source_index.json"),
        "evidence_readiness_status": readiness_status,
        "claim_count": len(rows),
        "status_counts": status_counts,
        "reliability": reliability_verdict(status_counts, len(rows)),
        "weak_or_unsourced_count": weak_count,
        "source_context_status_counts": source_context_status_counts,
        "source_context_blocked_count": source_context_blocked_count,
        "source_context": source_context,
        "rows": rows,
        "errors": errors,
    }


def render_text(report: dict[str, Any]) -> str:
    reliability = report.get("reliability") or {}
    lines = [
        f"Claim support: {report.get('project')}",
        f"Status: {report.get('status')}",
        f"Verdict: {reliability.get('headline', 'n/a')} — {reliability.get('summary', '')}".rstrip(" —"),
        f"Claims: {report.get('claim_count', 0)}",
        f"Evidence readiness: {report.get('evidence_readiness_status')}",
    ]
    counts = report.get("status_counts") or {}
    if counts:
        lines.append("Status counts:")
        for key in sorted(counts):
            lines.append(f"- {key}: {counts[key]}")
    source_context_counts = report.get("source_context_status_counts") or {}
    if source_context_counts:
        lines.append("Source context:")
        for key in sorted(source_context_counts):
            lines.append(f"- {key}: {source_context_counts[key]}")
    errors = report.get("errors") or []
    if errors:
        lines.extend(["", "Errors:"])
        lines.extend(f"- {error}" for error in errors)
    rows = report.get("rows") or []
    if rows:
        lines.extend(["", "Rows:"])
        for row in rows:
            lines.append(
                f"- {row.get('claim_id')}: {row.get('support_status')} "
                f"[sources={', '.join(row.get('source_ids') or []) or 'none'}] "
                f"{row.get('claim')}"
            )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Classify compiled-evidence claim rows by source support. "
            "This is deterministic and does not call a model."
        )
    )
    parser.add_argument("--project", required=True, help="Project name or explicit project path.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    args = parser.parse_args(argv)

    project_dir = resolve_project_dir(args.project)
    report = build_claim_support_audit(project_dir)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(render_text(report), end="")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
