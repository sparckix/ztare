"""
GP-051 — Bounded Evidence-Collection Agent

Reads evidence gaps from workspace/latest_evidence_gaps.json, fetches public sources
for degrading gaps (or operator-specified severity), appends accepted provenance
blocks to evidence.txt, saves accepted raw fetch content to raw/, writes a
machine-readable manifest for all attempts, and optionally runs source-check +
workspace-update + evidence-compile so the operator doesn't have to.

Spec: GP-051 (internal seam)
Seam: GP-051 (internal seam)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any

from ztare.common.paths import PROJECTS_DIR
from ztare.workspace.evidence_gaps import evidence_gap_recovery_contract


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MANIFEST_PREFIX = "evidence_fetch_manifest"
RAW_FILE_PREFIX = "evidence_fetch"
DEFAULT_SEVERITY = "degrading"
DEFAULT_MAX_FETCHES = 3
ANTHROPIC_SEARCH_MODEL = "claude-sonnet-4-6"
DEFAULT_OPENAI_SEARCH_MODEL = "gpt-4.1"
WEB_SEARCH_BACKENDS = {"auto", "openai", "anthropic"}


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


def filter_gaps(
    gaps: list[dict],
    severity: str,
    *,
    project_dir: Path | None = None,
    allow_inferred_public: bool = False,
    target: str = "",
) -> list[dict]:
    # When `target` is given, fetch that single gap regardless of severity (the caller picked it
    # explicitly, e.g. a one-click "fetch this gap" button); otherwise batch by severity.
    target_norm = (target or "").strip().lower()
    filtered: list[dict] = []
    for gap in gaps:
        if target_norm:
            if target_norm not in str(gap.get("target", "")).strip().lower():
                continue
        elif gap.get("severity") != severity:
            continue
        contract = evidence_gap_recovery_contract(gap, project_dir=project_dir)
        if not contract.get("can_public_fetch"):
            continue
        if contract.get("schema_promotion_required") and not allow_inferred_public:
            continue
        filtered.append(gap)
    return filtered


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
                    status = str(entry.get("status") or "").strip().lower()
                    if status and status not in {"accepted", "fetched"}:
                        continue
                    if not status and int(entry.get("content_chars") or 0) <= 0:
                        continue
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


def classify_fetch_error(error_message: str) -> dict[str, Any]:
    """Classify provider-search failures for retry and operator recovery."""
    text = str(error_message or "").strip()
    lowered = text.lower()
    if any(marker in lowered for marker in ("insufficient_quota", "credit balance", "quota")):
        return {
            "failure_kind": "provider_quota",
            "retryable": False,
            "recovery_hint": "change billing state or choose another search backend",
        }
    if any(marker in lowered for marker in ("invalid_api_key", "authentication", "unauthorized", "401")):
        return {
            "failure_kind": "provider_auth",
            "retryable": False,
            "recovery_hint": "check the API key for the selected search backend",
        }
    if any(marker in lowered for marker in ("rate_limit", "rate limit", "429")):
        return {
            "failure_kind": "provider_rate_limit",
            "retryable": True,
            "recovery_hint": "retry later or choose another search backend",
        }
    if any(
        marker in lowered
        for marker in ("connection error", "timeout", "timed out", "network", "dns")
    ):
        return {
            "failure_kind": "provider_connection",
            "retryable": True,
            "recovery_hint": "retry the same search backend after network recovery",
        }
    if not text:
        return {
            "failure_kind": "provider_empty_error",
            "retryable": True,
            "recovery_hint": "retry with debug logging enabled",
        }
    return {
        "failure_kind": "provider_error",
        "retryable": True,
        "recovery_hint": "inspect provider error and retry or choose another search backend",
    }


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
# Web fetch via provider web-search tools
# ---------------------------------------------------------------------------

def web_search_backend_for_model(model: str, *, backend: str = "auto") -> str:
    """Return the web-search backend used by evidence-fetch.

    This path uses provider-native web-search tools, not the general text
    runtime. OpenAI-family models route to OpenAI Responses web_search_preview;
    every other model label uses the Anthropic web_search tool in auto mode
    until that provider exposes a compatible search tool here. Pass an explicit
    backend when source search and compile model should be different.
    """
    backend_label = str(backend or "auto").strip().lower()
    if backend_label not in WEB_SEARCH_BACKENDS:
        raise ValueError(
            f"Unsupported evidence search backend: {backend!r}. "
            "Expected one of: auto, openai, anthropic."
        )
    if backend_label in {"openai", "anthropic"}:
        return backend_label
    model_label = (model or "").strip()
    if not model_label:
        return "anthropic"
    try:
        from ztare.common.llm_runtime import get_model_family, resolve_model_id

        family = get_model_family(resolve_model_id(model_label))
        return "openai" if family == "openai" else "anthropic"
    except Exception:
        model_lower = model_label.lower()
        if model_lower.startswith(("gpt", "openai", "o1", "o3", "o4")):
            return "openai"
        return "anthropic"


def fetch_via_web_search(
    query: str,
    model: str = "",
    *,
    search_backend: str = "auto",
) -> tuple[str, str]:
    """
    Fetch and summarize content for a query using web search.
    Routes to OpenAI (web_search_preview) for OpenAI-family model labels;
    otherwise uses Anthropic's web_search tool.
    Returns (content, source_note). Raises RuntimeError on failure.
    """
    if web_search_backend_for_model(model, backend=search_backend) == "openai":
        return _fetch_via_openai_web_search(query, model)
    return _fetch_via_anthropic_web_search(query, requested_model=model)


def _openai_search_model_id(model: str) -> str:
    """Return an OpenAI model id suitable for web search."""
    model_label = (model or "").strip()
    if not model_label:
        return DEFAULT_OPENAI_SEARCH_MODEL
    try:
        from ztare.common.llm_runtime import get_model_family, resolve_model_id

        resolved = resolve_model_id(model_label)
        if get_model_family(resolved) == "openai":
            return resolved
    except Exception:
        pass
    model_lower = model_label.lower()
    if model_lower.startswith(("gpt", "openai", "o1", "o3", "o4")):
        return model_label
    return DEFAULT_OPENAI_SEARCH_MODEL


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
    model_id = _openai_search_model_id(model)

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
        if model and _openai_search_model_id(model) == DEFAULT_OPENAI_SEARCH_MODEL:
            source_note += f" (requested MODEL={model})"
        return content, source_note
    except Exception as e:
        raise RuntimeError(f"OpenAI API error during web search: {e}") from e


def _fetch_via_anthropic_web_search(
    query: str,
    requested_model: str = "",
) -> tuple[str, str]:
    """Fetch via Anthropic's web_search tool (original implementation)."""
    try:
        import anthropic
    except ImportError as exc:
        raise RuntimeError(
            "Anthropic evidence search requested but the optional anthropic SDK is not installed. "
            "Install `ztare[anthropic]` or choose --search-backend openai."
        ) from exc
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
        if requested_model and requested_model not in {"claude", ANTHROPIC_SEARCH_MODEL}:
            source_note += f" (requested MODEL={requested_model})"
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
    search_backend: str = "auto",
    allow_inferred_public: bool = False,
    target: str = "",
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
    filtered = filter_gaps(
        gaps,
        severity,
        project_dir=project_dir,
        allow_inferred_public=allow_inferred_public,
        target=target,
    )
    resolved_search_backend = web_search_backend_for_model(
        model,
        backend=search_backend,
    )

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
    failure_counts: dict[str, int] = {}

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
                "search_backend": resolved_search_backend,
            })
            continue

        total_attempted += 1
        print(f"  Gap {idx}: fetching '{query[:80]}{'...' if len(query) > 80 else ''}'")

        if dry_run:
            content = "[DRY RUN — no actual fetch performed]"
            source_note = "dry_run"
            status = "dry_run"
            error_message = ""
        else:
            try:
                content, source_note = fetch_via_web_search(
                    query,
                    model=model,
                    search_backend=search_backend,
                )
                status = "accepted"
                error_message = ""
                total_accepted += 1
                already_seen.add(query)
                print(f"    -> accepted ({len(content)} chars)")
            except RuntimeError as e:
                error_message = str(e)
                content = ""
                source_note = "fetch_failed"
                status = "rejected"
                failure = classify_fetch_error(error_message)
                failure_counts[str(failure["failure_kind"])] = (
                    failure_counts.get(str(failure["failure_kind"]), 0) + 1
                )
                print(f"    -> rejected: {e}")

        header = build_provenance_header(
            gap_index=idx,
            gap=gap,
            run_timestamp=str(run_timestamp),
            fetch_ts=fetch_ts,
            status=status,
            source_note=source_note,
        )
        if status == "accepted":
            block = f"{header}\n\n{content}\n\n---"
            appended_blocks.append(block)
            raw_sections.append(
                f"### Gap {idx} — {gap.get('target', 'unnamed')}\n\n{header}\n\n{content}"
            )

        manifest_entry = {
            "gap_index": idx,
            "gap_severity": gap.get("severity"),
            "gap_target": gap.get("target"),
            "gap_query": query,
            "run_timestamp": str(run_timestamp),
            "fetch_timestamp": fetch_ts,
            "status": status,
            "source_note": source_note,
            "search_backend": resolved_search_backend,
            "content_chars": len(content),
        }
        if error_message:
            manifest_entry["error_message"] = error_message
            manifest_entry.update(classify_fetch_error(error_message))
        manifest_entries.append(manifest_entry)

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
        "search_backend": resolved_search_backend,
        "search_backend_selector": search_backend,
        "allow_inferred_public": allow_inferred_public,
        "run_timestamp": str(run_timestamp),
        "max_fetches": max_fetches,
        "dry_run": dry_run,
        "fetches": manifest_entries,
        "skipped_duplicates": skipped_duplicates,
        "total_attempted": total_attempted,
        "total_accepted": total_accepted,
        "failure_counts": failure_counts,
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
    """Run source-check, workspace-update, then evidence-compile. Returns True on success."""
    import subprocess

    project_name = project_dir.name
    print(f"\nRunning source-check for {project_name}...")
    r0 = subprocess.run(
        [sys.executable, "-m", "ztare.scaffold.source_check",
         "--project", project_name],
        capture_output=False,
    )
    if r0.returncode != 0:
        print(
            f"source-check failed (exit {r0.returncode}) — "
            "skipping workspace-update and evidence-compile."
        )
        print("Fix raw source typing, then run manually:")
        print(f"  ztare project source-check --project {project_name} --json")
        print(f"  make evidence-prepare PROJECT={project_name} MODEL={model}")
        return False

    print(f"\nRunning workspace-update for {project_name}...")
    r1 = subprocess.run(
        [sys.executable, "-m", "ztare.workspace.update_workspace",
         "--project", project_name, "--model", model],
        capture_output=False,
    )
    if r1.returncode != 0:
        print(f"workspace-update failed (exit {r1.returncode}) — skipping evidence-compile.")
        print("Fix the error above, then run manually:")
        print(f"  make evidence-prepare PROJECT={project_name} MODEL={model}")
        return False

    print(f"\nRunning evidence-compile for {project_name}...")
    r2 = subprocess.run(
        [sys.executable, "-m", "ztare.workspace.compile_evidence",
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
        "--target",
        default="",
        help="Fetch the single gap whose target matches this text (case-insensitive substring), "
        "regardless of severity. Enables a one-click 'fetch this gap' action. Default: batch by severity.",
    )
    parser.add_argument(
        "--model",
        default="gemini",
        help="Model family for workspace-update and evidence-compile after source-check (if --auto-compile). Default: gemini",
    )
    parser.add_argument(
        "--search-backend",
        default=os.environ.get("ZTARE_EVIDENCE_SEARCH_BACKEND", "auto"),
        choices=sorted(WEB_SEARCH_BACKENDS),
        help=(
            "Web-search backend for evidence fetching. 'auto' follows the "
            "model family; use openai or anthropic when search and compile "
            "providers should differ. Env: ZTARE_EVIDENCE_SEARCH_BACKEND."
        ),
    )
    parser.add_argument(
        "--auto-compile",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Automatically run source-check + workspace-update + evidence-compile after fetching. Default: on.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be fetched without making any API calls or file writes.",
    )
    parser.add_argument(
        "--allow-inferred-public",
        action="store_true",
        help=(
            "Allow legacy rows classified as public by fallback inference to drive "
            "web fetch. Default requires an explicit public recovery contract."
        ),
    )
    args = parser.parse_args()

    try:
        project_dir = resolve_project_dir(args.project)
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    print(f"Project: {project_dir}")
    print(f"Severity: {args.severity} | Max fetches: {args.max_fetches} | Auto-compile: {args.auto_compile}")
    print(
        "Search backend: "
        f"{web_search_backend_for_model(args.model, backend=args.search_backend)} "
        f"(selector={args.search_backend})"
    )
    if args.dry_run:
        print("DRY RUN — no files will be written.\n")

    try:
        manifest = run_fetch(
            project_dir=project_dir,
            severity=args.severity,
            target=args.target,
            max_fetches=args.max_fetches,
            auto_compile=args.auto_compile,
            model=args.model,
            search_backend=args.search_backend,
            allow_inferred_public=args.allow_inferred_public,
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
