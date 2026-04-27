"""
GP-051 — Bounded Evidence-Collection Agent

Reads evidence gaps from workspace/latest_evidence_gaps.json, fetches public sources
for degrading gaps (or operator-specified severity), appends stamped provenance blocks
to evidence.txt, saves raw fetch content to raw/, writes a machine-readable manifest,
and optionally runs workspace-update + evidence-compile so the operator doesn't have to.

Spec: research_areas/private/specs/active/GP-051_evidence_fetch_agent_spec.md
Seam: research_areas/private/seams/GP-051_evidence_fetch_agent_seam.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import anthropic

from src.ztare.common.paths import PROJECTS_DIR


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MANIFEST_PREFIX = "evidence_fetch_manifest"
RAW_FILE_PREFIX = "evidence_fetch"
DEFAULT_SEVERITY = "degrading"
DEFAULT_MAX_FETCHES = 3
ANTHROPIC_SEARCH_MODEL = "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ts() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _ts_file() -> str:
    return time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())


def resolve_project_dir(project: str) -> Path:
    p = Path(project)
    if p.is_absolute() and p.exists():
        return p
    candidate = PROJECTS_DIR / project
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f"Project not found: {project}")


def load_evidence_gaps(workspace_dir: Path) -> list[dict[str, Any]]:
    gaps_path = workspace_dir / "latest_evidence_gaps.json"
    if not gaps_path.exists():
        raise FileNotFoundError(
            f"No evidence gaps file found at {gaps_path}.\n"
            "Run: make loop PROJECT=<project> ... to generate gaps first."
        )
    with open(gaps_path) as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    # Some runs wrap gaps in a dict under "evidence_gaps"
    if isinstance(data, dict) and "evidence_gaps" in data:
        return data["evidence_gaps"]
    raise ValueError(f"Unexpected evidence gaps schema at {gaps_path}")


def filter_gaps(gaps: list[dict], severity: str) -> list[dict]:
    return [g for g in gaps if g.get("severity") == severity]


def already_fetched_queries(evidence_txt: Path) -> set[str]:
    """Return set of fetch_query strings already fetched, from manifests and evidence.txt."""
    seen: set[str] = set()

    # Primary: scan workspace/ manifests — survives evidence-compile rewrites
    raw_dir = evidence_txt.parent / "workspace"
    if raw_dir.exists():
        for manifest_path in raw_dir.glob(f"{MANIFEST_PREFIX}_*.json"):
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                for entry in manifest.get("fetches", []):
                    q = (entry.get("gap_query") or entry.get("query") or "").strip()
                    if q:
                        seen.add(q)
            except Exception:
                pass

    # Fallback: scan evidence.txt provenance headers (pre-compile runs)
    if evidence_txt.exists():
        text = evidence_txt.read_text(encoding="utf-8")
        seen.update(re.findall(r"^Gap query: (.+)$", text, re.MULTILINE))

    return seen


def build_provenance_header(
    *,
    gap_index: int,
    gap: dict[str, Any],
    run_timestamp: str,
    fetch_ts: str,
    status: str,
    source_note: str = "",
) -> str:
    lines = [
        f"## Evidence Batch — {fetch_ts}",
        f"Gap index: {gap_index}",
        f"Gap severity: {gap.get('severity', 'unknown')}",
        f"Gap target: {gap.get('target', '')}",
        f"Gap query: {gap.get('fetch_query', '')}",
        f"Run timestamp: {run_timestamp}",
        f"Status: {status}",
    ]
    if source_note:
        lines.append(f"Source note: {source_note}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Web fetch via Anthropic web_search tool
# ---------------------------------------------------------------------------

def fetch_via_web_search(query: str, model: str = "") -> tuple[str, str]:
    """
    Fetch and summarize content for a query using web search.
    Routes to OpenAI (web_search_preview) when the model param starts with "gpt",
    otherwise uses Anthropic's web_search tool.
    Returns (content, source_note). Raises RuntimeError on failure.
    """
    model_lower = (model or "").strip().lower()
    if model_lower.startswith("gpt") or model_lower.startswith("openai"):
        return _fetch_via_openai_web_search(query, model)
    return _fetch_via_anthropic_web_search(query)


def _fetch_via_openai_web_search(query: str, model: str) -> tuple[str, str]:
    """Fetch via OpenAI's web_search_preview tool."""
    try:
        from openai import OpenAI
    except ImportError:
        raise RuntimeError("openai package not installed — cannot use GPT web search")

    client = OpenAI()
    prompt = (
        f"Search for and summarize the most relevant factual information for this query:\n\n"
        f"{query}\n\n"
        f"Return a concise factual summary (300-600 words) citing specific numbers, dates, "
        f"and sources where available. Focus on information that would be useful as evidence "
        f"for an analytical model or thesis."
    )
    # Resolve model ID
    model_id = model if "." in model or "-" in model else "gpt-4.1"
    try:
        from src.ztare.common.llm_runtime import resolve_model_id
        model_id = resolve_model_id(model)
    except Exception:
        pass

    try:
        response = client.responses.create(
            model=model_id,
            tools=[{"type": "web_search_preview"}],
            input=prompt,
        )
        text_parts = []
        for item in response.output:
            if hasattr(item, "text"):
                text_parts.append(item.text)
            elif hasattr(item, "content"):
                for block in item.content:
                    if hasattr(block, "text"):
                        text_parts.append(block.text)
        content = "\n\n".join(text_parts).strip()
        if not content:
            raise RuntimeError("Empty response from OpenAI web search")
        source_note = f"web_search via {model_id}"
        return content, source_note
    except Exception as e:
        raise RuntimeError(f"OpenAI API error during web search: {e}") from e


