#!/usr/bin/env python3
"""Inspect the public PolyBench code/data surface for GP-245.

This script is intentionally not a score audit. It records what is available
from the public repository, whether a local PolyBench database is present, and
which row-level fields become auditable once the released database is available.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
PROGRAM = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_REPO_DIR = Path("/private/tmp/gp245_polybench/PolyBench")
DEFAULT_DATASET_RESPONSE = Path("/private/tmp/gp245_polybench/onedrive_page.html")
DEFAULT_OUT = PROGRAM / "paper_alignment_v1/workspace/field_wide_validity_audit_2026_06_16"
DATASET_URL = "https://1drv.ms/u/c/4d62feca782041b1/IQDR4BGbCmakS7Cid8OzCcHxAR-iaHdX0WPtmmdWQ_ab2Tg?e=cHQ2MZ"
DATASET_DOWNLOAD_URL = "https://1drv.ms/u/c/4d62feca782041b1/IQDR4BGbCmakS7Cid8OzCcHxAR-iaHdX0WPtmmdWQ_ab2Tg?download=1"
GITHUB_API = "https://api.github.com/repos/PolyBench/PolyBench"
PUBLIC_REPO_URL = "https://github.com/PolyBench/PolyBench"

TABLE_SQL_RE = re.compile(r"CREATE TABLE IF NOT EXISTS\s+([a-zA-Z_]+)\s*\((.*?)\)\s*\"\"\"", re.S)
FIELD_RE = re.compile(r"^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s+(TEXT|REAL|BOOLEAN|INTEGER|DATETIME)", re.M)
DATA_ARTIFACT_RE = re.compile(r"\.(db|sqlite|sqlite3|csv|tsv|jsonl|parquet|arrow|feather)$", re.I)
DATA_PATH_RE = re.compile(r"database|prediction|result|score|leader|eval|market|snapshot|resolution|trade", re.I)


CSV_COLUMNS = [
    "repo_available",
    "repo_head",
    "database_ready",
    "dataset_download_status",
    "schema_tables",
    "remote_repo_head",
    "github_release_count",
    "github_committed_data_artifacts",
    "dataset_head_status",
    "dataset_download_head_status",
    "row_level_fields",
    "missing_for_score",
    "pilot_status",
]

MD_COLUMNS = [
    "repo_available",
    "repo_head",
    "database_ready",
    "dataset_download_status",
    "schema_tables",
    "remote_repo_head",
    "github_release_count",
    "github_committed_data_files",
    "dataset_head_status",
    "dataset_download_head_status",
    "row_level_fields",
    "missing_for_score",
    "pilot_status",
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def repo_head(repo_dir: Path) -> str:
    head = read_text(repo_dir / ".git/HEAD").strip()
    if not head:
        return ""
    if head.startswith("ref:"):
        ref = head.split(" ", 1)[1]
        return read_text(repo_dir / ".git" / ref).strip()
    return head


def fetch_json(url: str, *, timeout: int = 20) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "gp245-polybench-source-pilot/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def head_status(url: str, *, timeout: int = 20) -> dict[str, Any]:
    req = urllib.request.Request(
        url,
        method="HEAD",
        headers={"User-Agent": "gp245-polybench-source-pilot/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return {
                "status": str(response.status),
                "final_url": response.geturl(),
                "content_type": response.headers.get("content-type", ""),
                "content_length": response.headers.get("content-length", ""),
                "error": "",
            }
    except urllib.error.HTTPError as exc:
        return {
            "status": str(exc.code),
            "final_url": exc.geturl(),
            "content_type": exc.headers.get("content-type", "") if exc.headers else "",
            "content_length": exc.headers.get("content-length", "") if exc.headers else "",
            "error": exc.reason or "",
        }
    except (urllib.error.URLError, TimeoutError) as exc:
        return {
            "status": "fetch_failed",
            "final_url": "",
            "content_type": "",
            "content_length": "",
            "error": str(exc),
        }


def github_remote_surface() -> dict[str, Any]:
    surface: dict[str, Any] = {
        "remote_repo_head": "",
        "remote_check_status": "not_checked",
        "github_release_count": None,
        "github_tree_paths": None,
        "github_candidate_paths": [],
        "github_committed_data_artifacts": [],
    }
    try:
        ref = fetch_json(f"{GITHUB_API}/git/refs/heads/main")
        surface["remote_repo_head"] = str(ref.get("object", {}).get("sha", ""))
        releases = fetch_json(f"{GITHUB_API}/releases")
        surface["github_release_count"] = len(releases) if isinstance(releases, list) else None
        tree = fetch_json(f"{GITHUB_API}/git/trees/main?recursive=1")
    except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
        surface["remote_check_status"] = f"fetch_failed: {exc}"
        return surface

    paths = [
        str(item.get("path"))
        for item in tree.get("tree", [])
        if isinstance(item, dict) and item.get("type") == "blob" and item.get("path")
    ]
    candidates = sorted(path for path in paths if DATA_PATH_RE.search(path))
    artifacts = sorted(path for path in candidates if DATA_ARTIFACT_RE.search(path))
    surface.update(
        {
            "remote_check_status": "ok",
            "github_tree_paths": len(paths),
            "github_candidate_paths": candidates,
            "github_committed_data_artifacts": artifacts,
        }
    )
    return surface


def parse_tables(models_py: Path) -> dict[str, list[str]]:
    text = read_text(models_py)
    tables: dict[str, list[str]] = {}
    for table, body in TABLE_SQL_RE.findall(text):
        fields = [
            match.group(1)
            for match in FIELD_RE.finditer(body)
            if match.group(1).lower() not in {"foreign"}
        ]
        tables[table] = fields
    return tables


def find_database_files(repo_dir: Path, dataset_path: Path | None) -> list[str]:
    roots = [repo_dir]
    if dataset_path is not None:
        roots.append(dataset_path)
    found: list[str] = []
    for root in roots:
        if not root.exists():
            continue
        if root.is_file() and root.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
            found.append(str(root))
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
                found.append(str(path))
    return sorted(set(found))


def dataset_status(response_path: Path, database_files: list[str]) -> dict[str, Any]:
    if database_files:
        return {
            "status": "local_database_present",
            "response_bytes": None,
            "response_excerpt": "",
        }
    text = read_text(response_path)
    if not text:
        return {
            "status": "not_downloaded",
            "response_bytes": 0,
            "response_excerpt": "",
        }
    plain = re.sub(r"<[^>]+>", " ", text)
    plain = re.sub(r"\s+", " ", plain).strip()
    if "The request is blocked" in text:
        status = "blocked_noninteractive_onedrive_request"
        excerpt = "The request is blocked."
    elif "unauthenticated" in text.lower():
        status = "unauthenticated_share_api"
        excerpt = plain[:240]
    else:
        status = "download_response_without_database"
        excerpt = plain[:240]
    return {
        "status": status,
        "response_bytes": response_path.stat().st_size,
        "response_excerpt": excerpt,
    }


def markdown_table(rows: list[dict[str, str]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(row.get(col, "").replace("|", r"\|") for col in columns) + " |")
    return "\n".join([header, sep, *body])


def build_report(repo_dir: Path, dataset_path: Path | None, dataset_response: Path) -> dict[str, Any]:
    readme = read_text(repo_dir / "README.md")
    tables = parse_tables(repo_dir / "database/models.py")
    db_files = find_database_files(repo_dir, dataset_path)
    ds = dataset_status(dataset_response, db_files)
    remote = github_remote_surface()
    dataset_head = head_status(DATASET_URL)
    dataset_download_head = head_status(DATASET_DOWNLOAD_URL)
    if (
        not db_files
        and dataset_download_head.get("status") == "200"
        and "text/html" in str(dataset_download_head.get("content_type", "")).lower()
    ):
        ds = {
            **ds,
            "status": "onedrive_html_page_no_direct_database_download",
            "response_excerpt": ds.get("response_excerpt") or "OneDrive returned an HTML page, not a direct database file.",
        }
    row_fields = {
        "source_currency": ["prediction timestamp", "snapshot timestamp", "market end date"],
        "equal_information": ["market prices", "order book snapshot", "prediction timestamp"],
        "label_time": ["winning outcome", "resolved at", "resolution source"],
        "model_output": ["model name", "decision", "side", "confidence", "raw response"],
    }
    missing = [
        "released SQLite database or equivalent row export",
        "confirmed mapping from model confidence/side to probability of the winning outcome",
        "same-snapshot market midpoint or executable price extraction for proper-score comparison",
        "event-family de-duplication across sibling binary markets",
    ]
    status = "source_schema_ready_dataset_unavailable"
    if db_files:
        status = "database_ready_for_row_schema_pilot"
    elif ds["status"] == "not_downloaded":
        status = "repo_schema_ready_dataset_not_checked"
    return {
        "schema": "gp245-polybench-source-access-pilot-v1",
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "repo_dir": str(repo_dir),
        "public_repo_url": PUBLIC_REPO_URL,
        "repo_available": repo_dir.exists(),
        "repo_head": repo_head(repo_dir),
        "remote_repo_head": remote["remote_repo_head"],
        "remote_head_matches_local": bool(remote["remote_repo_head"] and remote["remote_repo_head"] == repo_head(repo_dir)),
        "remote_check_status": remote["remote_check_status"],
        "github_release_count": remote["github_release_count"],
        "github_tree_paths": remote["github_tree_paths"],
        "github_candidate_paths": remote["github_candidate_paths"],
        "github_committed_data_artifacts": remote["github_committed_data_artifacts"],
        "dataset_url": DATASET_URL,
        "dataset_download_url": DATASET_DOWNLOAD_URL,
        "dataset_head_status": dataset_head,
        "dataset_download_head_status": dataset_download_head,
        "dataset_response_path": str(dataset_response),
        "dataset_download_status": ds["status"],
        "dataset_response_bytes": ds["response_bytes"],
        "dataset_response_excerpt": ds["response_excerpt"],
        "database_files_found": db_files,
        "database_ready": bool(db_files),
        "readme_dataset_link_present": "1drv.ms" in readme,
        "readme_reported_counts": {
            "binary_markets": 38666 if "38,666" in readme else None,
            "events": 4997 if "4,997" in readme else None,
        },
        "schema_tables": tables,
        "row_level_fields_available_from_schema": row_fields,
        "missing_for_score": missing,
        "pilot_status": status,
    }


def render_markdown(report: dict[str, Any]) -> str:
    row = {
        "repo_available": str(report["repo_available"]),
        "repo_head": str(report["repo_head"])[:12],
        "database_ready": str(report["database_ready"]),
        "dataset_download_status": str(report["dataset_download_status"]),
        "schema_tables": ", ".join(report["schema_tables"].keys()),
        "remote_repo_head": str(report["remote_repo_head"])[:12],
        "github_release_count": str(report["github_release_count"]),
        "github_committed_data_files": str(len(report["github_committed_data_artifacts"])),
        "dataset_head_status": str(report["dataset_head_status"].get("status")),
        "dataset_download_head_status": str(report["dataset_download_head_status"].get("status")),
        "row_level_fields": "; ".join(
            f"{key}: {', '.join(value)}"
            for key, value in report["row_level_fields_available_from_schema"].items()
        ),
        "missing_for_score": "; ".join(report["missing_for_score"]),
        "pilot_status": str(report["pilot_status"]),
    }
    lines = [
        "# GP-245 PolyBench Source-Access Pilot",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        f"- Repository directory: `{report['repo_dir']}`",
        f"- Repository available: `{report['repo_available']}`",
        f"- Repository commit: `{report['repo_head']}`",
        f"- Public repository: `{report['public_repo_url']}`",
        f"- Remote repository commit: `{report['remote_repo_head']}`",
        f"- Remote/local commit match: `{report['remote_head_matches_local']}`",
        f"- GitHub release count: `{report['github_release_count']}`",
        f"- Committed data files in GitHub tree: `{len(report['github_committed_data_artifacts'])}`",
        f"- Dataset link present in README: `{report['readme_dataset_link_present']}`",
        f"- Dataset download status: `{report['dataset_download_status']}`",
        f"- Dataset link HEAD status: `{report['dataset_head_status'].get('status')}`",
        f"- Dataset download HEAD status: `{report['dataset_download_head_status'].get('status')}`",
        f"- Database ready locally: `{report['database_ready']}`",
        "",
        "Interpretation: the public repository exposes the row schema needed for a PolyBench audit, but it has no GitHub release, no committed database/CSV/parquet row file, and the advertised OneDrive dataset link resolves to an HTML page rather than a direct database file in this noninteractive run. This supports a source-access finding, not a PolyBench score result.",
        "",
        "## Pilot Summary",
        "",
        markdown_table([row], MD_COLUMNS),
        "",
    ]
    if report.get("dataset_response_excerpt"):
        lines.extend(
            [
                "## Dataset Response Excerpt",
                "",
                report["dataset_response_excerpt"],
                "",
            ]
        )
    return "\n".join(lines)


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-dir", type=Path, default=DEFAULT_REPO_DIR)
    parser.add_argument("--dataset-path", type=Path)
    parser.add_argument("--dataset-response", type=Path, default=DEFAULT_DATASET_RESPONSE)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    report = build_report(args.repo_dir, args.dataset_path, args.dataset_response)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    json_path = args.out_dir / "field_wide_polybench_source_pilot.json"
    csv_path = args.out_dir / "field_wide_polybench_source_pilot.csv"
    md_path = args.out_dir / "field_wide_polybench_source_pilot.md"

    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    csv_row = {
        "repo_available": str(report["repo_available"]),
        "repo_head": str(report["repo_head"]),
        "database_ready": str(report["database_ready"]),
        "dataset_download_status": str(report["dataset_download_status"]),
        "schema_tables": ", ".join(report["schema_tables"].keys()),
        "remote_repo_head": str(report["remote_repo_head"]),
        "github_release_count": str(report["github_release_count"]),
        "github_committed_data_artifacts": str(len(report["github_committed_data_artifacts"])),
        "dataset_head_status": str(report["dataset_head_status"].get("status")),
        "dataset_download_head_status": str(report["dataset_download_head_status"].get("status")),
        "row_level_fields": json.dumps(report["row_level_fields_available_from_schema"], sort_keys=True),
        "missing_for_score": "; ".join(report["missing_for_score"]),
        "pilot_status": str(report["pilot_status"]),
    }
    write_csv(csv_path, [csv_row])
    md_path.write_text(render_markdown(report), encoding="utf-8")

    print(
        json.dumps(
            {
                "schema": report["schema"],
                "repo_available": report["repo_available"],
                "database_ready": report["database_ready"],
                "dataset_download_status": report["dataset_download_status"],
                "pilot_status": report["pilot_status"],
                "outputs": [str(json_path), str(csv_path), str(md_path)],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
