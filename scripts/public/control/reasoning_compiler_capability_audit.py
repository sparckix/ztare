#!/usr/bin/env python3
"""Audit the public reasoning-compiler capability map."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
DEFAULT_MAP = REPO / "docs/evidence_atlas/reasoning_compiler_capabilities.json"
DEFAULT_RESEARCH_ANCHORS = REPO / "docs/evidence_atlas/research_anchors.json"

REQUIRED_ROW_FIELDS = (
    "id",
    "label",
    "user_problem",
    "input_object",
    "check_or_transform",
    "output_object",
    "falsifier",
    "workbench_requirement",
    "user_visible_proof",
    "current_boundary",
    "workbench_surface",
)

REQUIRED_ARRAY_FIELDS = (
    "research_anchor_ids",
    "evidence_refs",
    "runnable_anchors",
)

WORKBENCH_SURFACES: dict[str, set[str]] = {
    "ZTARE Projects": {"Current project", "Projects", "Connect project", "Files", "Plugins", "Settings"},
    "Project": {"Overview", "Charter", "Thesis", "Evidence summary"},
    "Files": {"Prepare files", "Project brief", "Add file", "Edit file"},
    "Run": {"Ready to run", "Scoring guide", "Run settings", "Check readiness", "Start run", "Fix warnings"},
    "LeanMill": {"Start", "Draft target", "Proof files", "History"},
    "Review": {"Things to review", "Save review", "Save next step", "Saved history"},
    "Report": {"Report readiness", "Report inputs", "Project file"},
}

ALLOWED_NON_WORKBENCH_SURFACES = {
    "action-intelligence read models",
    "file viewer",
    "Kernel/read-model backlog",
    "Public evidence atlas",
    "release gates",
    "saved project file",
}

FORBIDDEN_SURFACE_TERMS = (
    "Autoresearch Projects",
    "Sources & evidence",
    "All projects",
    "Project library",
    "Evidence map",
    "Prepare sources",
    "Add source",
    "Edit source",
    "Open issues",
    "Support check",
    "Review points",
    "Receipts",
    "Run / Preflight",
    "LeanMill / Overview",
    "LeanMill / Blueprint",
    "LeanMill / Formalizations",
    "LeanMill / Saved history",
)

FORBIDDEN_PUBLIC_REF_PARTS = (
    "internal/",
    "research_areas/private/",
)


def _repo_relative(path: Path) -> str:
    return str(path.relative_to(REPO))


def _load_json(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, [f"missing map: {_repo_relative(path)}"]
    except json.JSONDecodeError as exc:
        return None, [f"invalid json: {_repo_relative(path)}:{exc.lineno}:{exc.colno}: {exc.msg}"]
    if not isinstance(payload, dict):
        return None, [f"top-level payload must be an object: {_repo_relative(path)}"]
    return payload, []


def _audit_research_anchors(path: Path = DEFAULT_RESEARCH_ANCHORS) -> tuple[set[str], dict[str, Any]]:
    payload, findings = _load_json(path)
    if payload is None:
        return set(), {
            "ok": False,
            "path": _repo_relative(path),
            "anchor_count": 0,
            "finding_count": len(findings),
            "findings": findings,
        }
    rows = payload.get("anchors")
    if payload.get("schema_version") != 1:
        findings.append("schema_version must be 1")
    if not str(payload.get("purpose") or "").strip():
        findings.append("missing purpose")
    coverage_status = str(payload.get("coverage_status") or "").strip()
    if coverage_status not in {"in_progress", "complete"}:
        findings.append("coverage_status must be one of: in_progress, complete")
    missing_backlog = payload.get("known_missing_anchor_backlog")
    missing_backlog_rows = (
        [str(value).strip() for value in missing_backlog if str(value or "").strip()]
        if isinstance(missing_backlog, list)
        else []
    )
    if coverage_status == "in_progress" and not missing_backlog_rows:
        findings.append("in-progress research anchor registry must name known missing-anchor backlog")
    if not isinstance(rows, list) or not rows:
        findings.append("anchors must be a non-empty list")
        rows = []
    ids: set[str] = set()
    seen_ids: set[str] = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            findings.append(f"anchor {index} must be an object")
            continue
        row_id = str(row.get("id") or "").strip()
        if not row_id:
            findings.append(f"anchor {index} missing id")
        elif row_id in seen_ids:
            findings.append(f"duplicate research anchor id: {row_id}")
        else:
            ids.add(row_id)
            seen_ids.add(row_id)
        for field in ("label", "design_lesson", "ztare_implication"):
            if not str(row.get(field) or "").strip():
                findings.append(f"anchor {row_id or index} missing {field}")
        sources = row.get("sources")
        if not isinstance(sources, list) or not sources:
            findings.append(f"anchor {row_id or index} missing sources")
            continue
        for source_index, source in enumerate(sources, start=1):
            if not isinstance(source, dict):
                findings.append(f"anchor {row_id or index} source {source_index} must be an object")
                continue
            for field in ("title", "url"):
                if not str(source.get(field) or "").strip():
                    findings.append(f"anchor {row_id or index} source {source_index} missing {field}")
            year = source.get("year")
            if not isinstance(year, int) or year < 1900:
                findings.append(f"anchor {row_id or index} source {source_index} has invalid year")
            url = str(source.get("url") or "")
            if url and not url.startswith("https://"):
                findings.append(f"anchor {row_id or index} source {source_index} must use https url")
    return ids, {
        "ok": not findings,
        "path": _repo_relative(path),
        "anchor_count": len(rows),
        "coverage_status": coverage_status,
        "missing_backlog_count": len(missing_backlog_rows),
        "finding_count": len(findings),
        "findings": findings,
    }


def _resolve_ref(ref: str) -> tuple[Path | None, str | None]:
    target = str(ref or "").strip().split("#", 1)[0]
    if not target:
        return None, "empty evidence ref"
    if "://" in target or target.startswith("mailto:"):
        return None, f"external refs are not accepted in this public map: {ref}"
    if target.startswith("/") or ".." in Path(target).parts:
        return None, f"evidence ref must stay repo-relative: {ref}"
    if any(part in target for part in FORBIDDEN_PUBLIC_REF_PARTS):
        return None, f"public map cannot cite private/internal ref: {ref}"
    resolved = (REPO / target).resolve()
    try:
        resolved.relative_to(REPO)
    except ValueError:
        return None, f"evidence ref escapes repo: {ref}"
    return resolved, None


def _audit_workbench_surface(value: Any) -> list[str]:
    text = str(value or "").strip()
    findings: list[str] = []
    if not text:
        return ["missing workbench_surface"]
    if "Intake" in text or "Add intake" in text:
        findings.append("workbench_surface uses old UI wording; use Project brief or Connect project")
    for term in FORBIDDEN_SURFACE_TERMS:
        if term in text:
            findings.append(f"workbench_surface uses old UI wording: {term}")
    for chunk in [part.strip() for part in text.split(";") if part.strip()]:
        if " / " not in chunk:
            if chunk not in ALLOWED_NON_WORKBENCH_SURFACES:
                findings.append(f"unknown non-workbench surface: {chunk}")
            continue
        workspace, subsection = [part.strip() for part in chunk.split(" / ", 1)]
        if workspace not in WORKBENCH_SURFACES:
            findings.append(f"unknown workbench section: {workspace}")
            continue
        if subsection not in WORKBENCH_SURFACES[workspace]:
            findings.append(f"unknown workbench subsection for {workspace}: {subsection}")
    return findings


def _uses_workbench_surface(value: Any) -> bool:
    text = str(value or "").strip()
    return any(f"{workspace} / " in text for workspace in WORKBENCH_SURFACES)


def _audit_row(row: Any, index: int, seen_ids: set[str], research_anchor_ids: set[str]) -> dict[str, Any]:
    if not isinstance(row, dict):
        return {
            "index": index,
            "id": f"row_{index}",
            "ok": False,
            "findings": ["capability row must be an object"],
        }
    row_id = str(row.get("id") or f"row_{index}")
    findings: list[str] = []
    for field in REQUIRED_ROW_FIELDS:
        if not str(row.get(field) or "").strip():
            findings.append(f"missing {field}")
    for field in REQUIRED_ARRAY_FIELDS:
        values = row.get(field)
        if not isinstance(values, list) or not [value for value in values if str(value or "").strip()]:
            findings.append(f"missing {field}")
    if row_id in seen_ids:
        findings.append(f"duplicate id: {row_id}")
    seen_ids.add(row_id)

    label = str(row.get("label") or "")
    if label and label == row_id:
        findings.append("label must be human-readable, not just the id")
    if label and "_" in label:
        findings.append("label should use plain words, not snake_case")
    workbench_requirement = str(row.get("workbench_requirement") or "").strip()
    if workbench_requirement and "must" not in workbench_requirement.lower():
        findings.append("workbench_requirement must state a user-visible obligation with 'must'")
    user_visible_proof = str(row.get("user_visible_proof") or "").strip()
    if user_visible_proof and not any(
        marker in user_visible_proof
        for marker in ("Open ", "Run ", "`ztare", "`make", "`python", ".py ")
    ):
        findings.append("user_visible_proof must name an inspectable Workbench action or runnable command")
    findings.extend(_audit_workbench_surface(row.get("workbench_surface")))

    row_research_ids = [
        str(value).strip()
        for value in row.get("research_anchor_ids") or []
        if str(value or "").strip()
    ]
    if len(row_research_ids) < 2:
        findings.append("capability needs at least two research anchors")
    for anchor_id in row_research_ids:
        if anchor_id not in research_anchor_ids:
            findings.append(f"unknown research anchor id: {anchor_id}")
    evidence_refs = [str(value).strip() for value in row.get("evidence_refs") or [] if str(value or "").strip()]
    existing_refs = 0
    for ref in evidence_refs:
        resolved, error = _resolve_ref(ref)
        if error:
            findings.append(error)
            continue
        if resolved is None:
            findings.append(f"unresolved evidence ref: {ref}")
            continue
        if not resolved.exists():
            findings.append(f"missing evidence ref: {ref}")
            continue
        existing_refs += 1
    if evidence_refs and existing_refs == 0:
        findings.append("no evidence refs exist")

    runnable_anchors = [
        str(value).strip()
        for value in row.get("runnable_anchors") or []
        if str(value or "").strip()
    ]
    if not runnable_anchors and existing_refs < 2:
        findings.append("needs at least one runnable anchor or two existing artifacts")

    return {
        "index": index,
        "id": row_id,
        "label": label,
        "ok": not findings,
        "finding_count": len(findings),
        "findings": findings,
        "evidence_ref_count": len(evidence_refs),
        "existing_evidence_ref_count": existing_refs,
        "research_anchor_count": len(row_research_ids),
        "runnable_anchor_count": len(runnable_anchors),
    }


def audit(path: Path = DEFAULT_MAP, research_anchors_path: Path = DEFAULT_RESEARCH_ANCHORS) -> dict[str, Any]:
    research_anchor_ids, research_report = _audit_research_anchors(research_anchors_path)
    payload, load_findings = _load_json(path)
    if payload is None:
        return {
            "ok": False,
            "path": _repo_relative(path),
            "capability_count": 0,
            "finding_count": len(load_findings),
            "findings": load_findings,
            "research_anchors": research_report,
            "rows": [],
        }
    rows = payload.get("capabilities")
    findings = list(load_findings)
    if payload.get("schema_version") != 1:
        findings.append("schema_version must be 1")
    if not str(payload.get("purpose") or "").strip():
        findings.append("missing purpose")
    if not isinstance(rows, list) or not rows:
        findings.append("capabilities must be a non-empty list")
        rows = []

    seen_ids: set[str] = set()
    row_results = [
        _audit_row(row, index, seen_ids, research_anchor_ids)
        for index, row in enumerate(rows, start=1)
    ]
    failing_rows = [row for row in row_results if not row["ok"]]
    finding_count = (
        len(findings)
        + int(research_report["finding_count"])
        + sum(int(row["finding_count"]) for row in row_results)
    )
    return {
        "ok": research_report["ok"] and not findings and not failing_rows,
        "path": _repo_relative(path),
        "capability_count": len(row_results),
        "failing_capability_count": len(failing_rows),
        "finding_count": finding_count,
        "findings": findings,
        "research_anchors": research_report,
        "rows": row_results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=DEFAULT_MAP)
    parser.add_argument("--research-anchors", type=Path, default=DEFAULT_RESEARCH_ANCHORS)
    parser.add_argument("--json", action="store_true", help="Print the full JSON report.")
    args = parser.parse_args(argv)

    report = audit(args.path.resolve(), args.research_anchors.resolve())
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        status = "OK" if report["ok"] else "FAIL"
        print(
            f"reasoning-compiler capability audit {status}: "
            f"{report['capability_count']} rows, {report['finding_count']} findings"
        )
        for row in report["rows"]:
            if row["ok"]:
                continue
            print(f"- {row['id']}: {'; '.join(row['findings'])}")
        for finding in report["findings"]:
            print(f"- {finding}")
        for finding in report["research_anchors"]["findings"]:
            print(f"- research anchors: {finding}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