def _fetch_via_anthropic_web_search(query: str) -> tuple[str, str]:
    """Fetch via Anthropic's web_search tool (original implementation)."""
    client = anthropic.Anthropic()
    prompt = (
        f"Search for and summarize the most relevant factual information for this query:\n\n"
        f"{query}\n\n"
        f"Return a concise factual summary (300-600 words) citing specific numbers, dates, "
        f"and sources where available. Focus on information that would be useful as evidence "
        f"for an analytical model or thesis."
    )
    try:
        response = client.messages.create(
            model=ANTHROPIC_SEARCH_MODEL,
            max_tokens=1024,
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=[{"role": "user", "content": prompt}],
        )
        text_parts = []
        for block in response.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)
        content = "\n\n".join(text_parts).strip()
        if not content:
            raise RuntimeError("Empty response from web search")
        source_note = "web_search via claude-sonnet-4-6"
        return content, source_note
    except anthropic.APIError as e:
        raise RuntimeError(f"Anthropic API error during web search: {e}") from e


# ---------------------------------------------------------------------------
# Core fetch loop
# ---------------------------------------------------------------------------

def run_fetch(
    *,
    project_dir: Path,
    severity: str,
    max_fetches: int,
    auto_compile: bool,
    model: str,
    dry_run: bool,
) -> dict[str, Any]:
    workspace_dir = project_dir / "workspace"
    evidence_txt = project_dir / "evidence.txt"
    raw_dir = project_dir / "raw"
    raw_dir.mkdir(exist_ok=True)

    # Determine run timestamp from workspace meta if available
    run_timestamp = "unknown"
    meta_path = workspace_dir / "workspace_meta.json"
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            run_timestamp = meta.get("generated_on", run_timestamp)
        except Exception:
            pass
    # Also check iteration telemetry for loop run timestamp
    telemetry_path = workspace_dir / "iteration_telemetry.jsonl"
    if telemetry_path.exists():
        try:
            lines = telemetry_path.read_text().strip().splitlines()
            if lines:
                last = json.loads(lines[-1])
                run_timestamp = last.get("run_id", run_timestamp)
        except Exception:
            pass

    # Load and filter gaps
    gaps = load_evidence_gaps(workspace_dir)
    filtered = filter_gaps(gaps, severity)

    if not filtered:
        print(f"No evidence gaps with severity='{severity}' found. Nothing to fetch.")
        return {"fetches": [], "skipped_duplicates": 0, "total_attempted": 0, "total_accepted": 0}

    already_seen = already_fetched_queries(evidence_txt)
    fetch_ts = _ts()

    manifest_entries = []
    appended_blocks = []
    raw_sections = []
    skipped_duplicates = 0
    total_attempted = 0
    total_accepted = 0

    candidates = filtered[:max_fetches]
    if len(filtered) > max_fetches:
        print(f"Found {len(filtered)} {severity} gaps; fetching first {max_fetches} (--max-fetches={max_fetches}).")

    for idx, gap in enumerate(candidates):
        query = gap.get("fetch_query", "").strip()
        if not query:
            print(f"  Gap {idx}: no fetch_query — skipping.")
            continue

        if query in already_seen:
            print(f"  Gap {idx}: already fetched '{query[:60]}...' — skipping duplicate.")
            skipped_duplicates += 1
            manifest_entries.append({
                "gap_index": idx,
                "gap_severity": gap.get("severity"),
                "gap_target": gap.get("target"),
                "gap_query": query,
                "run_timestamp": str(run_timestamp),
                "status": "skipped_duplicate",
            })
            continue

        total_attempted += 1
        print(f"  Gap {idx}: fetching '{query[:80]}{'...' if len(query) > 80 else ''}'")

        if dry_run:
            content = "[DRY RUN — no actual fetch performed]"
            source_note = "dry_run"
            status = "dry_run"
        else:
            try:
                content, source_note = fetch_via_web_search(query, model=model)
                status = "accepted"
                total_accepted += 1
                already_seen.add(query)
                print(f"    -> accepted ({len(content)} chars)")
            except RuntimeError as e:
                content = f"[FETCH FAILED: {e}]"
                source_note = "fetch_failed"
                status = "rejected"
                print(f"    -> rejected: {e}")

        header = build_provenance_header(
            gap_index=idx,
            gap=gap,
            run_timestamp=str(run_timestamp),
            fetch_ts=fetch_ts,
            status=status,
            source_note=source_note,
        )
        block = f"{header}\n\n{content}\n\n---"
        appended_blocks.append(block)
        raw_sections.append(f"### Gap {idx} — {gap.get('target', 'unnamed')}\n\n{header}\n\n{content}")

        manifest_entries.append({
            "gap_index": idx,
            "gap_severity": gap.get("severity"),
            "gap_target": gap.get("target"),
            "gap_query": query,
            "run_timestamp": str(run_timestamp),
            "fetch_timestamp": fetch_ts,
            "status": status,
            "source_note": source_note,
            "content_chars": len(content),
        })

    # Write to evidence.txt
    if appended_blocks and not dry_run:
        separator = "\n\n" if evidence_txt.exists() else ""
        existing = evidence_txt.read_text(encoding="utf-8") if evidence_txt.exists() else ""
        with open(evidence_txt, "w", encoding="utf-8") as f:
            f.write(existing)
            f.write(separator)
            f.write("\n\n".join(appended_blocks))
            f.write("\n")
        print(f"\nAppended {len(appended_blocks)} block(s) to {evidence_txt}")

    # Write raw file for workspace pipeline
    if raw_sections and not dry_run:
        raw_filename = f"{RAW_FILE_PREFIX}_{_ts_file()}.md"
        raw_path = raw_dir / raw_filename
        raw_header = (
            f"---\nsource_type: source_evidence\n---\n"
            f"# Evidence Fetch — {fetch_ts}\n"
            f"Source: GP-051 bounded evidence-collection agent\n"
            f"Severity filter: {severity}\n"
            f"Gaps fetched: {len(raw_sections)}\n\n"
        )
        raw_path.write_text(raw_header + "\n\n".join(raw_sections), encoding="utf-8")
        print(f"Saved raw fetch file: {raw_path.name}")

    # Write manifest (skipped in dry_run)
    manifest = {
        "fetched_at": fetch_ts,
        "project": project_dir.name,
        "severity_filter": severity,
        "run_timestamp": str(run_timestamp),
        "max_fetches": max_fetches,
        "dry_run": dry_run,
        "fetches": manifest_entries,
        "skipped_duplicates": skipped_duplicates,
        "total_attempted": total_attempted,
        "total_accepted": total_accepted,
    }
    if not dry_run:
        manifest_path = workspace_dir / f"{MANIFEST_PREFIX}_{_ts_file()}.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"Manifest: {manifest_path.name}")

    return manifest


# ---------------------------------------------------------------------------
# Auto-compile pipeline
# ---------------------------------------------------------------------------

def run_auto_compile(*, project_dir: Path, model: str) -> bool:
    """Run workspace-update then evidence-compile. Returns True on success."""
    import subprocess

    project_name = project_dir.name
    print(f"\nRunning workspace-update for {project_name}...")
    r1 = subprocess.run(
        [sys.executable, "-m", "src.ztare.workspace.update_workspace",
         "--project", project_name, "--model", model],
        capture_output=False,
    )
    if r1.returncode != 0:
        print(f"workspace-update failed (exit {r1.returncode}) — skipping evidence-compile.")
        print("Fix the error above, then run manually:")
        print(f"  make workspace-update PROJECT={project_name} MODEL={model}")
        print(f"  make evidence-compile PROJECT={project_name} MODEL={model}")
        return False

    print(f"\nRunning evidence-compile for {project_name}...")
    r2 = subprocess.run(
        [sys.executable, "-m", "src.ztare.workspace.compile_evidence",
         "--project", project_name, "--mode", "workspace", "--model", model],
        capture_output=False,
    )
    if r2.returncode != 0:
        print(f"evidence-compile failed (exit {r2.returncode}).")
        print("Fix the error above, then run manually:")
        print(f"  make evidence-compile PROJECT={project_name} MODEL={model}")
        return False

    print("\nevidence-compile complete.")
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "GP-051 bounded evidence-collection agent. "
            "Fetches sources for degrading evidence gaps and appends them to evidence.txt."
        )
    )
    parser.add_argument("--project", required=True, help="Project name or absolute path.")
    parser.add_argument(
        "--severity",
        default=DEFAULT_SEVERITY,
        choices=["degrading", "enriching", "blocking"],
        help=f"Severity filter for evidence gaps. Default: {DEFAULT_SEVERITY}",
    )
    parser.add_argument(
        "--max-fetches",
        type=int,
        default=DEFAULT_MAX_FETCHES,
        help=f"Maximum number of gaps to fetch. Default: {DEFAULT_MAX_FETCHES}",
    )
    parser.add_argument(
        "--model",
        default="gemini",
        help="Model family for workspace-update and evidence-compile (if --auto-compile). Default: gemini",
    )
    parser.add_argument(
        "--auto-compile",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Automatically run workspace-update + evidence-compile after fetching. Default: on.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be fetched without making any API calls or file writes.",
    )
    args = parser.parse_args()

    try:
        project_dir = resolve_project_dir(args.project)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"Project: {project_dir}")
    print(f"Severity: {args.severity} | Max fetches: {args.max_fetches} | Auto-compile: {args.auto_compile}")
    if args.dry_run:
        print("DRY RUN — no files will be written.\n")

    try:
        manifest = run_fetch(
            project_dir=project_dir,
            severity=args.severity,
            max_fetches=args.max_fetches,
            auto_compile=args.auto_compile,
            model=args.model,
            dry_run=args.dry_run,
        )
    except (FileNotFoundError, ValueError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    accepted = manifest.get("total_accepted", 0)
    attempted = manifest.get("total_attempted", 0)
    skipped = manifest.get("skipped_duplicates", 0)

    print(f"\nSummary: {accepted}/{attempted} fetched, {skipped} duplicates skipped.")

    if accepted == 0:
        print("Nothing new fetched — no compile needed.")
        return 0

    if args.dry_run:
        print("Dry run complete. Re-run without --dry-run to fetch and write.")
        return 0

    if args.auto_compile:
        success = run_auto_compile(project_dir=project_dir, model=args.model)
        if not success:
            return 2

    print("\nDone. Run the loop when ready:")
    print(f"  make loop PROJECT={project_dir.name} RUBRIC=<rubric> ITERS=<n> ...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
