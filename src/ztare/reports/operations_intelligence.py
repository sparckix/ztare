"""Private ZTARE intelligence surface.

This module composes existing ledgers and durable work surfaces into a private,
read-only packet. Source ledgers remain authoritative; this surface only joins,
summarizes, and names observer-only learning candidates.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[3]
DEFAULT_PRIVATE_DIR = REPO / "analytics/private/intelligence"
DEFAULT_JSON_OUT = DEFAULT_PRIVATE_DIR / "ztare_intelligence_surface.json"
DEFAULT_MD_OUT = DEFAULT_PRIVATE_DIR / "ztare_intelligence_surface.md"
DEFAULT_HTML_OUT = DEFAULT_PRIVATE_DIR / "ztare_intelligence_surface.html"

FORECAST_POOL = Path("analytics/public/forecast_pool")
GP233 = Path("analytics/public/ledgers/research_yield_decomposition/GP-233_EVIDENCE_LEDGER.md")
CATCH = Path("analytics/public/ledgers/catch/catch_ledger.jsonl")
ACTION_HEALTH = Path("analytics/public/action_intelligence/state/source_health.json")
ACTION_STATE = Path("analytics/public/action_intelligence/state/action_intelligence.json")
EXPERIMENT_LEDGER = Path("research_areas/EXPERIMENT_TRACK_RECORD.md")
P0_METRICS = Path("analytics/public/ledgers/reflexive/p0_metrics.json")
RECURSIVE_GAIN = Path("analytics/public/queries/trajectory/recursive_gain_candidates.json")
BIFURCATION = Path("analytics/public/ledgers/reflexive/bifurcation_report.json")
DASHBOARD_SOURCES: dict[str, Path] = {
    "trajectory_curves": Path("analytics/public/queries/trajectory/trajectory_curves.json"),
    "inflection_candidates": Path("analytics/public/queries/trajectory/inflection_candidates.json"),
    "taste_weighted_insight": Path("analytics/public/queries/taste/taste_weighted_insight.json"),
    "reference_graph": Path("analytics/public/queries/reference_graph.json"),
    "consequential_artifacts_by_week": Path("analytics/public/queries/trajectory/consequential_artifacts_by_week.json"),
    "recursive_gain_candidates": RECURSIVE_GAIN,
    "bifurcation_report": BIFURCATION,
    "graph_sowhat": Path("analytics/public/queries/graph_sowhat.json"),
    "p0_metrics": P0_METRICS,
}

STATUS_NAME_RE = re.compile(
    r"(research-log|research_log|residual|manifest|summary|status|decision|README|CHARTER|charter)",
    re.IGNORECASE,
)

FOCUS_TRACKS: dict[str, dict[str, Any]] = {
    "ns_millennium_hunt": {
        "label": "NS Millennium Hunt",
        "paths": ["projects/ns_millennium_hunt"],
        "status_globs": [
            "projects/ns_millennium_hunt/workspace/*manifest*.md",
            "projects/ns_millennium_hunt/workspace/*manifest*.json",
            "projects/ns_millennium_hunt/workspace/*summary*.md",
            "projects/ns_millennium_hunt/workspace/*status*.md",
            "projects/ns_millennium_hunt/research-output/*.md",
        ],
        "aliases": ["ns_millennium_hunt", "navier", "clay", "ns route", "c7", "tick6"],
    },
    "gnn_lemma_relevance": {
        "label": "GNN / LeanMill Lemma Relevance",
        "paths": ["analytics/public/leanmill", "scripts/public/control"],
        "status_globs": [
            "analytics/public/leanmill/dashboard_data/*.json",
            "analytics/public/leanmill/_archive/LATEST_META_SOLVER_CONSUMPTION_MANIFEST.*",
            "analytics/public/leanmill/leansearch/LEANSEARCH_MCB_REMAINING_ROW_CONTEXT_FILTER.json",
            "scripts/public/control/leansearch_factory*.py",
        ],
        "aliases": ["gnn", "lemma relevance", "leansearch", "leanmill", "leanhammer", "gp225"],
    },
    "epistemic_generation": {
        "label": "Epistemic Generation",
        "paths": ["workingpapers/epistemic-generation", "papers/epistemic-generation"],
        "status_globs": [
            "workingpapers/epistemic-generation/README.md",
            "workingpapers/epistemic-generation/research_log.md",
            "workingpapers/epistemic-generation/SEALED_PREREG_*.md",
            "workingpapers/epistemic-generation/evidence/**/*verdict*.json",
            "papers/epistemic-generation/main.tex",
        ],
        "aliases": ["epistemic-generation", "epistemic_generation", "epistemic generation", "functional uplift", "ecr"],
    },
}

RESEARCH_OPS_METRIC_AREAS: list[dict[str, Any]] = [
    {
        "area_id": "information_yield",
        "purpose": "Track whether research changed belief, route choice, or artifact quality.",
        "implemented_metrics": ["gp233_rows", "finding_rows", "decision_changed_rate_proxy", "top_bottlenecks"],
        "primary_sources": [str(GP233), str(EXPERIMENT_LEDGER)],
        "status": "partial",
        "source_gap": "GP-233 and the experiment ledger need derived structured rows for reliable decision-change and belief-delta rates.",
    },
    {
        "area_id": "decision_use",
        "purpose": "Track whether forecasts and surfaced signals changed action.",
        "implemented_metrics": ["forecast_decision_use_rate", "decision_use_gap", "allocation_counts_latest40"],
        "primary_sources": [str(FORECAST_POOL / "aggregates"), str(FORECAST_POOL / "decision_use/decision_use_ledger.jsonl")],
        "status": "implemented_source_blocked",
        "source_gap": "Decision-use rows are sparse relative to forecast aggregates.",
    },
    {
        "area_id": "recursive_learning",
        "purpose": "Track whether insights become reusable primitives, gates, patterns, or retired routes.",
        "implemented_metrics": ["learning_candidate_count", "learning_candidate_lifecycle", "recursive_gain_candidates"],
        "primary_sources": [str(RECURSIVE_GAIN), "research_areas/seams", "research_areas/specs", "src/ztare"],
        "status": "partial",
        "source_gap": "Lifecycle matching is a proxy until promoted learning events have durable IDs.",
    },
    {
        "area_id": "research_flow",
        "purpose": "Track lead time, rework, recovery, and parallelism without rewarding shallow speed.",
        "implemented_metrics": ["iteration_telemetry_files", "latest_telemetry_sources"],
        "primary_sources": ["projects/*/workspace/iteration_telemetry.jsonl", str(FORECAST_POOL / "contracts")],
        "status": "source_gap",
        "source_gap": "Question-to-contract, contract-to-evidence, and evidence-to-close timestamps are not yet joined.",
    },
    {
        "area_id": "reliability_calibration",
        "purpose": "Track calibration, high-confidence misses, source health, and evidence coverage.",
        "implemented_metrics": ["source_health_blockers", "unresolved_contracts", "unscored_outcomes", "metric_caveats"],
        "primary_sources": [str(ACTION_HEALTH), str(FORECAST_POOL / "scores"), str(FORECAST_POOL / "outcomes")],
        "status": "partial",
        "source_gap": "Reliability buckets and high-confidence miss incidents need a structured score rollup.",
    },
    {
        "area_id": "externality_guardrails",
        "purpose": "Track Goodhart risk, treadmill recurrence, human bottlenecks, and measurement overhead.",
        "implemented_metrics": ["activity_yield_divergence", "recurrence_suppression_candidates", "top_catch_categories"],
        "primary_sources": [str(DASHBOARD_SOURCES["trajectory_curves"]), str(CATCH)],
        "status": "partial",
        "source_gap": "Suppression rates need later recurrence/avoidance labels at the catch source.",
    },
]

PROCESS_INPUT_METRIC_CONTRACTS: list[dict[str, Any]] = [
    {
        "metric_id": "decision_use_logging",
        "metric_kind": "controllable_input",
        "cadence": "per forecast aggregate",
        "definition": "Record whether and how a forecast changed an action.",
        "desired_direction": "up",
        "downstream_output": "forecast_decision_use_rate",
        "source_gap_if_missing": "forecast aggregates remain calibration-only",
    },
    {
        "metric_id": "source_health_repair",
        "metric_kind": "controllable_input",
        "cadence": "daily or before consuming the surface",
        "definition": "Repair blocking source-health issues before using aggregate recommendations.",
        "desired_direction": "down for blockers",
        "downstream_output": "trusted_intelligence_surface",
        "source_gap_if_missing": "missing emitters can create false confidence",
    },
    {
        "metric_id": "structured_yield_logging",
        "metric_kind": "controllable_input",
        "cadence": "per closed run",
        "definition": "Log bottleneck, evidence pointer, decision change, and verdict in queryable form.",
        "desired_direction": "up",
        "downstream_output": "decision_changed_rate and bottleneck resolution",
        "source_gap_if_missing": "markdown-only rows block robust joins",
    },
    {
        "metric_id": "catch_preconditioner_consumption",
        "metric_kind": "controllable_input",
        "cadence": "before run and at close",
        "definition": "Record when a catch or anti-pattern was consumed as a run preconditioner.",
        "desired_direction": "up",
        "downstream_output": "recurrence_suppression_rate",
        "source_gap_if_missing": "failure-mode catalogue cannot prove avoided recurrence",
    },
    {
        "metric_id": "learning_candidate_review",
        "metric_kind": "controllable_process",
        "cadence": "weekly or after intelligence refresh",
        "definition": "Review observer-only learning candidates and mark promote, defer, reject, or source-fix.",
        "desired_direction": "up for reviewed share",
        "downstream_output": "candidate_promotion_rate and primitive reuse",
        "source_gap_if_missing": "recursive insights accumulate without adoption state",
    },
    {
        "metric_id": "dashboard_feed_freshness",
        "metric_kind": "controllable_process",
        "cadence": "per intelligence refresh",
        "definition": "Ensure the trajectory, P0, recursive-gain, and reference-graph feeds are present and fresh.",
        "desired_direction": "up for present/fresh feeds",
        "downstream_output": "activity_yield and reflexive trajectory confidence",
        "source_gap_if_missing": "stale public-dashboard feeds weaken private intelligence",
    },
    {
        "metric_id": "hard_tick_depth_receipt_quality",
        "metric_kind": "controllable_input",
        "cadence": "per hard research tick",
        "definition": "Produce inspectable orientation, stress-test, and verification artifacts before close.",
        "desired_direction": "up",
        "downstream_output": "lower shallow-close/rework rate",
        "source_gap_if_missing": "research-flow metrics can reward fast but shallow closure",
    },
    {
        "metric_id": "human_unblock_logging",
        "metric_kind": "controllable_process",
        "cadence": "when human action blocks agent progress",
        "definition": "Log the blocked action, needed human contribution, and whether the block was avoidable.",
        "desired_direction": "up for logged blocks; down for avoidable blocks",
        "downstream_output": "human_blocked_time and handoff quality",
        "source_gap_if_missing": "human bottleneck metrics become anecdotal",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(repo: Path, path: Path) -> str:
    try:
        return str(path.relative_to(repo))
    except ValueError:
        return str(path)


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def safe_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def iso_from_mtime(path: Path) -> str | None:
    ts = safe_mtime(path)
    if not ts:
        return None
    return datetime.fromtimestamp(ts, timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_markdown_table(path: Path) -> list[list[str]]:
    if not path.exists():
        return []
    rows: list[list[str]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        stripped = line.strip()
        if not stripped.startswith("|") or "---" in stripped:
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if len(cells) >= 2:
            rows.append(cells)
    return rows


def parse_gp233(repo: Path) -> dict[str, Any]:
    path = repo / GP233
    rows = parse_markdown_table(path)
    data_rows = [r for r in rows if r and r[0].lower() != "date"]
    parsed: list[dict[str, Any]] = []
    verdicts: Counter[str] = Counter()
    bottlenecks: Counter[str] = Counter()
    for cells in data_rows:
        if len(cells) < 6:
            continue
        row = {
            "date": cells[0],
            "lane": cells[1],
            "evidence_pointer": cells[2],
            "bottleneck": cells[3],
            "decision_changed": cells[4],
            "verdict": cells[5],
        }
        parsed.append(row)
        verdicts[row["verdict"]] += 1
        bottlenecks[row["bottleneck"]] += 1
    return {
        "source": rel(repo, path),
        "row_count": len(parsed),
        "verdict_counts": dict(verdicts.most_common()),
        "top_bottlenecks": [{"name": k, "count": v} for k, v in bottlenecks.most_common(12)],
        "latest": parsed[:12],
        "rows": parsed,
    }


def parse_experiment_ledger(repo: Path) -> dict[str, Any]:
    path = repo / EXPERIMENT_LEDGER
    rows = parse_markdown_table(path)
    if not rows:
        return {"source": rel(repo, path), "row_count": 0, "status_counts": {}, "latest": [], "rows": []}
    header = [cell.lower().replace(" ", "_").replace("/", "_") for cell in rows[0]]
    parsed: list[dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    kind_counts: Counter[str] = Counter()
    for cells in rows[1:]:
        if len(header) == 7 and len(cells) >= 7:
            normalized = [
                cells[0],
                cells[1],
                cells[2],
                cells[3],
                " | ".join(cells[4:-2]),
                cells[-2],
                cells[-1],
            ]
        else:
            normalized = cells[:len(header)]
        row = {header[idx] if idx < len(header) else f"col_{idx}": cell for idx, cell in enumerate(normalized)}
        parsed.append(row)
        status = str(row.get("status") or row.get("verdict") or "unknown")
        kind = str(row.get("kind") or row.get("type") or row.get("experiment") or "row")
        status_counts[status] += 1
        kind_counts[kind] += 1
    finding_rows = sum(
        1
        for row in parsed
        if "finding" in " ".join(str(v).lower() for v in row.values())
        or "result" in " ".join(str(v).lower() for v in row.values())
    )
    return {
        "source": rel(repo, path),
        "row_count": len(parsed),
        "finding_rows": finding_rows,
        "status_counts": dict(status_counts.most_common(12)),
        "kind_counts": dict(kind_counts.most_common(12)),
        "latest": [{k: str(v)[:360] for k, v in row.items()} for row in parsed[:12]],
        "rows": parsed,
    }


def summarize_forecast_market(repo: Path) -> dict[str, Any]:
    base = repo / FORECAST_POOL
    contracts = sorted((base / "contracts").glob("*.json")) if (base / "contracts").exists() else []
    aggregates = sorted((base / "aggregates").glob("*.json")) if (base / "aggregates").exists() else []
    outcomes = {p.stem for p in (base / "outcomes").glob("*.json")} if (base / "outcomes").exists() else set()
    scores = {p.stem for p in (base / "scores").glob("*.json")} if (base / "scores").exists() else set()
    decision_use = read_jsonl(base / "decision_use/decision_use_ledger.jsonl")
    allocation_counts: Counter[str] = Counter()
    latest: list[dict[str, Any]] = []
    for path in sorted(aggregates, key=safe_mtime, reverse=True)[:40]:
        payload = read_json(path, {})
        if not isinstance(payload, dict):
            continue
        alloc = payload.get("allocation_recommendation") or {}
        agg = payload.get("aggregate") or {}
        if isinstance(alloc, dict):
            allocation_counts[str(alloc.get("action") or "unknown")] += 1
        latest.append({
            "contract_id": payload.get("contract_id") or path.stem,
            "question": payload.get("contract_question"),
            "p_success": agg.get("p_success") if isinstance(agg, dict) else None,
            "allocation": alloc.get("action") if isinstance(alloc, dict) else None,
            "routing_hint": payload.get("routing_hint"),
            "forecast_count": payload.get("forecast_count"),
            "source": rel(repo, path),
        })
    unresolved = [p.stem for p in contracts if p.stem not in outcomes]
    unscored = [name for name in outcomes if name not in scores]
    decision_use_gap = max(0, len(aggregates) - len(decision_use))
    decision_use_rate = round(len(decision_use) / len(aggregates), 4) if aggregates else None
    return {
        "source_root": rel(repo, base),
        "contracts": len(contracts),
        "aggregates": len(aggregates),
        "outcomes": len(outcomes),
        "scores": len(scores),
        "unresolved_contracts": len(unresolved),
        "unscored_outcomes": len(unscored),
        "decision_use_rows": len(decision_use),
        "decision_use_gap": decision_use_gap,
        "decision_use_rate": decision_use_rate,
        "allocation_counts_latest40": dict(allocation_counts.most_common()),
        "latest_aggregates": latest[:12],
        "source_health_refs": [
            rel(repo, base / "contracts"),
            rel(repo, base / "aggregates"),
            rel(repo, base / "decision_use/decision_use_ledger.jsonl"),
        ],
    }


def summarize_catches(repo: Path) -> dict[str, Any]:
    path = repo / CATCH
    rows = read_jsonl(path)
    categories: Counter[str] = Counter(str(r.get("category") or "unknown") for r in rows)
    recent_categories: Counter[str] = Counter(str(r.get("category") or "unknown") for r in rows[-40:])
    ratified = sum(1 for r in rows if r.get("status") == "ratified" or r.get("ratified_at"))
    consequential = sum(1 for r in rows if r.get("load_bearing") is True or r.get("consequential") is True)
    latest = [
        {
            "catch_id": row.get("catch_id"),
            "title": row.get("title"),
            "category": row.get("category"),
            "status": row.get("status"),
            "source": rel(repo, path),
        }
        for row in rows[-12:][::-1]
    ]
    return {
        "source": rel(repo, path),
        "rows": len(rows),
        "ratified": ratified,
        "consequential": consequential,
        "top_categories": [{"name": k, "count": v} for k, v in categories.most_common(12)],
        "recent_categories": [{"name": k, "count": v} for k, v in recent_categories.most_common(12)],
        "latest": latest,
    }


def markdown_summary(path: Path) -> str:
    if not path.exists() or path.suffix.lower() != ".md":
        return ""
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            for next_line in lines[idx + 1: idx + 12]:
                text = next_line.strip()
                if text and not text.startswith("#") and not text.startswith("```"):
                    return text[:360]
            return stripped.lstrip("# ").strip()[:360]
    for line in lines:
        text = line.strip()
        if text:
            return text[:360]
    return ""


def status_files_under(root: Path) -> list[Path]:
    if not root.exists():
        return []
    files: list[Path] = []
    for child in root.rglob("*"):
        if not child.is_file():
            continue
        try:
            rel_parts = child.relative_to(root).parts
        except ValueError:
            rel_parts = child.parts
        if any(part in {".git", "node_modules", "__pycache__", "external_benchmarks", "envs"} for part in rel_parts):
            continue
        if child.suffix.lower() not in {".md", ".json", ".jsonl", ".txt", ".log"}:
            continue
        if STATUS_NAME_RE.search(child.name) or "research-output" in rel_parts or "synthesis" in rel_parts:
            files.append(child)
    return sorted(files, key=safe_mtime, reverse=True)


def configured_status_files(repo: Path, track: dict[str, Any]) -> list[Path]:
    globs = track.get("status_globs") or []
    files: list[Path] = []
    for pattern in globs:
        files.extend(p for p in repo.glob(pattern) if p.is_file())
    if files:
        return sorted(set(files), key=safe_mtime, reverse=True)
    roots = [repo / p for p in track.get("paths") or []]
    discovered: list[Path] = []
    for root in roots:
        discovered.extend(status_files_under(root))
    return sorted(set(discovered), key=safe_mtime, reverse=True)


@dataclass
class TrackRefs:
    forecast_refs: int = 0
    gp233_refs: int = 0
    catch_refs: int = 0
    experiment_refs: int = 0
    evidence_refs: list[str] | None = None


def blob_has_alias(blob: str, aliases: list[str]) -> bool:
    low = blob.lower()
    return any(alias.lower() in low for alias in aliases)


def refs_for_track(
    repo: Path,
    track: dict[str, Any],
    gp233_rows: list[dict[str, Any]],
    forecast_latest: list[dict[str, Any]],
    catch_rows: list[dict[str, Any]],
    experiment_rows: list[dict[str, Any]],
) -> TrackRefs:
    aliases = list(track.get("aliases") or [])
    evidence: list[str] = []
    gp233_count = 0
    for row in gp233_rows:
        blob = " ".join(str(row.get(k) or "") for k in ("lane", "evidence_pointer", "bottleneck", "decision_changed"))
        if blob_has_alias(blob, aliases):
            gp233_count += 1
            if row.get("evidence_pointer"):
                evidence.append(str(row["evidence_pointer"])[:220])
    forecast_count = 0
    for row in forecast_latest:
        blob = " ".join(str(row.get(k) or "") for k in ("contract_id", "question", "source"))
        if blob_has_alias(blob, aliases):
            forecast_count += 1
            if row.get("source"):
                evidence.append(str(row["source"]))
    catch_count = 0
    for row in catch_rows:
        if blob_has_alias(json.dumps(row, sort_keys=True), aliases):
            catch_count += 1
            evidence.append(rel(repo, repo / CATCH))
    experiment_count = 0
    for row in experiment_rows:
        if blob_has_alias(json.dumps(row, sort_keys=True), aliases):
            experiment_count += 1
            evidence.append(rel(repo, repo / EXPERIMENT_LEDGER))
    return TrackRefs(forecast_count, gp233_count, catch_count, experiment_count, evidence[:12])


def extract_focus_tracks(
    repo: Path,
    gp233_rows: list[dict[str, Any]],
    forecast_latest: list[dict[str, Any]],
    catch_rows: list[dict[str, Any]],
    experiment_rows: list[dict[str, Any]],
    *,
    freshness_days: int,
) -> dict[str, Any]:
    now_ts = datetime.now(timezone.utc).timestamp()
    freshness_s = freshness_days * 86400
    rows: list[dict[str, Any]] = []
    for track_id, track in FOCUS_TRACKS.items():
        roots = [repo / p for p in track.get("paths") or []]
        status_files = configured_status_files(repo, track)
        latest_file = status_files[0] if status_files else next((root for root in roots if root.exists()), roots[0])
        latest_ts = safe_mtime(latest_file)
        refs = refs_for_track(repo, track, gp233_rows, forecast_latest, catch_rows, experiment_rows)
        fresh = latest_ts and (now_ts - latest_ts) <= freshness_s
        active_by_refs = refs.forecast_refs or refs.gp233_refs or refs.experiment_refs
        linkage = "strong" if refs.forecast_refs or refs.gp233_refs or refs.experiment_refs else "medium" if fresh else "weak"
        evidence_refs = [rel(repo, p) for p in status_files[:6]]
        evidence_refs.extend(refs.evidence_refs or [])
        rows.append({
            "track_id": track_id,
            "label": track.get("label") or track_id,
            "paths": [rel(repo, p) for p in roots],
            "latest_touch": iso_from_mtime(latest_file),
            "latest_touch_source": rel(repo, latest_file),
            "activity_state": "active" if fresh or active_by_refs else "stale",
            "linkage_quality": linkage,
            "signals": {
                "forecast_refs": refs.forecast_refs,
                "gp233_refs": refs.gp233_refs,
                "catch_refs": refs.catch_refs,
                "experiment_refs": refs.experiment_refs,
                "status_files": len(status_files),
            },
            "latest_summary": markdown_summary(latest_file),
            "evidence_refs": evidence_refs[:14],
        })
    rows.sort(
        key=lambda r: (
            {"strong": 3, "medium": 2, "weak": 1}.get(str(r["linkage_quality"]), 0),
            str(r.get("latest_touch") or ""),
        ),
        reverse=True,
    )
    return {
        "summary": {
            "total_indexed": len(rows),
            "active": sum(1 for r in rows if r["activity_state"] == "active"),
            "strong_linkage": sum(1 for r in rows if r["linkage_quality"] == "strong"),
            "freshness_days": freshness_days,
            "note": "Focus tracks are configured joins over durable artifacts; they are not project authority.",
        },
        "rows": rows,
    }


def summarize_telemetry(repo: Path) -> dict[str, Any]:
    files = list((repo / "projects").glob("*/workspace/iteration_telemetry.jsonl"))
    latest = sorted(files, key=safe_mtime, reverse=True)[:12]
    return {
        "iteration_telemetry_files": len(files),
        "latest": [{"path": rel(repo, p), "latest_touch": iso_from_mtime(p)} for p in latest],
    }


def summarize_reflexive(repo: Path) -> dict[str, Any]:
    p0 = read_json(repo / P0_METRICS, {})
    rg = read_json(repo / RECURSIVE_GAIN, {})
    bif = read_json(repo / BIFURCATION, {})
    metrics = p0.get("metrics") if isinstance(p0, dict) else []
    status_counts: Counter[str] = Counter()
    tier_counts: Counter[str] = Counter()
    if isinstance(metrics, list):
        for metric in metrics:
            if isinstance(metric, dict):
                status_counts[str(metric.get("status") or "unknown")] += 1
                tier_counts[str(metric.get("tier") or "unknown")] += 1
    return {
        "p0_metric_count": len(metrics) if isinstance(metrics, list) else 0,
        "p0_status_counts": dict(status_counts.most_common()),
        "p0_tier_counts": dict(tier_counts.most_common()),
        "recursive_gain_candidates": rg.get("n_candidates") if isinstance(rg, dict) else None,
        "out_of_loop_share": ((bif.get("bifurcation") or {}).get("agent_work_share") if isinstance(bif, dict) else None),
        "sources": [rel(repo, repo / P0_METRICS), rel(repo, repo / RECURSIVE_GAIN), rel(repo, repo / BIFURCATION)],
    }


def count_json_records(payload: Any) -> int | None:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        for key in ("rows", "items", "metrics", "candidates", "weeks", "nodes", "edges"):
            value = payload.get(key)
            if isinstance(value, list):
                return len(value)
            if isinstance(value, dict):
                return len(value)
        return len(payload)
    return None


def summarize_dashboard_sources(repo: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    for name, rel_path in DASHBOARD_SOURCES.items():
        path = repo / rel_path
        payload = read_json(path, None)
        if payload is None:
            missing.append(name)
            rows.append({
                "name": name,
                "source": rel(repo, path),
                "present": False,
                "record_count": None,
                "latest_touch": None,
            })
            continue
        rows.append({
            "name": name,
            "source": rel(repo, path),
            "present": True,
            "record_count": count_json_records(payload),
            "latest_touch": iso_from_mtime(path),
        })
    return {
        "source": "analytics/public/dashboard/scripts/refresh-data.sh",
        "present": sum(1 for row in rows if row["present"]),
        "missing": missing,
        "rows": rows,
    }


def last_numeric(curve: dict[str, Any]) -> float | None:
    values: list[tuple[str, float]] = []
    for key, value in curve.items():
        try:
            values.append((str(key), float(value)))
        except (TypeError, ValueError):
            continue
    if not values:
        return None
    values.sort(key=lambda item: item[0])
    return values[-1][1]


def previous_numeric(curve: dict[str, Any]) -> float | None:
    values: list[tuple[str, float]] = []
    for key, value in curve.items():
        try:
            values.append((str(key), float(value)))
        except (TypeError, ValueError):
            continue
    if len(values) < 2:
        return None
    values.sort(key=lambda item: item[0])
    return values[-2][1]


def pct_change(previous: float | None, current: float | None) -> float | None:
    if previous is None or current is None or previous == 0:
        return None
    return round((current - previous) / abs(previous), 4)


def summarize_activity_yield(repo: Path, experiment_ledger: dict[str, Any]) -> dict[str, Any]:
    payload = read_json(repo / DASHBOARD_SOURCES["trajectory_curves"], {})
    curves = payload.get("curves") if isinstance(payload, dict) else {}
    if not isinstance(curves, dict):
        return {"available": False, "source": rel(repo, repo / DASHBOARD_SOURCES["trajectory_curves"])}
    activity_names = ["confound_a_code_activity_density", "confound_b_total_artifact_creation_per_week"]
    yield_names = ["insight_a_f_row_creates_per_week", "insight_b_f_row_closures_per_week", "insight_e_verified_axioms_added_per_week"]
    activity_now = sum((last_numeric(curves.get(name) or {}) or 0) for name in activity_names)
    activity_prev = sum((previous_numeric(curves.get(name) or {}) or 0) for name in activity_names)
    yield_now = sum((last_numeric(curves.get(name) or {}) or 0) for name in yield_names)
    yield_prev = sum((previous_numeric(curves.get(name) or {}) or 0) for name in yield_names)
    activity_delta = pct_change(activity_prev, activity_now)
    yield_delta = pct_change(yield_prev, yield_now)
    divergence = None
    if activity_delta is not None and yield_delta is not None:
        divergence = round(activity_delta - yield_delta, 4)
    verdict = "insufficient_data"
    if divergence is not None:
        if divergence > 0.5:
            verdict = "activity_outpacing_yield"
        elif divergence < -0.5:
            verdict = "yield_outpacing_activity"
        else:
            verdict = "roughly_aligned"
    return {
        "available": True,
        "source": rel(repo, repo / DASHBOARD_SOURCES["trajectory_curves"]),
        "activity_current": activity_now,
        "activity_previous": activity_prev,
        "yield_current": yield_now,
        "yield_previous": yield_prev,
        "activity_delta_pct": activity_delta,
        "yield_delta_pct": yield_delta,
        "activity_yield_divergence": divergence,
        "verdict": verdict,
        "experiment_rows": experiment_ledger.get("row_count"),
        "finding_rows": experiment_ledger.get("finding_rows"),
        "caveat": "Trajectory curves are self-produced and confounded by general artifact volume; use only as an attention signal.",
    }


def summarize_learning_candidate_lifecycle(repo: Path, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    search_roots = [
        repo / "research_areas/seams",
        repo / "research_areas/specs",
        repo / "org/patterns",
        repo / "org/anti-patterns",
        repo / "src/ztare",
    ]
    files: list[Path] = []
    for root in search_roots:
        if root.exists():
            files.extend(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in {".md", ".py", ".yaml", ".yml", ".json"})
    files = [
        p for p in files
        if "GP-244_research_operations_intelligence_cockpit" not in p.name
        and p.name != "operations_intelligence.py"
    ]
    rows: list[dict[str, Any]] = []
    promoted = 0
    for candidate in candidates:
        tokens = [str(candidate.get("candidate_id") or ""), str(candidate.get("object_ref") or "")]
        tokens.extend(str(x) for x in candidate.get("source_refs") or [])
        tokens = [t for t in tokens if len(t) >= 8]
        refs: list[str] = []
        for path in files:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if any(token in text for token in tokens):
                refs.append(rel(repo, path))
            if len(refs) >= 6:
                break
        if refs:
            promoted += 1
        rows.append({
            "candidate_id": candidate.get("candidate_id"),
            "transition_kind": candidate.get("transition_kind"),
            "object_ref": candidate.get("object_ref"),
            "status": "referenced" if refs else "observer_only_unresolved",
            "refs": refs,
        })
    return {
        "candidate_count": len(candidates),
        "referenced_count": promoted,
        "unresolved_count": len(candidates) - promoted,
        "promotion_rate_proxy": round(promoted / len(candidates), 4) if candidates else None,
        "caveat": "Reference matching is a proxy. It does not prove a membrane-approved learning transition.",
        "rows": rows,
    }


def recurrence_suppression_candidates(catch: dict[str, Any], gp233: dict[str, Any]) -> dict[str, Any]:
    top = catch.get("top_categories") or []
    recent = {row.get("name"): row.get("count") for row in (catch.get("recent_categories") or [])}
    bottleneck_blob = " ".join(str(row.get("name") or "") for row in (gp233.get("top_bottlenecks") or [])).lower()
    rows: list[dict[str, Any]] = []
    for row in top[:10]:
        name = str(row.get("name") or "unknown")
        count = int(row.get("count") or 0)
        recent_count = int(recent.get(name) or 0)
        priority = "p1" if recent_count else "p2"
        if count >= 10 and recent_count:
            priority = "p0"
        rows.append({
            "category": name,
            "total_count": count,
            "recent_count_last40": recent_count,
            "priority": priority,
            "gp233_name_overlap": name.lower() in bottleneck_blob,
            "recommended_metric": "recurrence_suppression_rate",
            "review_question": "Did this failure mode stop recurring after the relevant catch or preconditioner was introduced?",
        })
    return {
        "source": catch.get("source"),
        "candidate_count": len(rows),
        "rows": rows,
    }


def metric_caveats() -> list[dict[str, Any]]:
    return [
        {
            "metric": "forecast_decision_use_rate",
            "decision_supported": "whether GP-230 can be treated as allocation evidence",
            "denominator": "forecast aggregate files",
            "failure_mode": "market forecasts become calibration-only if action consumption is not logged",
        },
        {
            "metric": "activity_yield_divergence",
            "decision_supported": "whether activity growth reflects insight or busywork",
            "denominator": "weekly trajectory curves",
            "failure_mode": "file churn and artifact volume can look like research progress",
        },
        {
            "metric": "learning_candidate_lifecycle",
            "decision_supported": "whether observer-only insights become reusable apparatus changes",
            "denominator": "learning candidates emitted by intelligence surfaces",
            "failure_mode": "text references are not proof of adoption or causal effect",
        },
        {
            "metric": "recurrence_suppression_rate",
            "decision_supported": "whether catch/amnesia mechanisms reduce repeated failures",
            "denominator": "catch categories and later run/catch occurrences",
            "failure_mode": "vocabulary drift can hide recurrence under a new name",
        },
        {
            "metric": "source_health_blocker_days",
            "decision_supported": "whether the intelligence surface is trustworthy enough to consume",
            "denominator": "source-health issues",
            "failure_mode": "missing emitters can make low counts look healthy",
        },
    ]


def metric_area_interface() -> dict[str, Any]:
    status_counts = Counter(str(area.get("status") or "unknown") for area in RESEARCH_OPS_METRIC_AREAS)
    return {
        "schema": "ztare-research-ops-metric-areas-v1",
        "area_count": len(RESEARCH_OPS_METRIC_AREAS),
        "status_counts": dict(status_counts.most_common()),
        "areas": RESEARCH_OPS_METRIC_AREAS,
    }


def build_process_input_metrics(payload: dict[str, Any]) -> dict[str, Any]:
    fm = payload.get("forecast_market") or {}
    source_health_summary = payload.get("source_health_summary") or {}
    scientific_yield = payload.get("scientific_yield") or {}
    catch = payload.get("catch_and_risk") or {}
    lifecycle = payload.get("learning_candidate_lifecycle") or {}
    dashboard_sources = payload.get("dashboard_sources") or {}
    action_summary = ((payload.get("action_intelligence") or {}).get("summary") or {})
    values = {
        "decision_use_logging": {
            "current": fm.get("decision_use_rate"),
            "numerator": fm.get("decision_use_rows"),
            "denominator": fm.get("aggregates"),
            "status": "source_blocked" if fm.get("decision_use_gap") else "ok",
        },
        "source_health_repair": {
            "current": source_health_summary.get("blocking_count"),
            "denominator": source_health_summary.get("issue_count"),
            "status": "blocked" if source_health_summary.get("blocking_count") else "ok",
        },
        "structured_yield_logging": {
            "current": scientific_yield.get("row_count"),
            "denominator": scientific_yield.get("row_count"),
            "status": "source_gap" if any(row.get("source_id") == "gp233_scientific_yield" for row in (payload.get("source_improvement_backlog") or [])) else "partial",
        },
        "catch_preconditioner_consumption": {
            "current": action_summary.get("consumed_surfacing_events"),
            "denominator": catch.get("consequential"),
            "status": "source_blocked" if not action_summary.get("consumed_surfacing_events") else "partial",
        },
        "learning_candidate_review": {
            "current": lifecycle.get("promotion_rate_proxy"),
            "numerator": lifecycle.get("referenced_count"),
            "denominator": lifecycle.get("candidate_count"),
            "status": "proxy_only",
        },
        "dashboard_feed_freshness": {
            "current": dashboard_sources.get("present"),
            "denominator": len((dashboard_sources.get("rows") or [])),
            "status": "ok" if not dashboard_sources.get("missing") else "missing_feeds",
        },
        "hard_tick_depth_receipt_quality": {
            "current": None,
            "denominator": None,
            "status": "source_gap",
        },
        "human_unblock_logging": {
            "current": None,
            "denominator": None,
            "status": "source_gap",
        },
    }
    rows: list[dict[str, Any]] = []
    for contract in PROCESS_INPUT_METRIC_CONTRACTS:
        value = values.get(str(contract["metric_id"]), {})
        rows.append({**contract, **value})
    status_counts = Counter(str(row.get("status") or "unknown") for row in rows)
    return {
        "schema": "ztare-process-input-metrics-v1",
        "philosophy": "Controllable inputs and process health are paired with downstream outputs; they are not final research outcomes.",
        "status_counts": dict(status_counts.most_common()),
        "rows": rows,
    }


def build_source_map(payload: dict[str, Any]) -> dict[str, Any]:
    rows = [
        {
            "source_id": "gp230_forecast_pool",
            "source_refs": (payload.get("forecast_market") or {}).get("source_health_refs") or [],
            "feeds": ["forecast_market", "attention", "learning_candidates", "research_ops_metrics"],
            "aggregate_fields": ["contracts", "aggregates", "outcomes", "scores", "decision_use_rows", "decision_use_rate"],
            "source_gaps": [
                "decision_use rows are sparse relative to forecast aggregates"
            ] if (payload.get("forecast_market") or {}).get("decision_use_gap") else [],
        },
        {
            "source_id": "gp233_scientific_yield",
            "source_refs": [(payload.get("scientific_yield") or {}).get("source")],
            "feeds": ["scientific_yield", "focus_tracks", "learning_candidates", "research_ops_metrics"],
            "aggregate_fields": ["row_count", "verdict_counts", "top_bottlenecks"],
            "source_gaps": [
                "markdown-only linkage limits structured joins"
            ] if any(issue.get("issue_type") == "weak_gp233_linkage" for issue in ((payload.get("source_health") or {}).get("issues") or [])) else [],
        },
        {
            "source_id": "experiment_track_record",
            "source_refs": [(payload.get("experiment_ledger") or {}).get("source")],
            "feeds": ["experiment_ledger", "focus_tracks", "activity_yield", "research_ops_metrics"],
            "aggregate_fields": ["row_count", "finding_rows", "status_counts", "kind_counts"],
            "source_gaps": ["wide prose table cells need a derived structured read model"],
        },
        {
            "source_id": "catch_ledger",
            "source_refs": [(payload.get("catch_and_risk") or {}).get("source")],
            "feeds": ["catch_and_risk", "recurrence_suppression_candidates", "focus_tracks"],
            "aggregate_fields": ["rows", "ratified", "consequential", "top_categories", "recent_categories"],
            "source_gaps": ["catch categories need later recurrence/avoidance labels to estimate suppression"],
        },
        {
            "source_id": "action_intelligence",
            "source_refs": [
                "analytics/public/action_intelligence/state/source_health.json",
                "analytics/public/action_intelligence/state/action_intelligence.json",
                "analytics/public/ledgers/action_intelligence/action_impact_ledger.jsonl",
            ],
            "feeds": ["source_health", "action_intelligence", "attention", "learning_candidates"],
            "aggregate_fields": ["source_health issues", "shadow recommendations", "action impact rows"],
            "source_gaps": [
                "action-impact and surfacing-consumption rows are still thin"
            ],
        },
        {
            "source_id": "trajectory_dashboard_feeds",
            "source_refs": [row.get("source") for row in (payload.get("dashboard_sources") or {}).get("rows", [])],
            "feeds": ["dashboard_sources", "activity_yield", "reflexive_intelligence"],
            "aggregate_fields": ["feed freshness", "record counts", "activity_yield_divergence"],
            "source_gaps": ["self-produced trajectory metrics need caveats and decision-use follow-through"],
        },
        {
            "source_id": "focus_track_artifacts",
            "source_refs": [ref for row in (payload.get("focus_tracks") or {}).get("rows", []) for ref in row.get("evidence_refs", [])[:3]],
            "feeds": ["focus_tracks"],
            "aggregate_fields": ["latest_touch", "activity_state", "linkage_quality", "signals"],
            "source_gaps": [
                "focus tracks are configured joins, not standardized project records"
            ],
        },
    ]
    return {
        "schema": "ztare-intelligence-source-map-v1",
        "rows": rows,
        "gap_count": sum(len(row.get("source_gaps") or []) for row in rows),
    }


def source_improvement_backlog(source_map: dict[str, Any]) -> list[dict[str, Any]]:
    backlog: list[dict[str, Any]] = []
    priority_by_source = {
        "gp230_forecast_pool": "p0",
        "action_intelligence": "p0",
        "gp233_scientific_yield": "p1",
        "experiment_track_record": "p1",
        "catch_ledger": "p1",
        "trajectory_dashboard_feeds": "p2",
        "focus_track_artifacts": "p2",
    }
    for row in source_map.get("rows") or []:
        for gap in row.get("source_gaps") or []:
            backlog.append({
                "priority": priority_by_source.get(str(row.get("source_id")), "p2"),
                "source_id": row.get("source_id"),
                "gap": gap,
                "recommended_action": "improve_source_emitter_or_schema",
                "why_source_not_report": "Fixing this at the source improves every downstream consumer of the intelligence layer.",
                "source_refs": row.get("source_refs") or [],
            })
    backlog.sort(key=lambda item: {"p0": 0, "p1": 1, "p2": 2}.get(str(item.get("priority")), 9))
    return backlog


def build_source_readiness(payload: dict[str, Any]) -> dict[str, Any]:
    source_map = payload.get("source_map") or {}
    backlog = payload.get("source_improvement_backlog") or []
    validation_issues = ((payload.get("etl_manifest") or {}).get("validate") or {}).get("issues") or []
    backlog_by_source: dict[str, list[dict[str, Any]]] = {}
    blocking_by_source = Counter()
    for row in backlog:
        backlog_by_source.setdefault(str(row.get("source_id")), []).append(row)
    for issue in validation_issues:
        if issue.get("severity") == "blocking":
            blocking_by_source[str(issue.get("source_id"))] += 1

    rows: list[dict[str, Any]] = []
    for row in source_map.get("rows") or []:
        source_id = str(row.get("source_id"))
        gaps = row.get("source_gaps") or []
        source_backlog = backlog_by_source.get(source_id, [])
        blocking_count = blocking_by_source.get(source_id, 0)
        if blocking_count:
            readiness = "blocked"
            score = 0.0
            use_now = "do_not_use_for_allocation"
        elif gaps:
            readiness = "partial"
            score = 0.5
            use_now = "use_for_triage_only"
        else:
            readiness = "ready"
            score = 1.0
            use_now = "usable_for_read_model"
        rows.append({
            "source_id": source_id,
            "readiness": readiness,
            "readiness_score": score,
            "use_now": use_now,
            "feeds": row.get("feeds") or [],
            "source_refs": row.get("source_refs") or [],
            "gap_count": len(gaps),
            "blocking_validation_issues": blocking_count,
            "next_source_fix": (source_backlog[0].get("gap") if source_backlog else None),
            "recommended_action": (source_backlog[0].get("recommended_action") if source_backlog else "keep_emitter_stable"),
        })
    status_counts = Counter(str(row.get("readiness")) for row in rows)
    return {
        "schema": "ztare-source-readiness-v1",
        "summary": {
            "source_count": len(rows),
            "ready": status_counts.get("ready", 0),
            "partial": status_counts.get("partial", 0),
            "blocked": status_counts.get("blocked", 0),
            "mean_readiness_score": round(sum(float(row.get("readiness_score") or 0.0) for row in rows) / max(1, len(rows)), 3),
        },
        "rows": rows,
    }


def build_executive_brief(payload: dict[str, Any]) -> dict[str, Any]:
    readiness = (payload.get("source_readiness") or {}).get("summary") or {}
    etl_validation = ((payload.get("etl_manifest") or {}).get("validate") or {})
    attention = payload.get("attention") or []
    backlog = payload.get("source_improvement_backlog") or []
    forecast = payload.get("forecast_market") or {}
    if etl_validation.get("blocking_count"):
        operating_status = "blocked_for_allocation"
        status_reason = "Blocking validation issues are present in the intelligence sources."
    elif readiness.get("partial") or readiness.get("blocked"):
        operating_status = "triage_ready"
        status_reason = "The surface can rank source gaps and focus areas, but some joins are still partial."
    else:
        operating_status = "ready_read_model"
        status_reason = "Configured sources emitted without detected source gaps."

    first_action = None
    if attention:
        first = attention[0]
        first_action = {
            "kind": first.get("kind"),
            "priority": first.get("priority"),
            "action": first.get("title"),
            "why": first.get("why"),
            "evidence_refs": first.get("evidence_refs") or [],
        }
    elif backlog:
        first = backlog[0]
        first_action = {
            "kind": "source_improvement",
            "priority": first.get("priority"),
            "action": first.get("gap"),
            "why": first.get("why_source_not_report"),
            "evidence_refs": first.get("source_refs") or [],
        }
    else:
        first_action = {
            "kind": "review",
            "priority": "p2",
            "action": "review intelligence surface",
            "why": "No p0/p1 attention row emitted.",
            "evidence_refs": [],
        }

    do_not_use_for = [
        "official scientific promotion or demotion without reading the source ledger",
        "autonomous route execution",
        "live bandit or reinforcement updates",
    ]
    if forecast.get("decision_use_gap"):
        do_not_use_for.append("forecast-market allocation claims until decision-use rows are emitted")
    return {
        "schema": "ztare-intelligence-executive-brief-v1",
        "operating_status": operating_status,
        "status_reason": status_reason,
        "source_readiness": readiness,
        "first_action": first_action,
        "operator_questions": [
            "Which p0 source gap would change the next research allocation if repaired?",
            "Which attention row is still only a proxy rather than a ledger-backed signal?",
            "Which learning candidate should remain observer-only until a source emitter proves it?",
        ],
        "do_not_use_for": do_not_use_for,
    }


def build_etl_manifest(payload: dict[str, Any]) -> dict[str, Any]:
    source_map = payload.get("source_map") or {}
    validation_issues: list[dict[str, Any]] = []
    for row in source_map.get("rows") or []:
        for gap in row.get("source_gaps") or []:
            validation_issues.append({
                "severity": "warning",
                "source_id": row.get("source_id"),
                "issue": gap,
                "stage": "validate",
            })
    for issue in (payload.get("source_health") or {}).get("issues") or []:
        if issue.get("severity") == "blocking":
            validation_issues.append({
                "severity": "blocking",
                "source_id": issue.get("scope") or issue.get("issue_type") or "source_health",
                "issue": issue.get("blocking_rule") or issue.get("issue_type"),
                "stage": "validate",
            })
    fm = payload.get("forecast_market") or {}
    if fm.get("aggregates") and fm.get("decision_use_rows") == 0:
        validation_issues.append({
            "severity": "blocking",
            "source_id": "gp230_forecast_pool",
            "issue": "forecast aggregates exist but no decision-use rows were found",
            "stage": "validate",
        })
    return {
        "schema": "ztare-intelligence-etl-v1",
        "extract": {
            "sources": [row.get("source_id") for row in source_map.get("rows") or []],
            "mode": "read_only_filesystem",
        },
        "transform": {
            "aggregates": [
                "focus_tracks",
                "forecast_market",
                "scientific_yield",
                "experiment_ledger",
                "reflexive_intelligence",
                "activity_yield",
                "recurrence_suppression_candidates",
                "learning_candidate_lifecycle",
            ],
            "join_policy": "configured_alias_and_source_reference_joins",
        },
        "validate": {
            "issue_count": len(validation_issues),
            "blocking_count": sum(1 for issue in validation_issues if issue.get("severity") == "blocking"),
            "issues": validation_issues,
        },
        "load": {
            "default_outputs": [
                rel(REPO, DEFAULT_JSON_OUT),
                rel(REPO, DEFAULT_MD_OUT),
            ],
            "optional_outputs": [rel(REPO, DEFAULT_HTML_OUT)],
            "writes_official_state": False,
        },
    }


def summarize_source_health(source_health: dict[str, Any], repo: Path) -> dict[str, Any]:
    issues = source_health.get("issues") or []
    blocking = [issue for issue in issues if issue.get("severity") == "blocking"]
    path = repo / ACTION_HEALTH
    latest = iso_from_mtime(path)
    return {
        "source": rel(repo, path),
        "issue_count": len(issues),
        "blocking_count": len(blocking),
        "latest_touch": latest,
        "blocker_days_proxy": None if not blocking else 0,
        "caveat": "Blocker age is a proxy until source-health issues carry first_seen timestamps.",
    }


def build_attention(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    source_health = payload.get("source_health") or {}
    for issue in (source_health.get("issues") or [])[:8]:
        sev = issue.get("severity")
        items.append({
            "priority": "p0" if sev == "blocking" else "p1",
            "kind": "source_health",
            "title": str(issue.get("issue_type") or "source issue"),
            "why": str(issue.get("blocking_rule") or issue.get("recommended_action") or ""),
            "evidence_refs": issue.get("evidence_refs") or [],
        })
    fm = payload.get("forecast_market") or {}
    if fm.get("decision_use_gap"):
        items.append({
            "priority": "p0" if fm.get("decision_use_rows") == 0 else "p1",
            "kind": "decision_use_gap",
            "title": f"{fm['decision_use_gap']} forecast aggregates without logged decision use",
            "why": "Market outputs need action consumption before they become allocation evidence.",
            "evidence_refs": fm.get("source_health_refs") or [],
        })
    if fm.get("unresolved_contracts"):
        items.append({
            "priority": "p1",
            "kind": "forecast_debt",
            "title": f"{fm['unresolved_contracts']} unresolved forecast contracts",
            "why": "Unresolved contracts weaken calibration and decision-use accounting.",
            "evidence_refs": fm.get("source_health_refs") or [],
        })
    tracks = (payload.get("focus_tracks") or {}).get("rows") or []
    weak_active = [p for p in tracks if p.get("activity_state") == "active" and p.get("linkage_quality") == "weak"]
    if weak_active:
        items.append({
            "priority": "p1",
            "kind": "focus_track_linkage",
            "title": f"{len(weak_active)} active focus tracks with weak ledger linkage",
            "why": "Artifacts exist, but forecast/yield/experiment joins are not strong enough for confident aggregation.",
            "evidence_refs": [p.get("paths", [""])[0] for p in weak_active[:5]],
        })
    divergence = payload.get("activity_yield") or {}
    if divergence.get("verdict") == "activity_outpacing_yield":
        items.append({
            "priority": "p1",
            "kind": "activity_yield_divergence",
            "title": "activity is outpacing measured yield",
            "why": "Trajectory curves show activity rising faster than insight/yield measures.",
            "evidence_refs": [divergence.get("source")],
        })
    return items[:12]


def candidate_id(kind: str, object_ref: str) -> str:
    raw = f"{kind}:{object_ref}"
    return "ztare-ltc-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def learning_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for issue in (payload.get("source_health") or {}).get("issues", [])[:8]:
        object_ref = ",".join(str(x) for x in issue.get("evidence_refs") or []) or str(issue.get("issue_type"))
        candidates.append({
            "candidate_id": candidate_id("source_repair", object_ref),
            "transition_kind": "source_repair",
            "severity": "blocking" if issue.get("severity") == "blocking" else "normal",
            "rationale": issue.get("blocking_rule") or issue.get("recommended_action") or "Repair source before treating aggregate as reliable.",
            "source_kind": "source_health",
            "object_ref": object_ref,
            "suggested_owner_role": "operator",
            "review_question": "Which emitter or ledger join should be repaired before this surface is trusted?",
            "source_refs": issue.get("evidence_refs") or [],
            "proposed_payload": {"issue_type": issue.get("issue_type"), "severity": issue.get("severity")},
            "observer_only": True,
        })
    fm = payload.get("forecast_market") or {}
    if fm.get("unresolved_contracts"):
        candidates.append({
            "candidate_id": candidate_id("forecast_contract", "unresolved_contracts"),
            "transition_kind": "forecast_contract",
            "severity": "normal",
            "rationale": "Close or explicitly defer unresolved contracts so the market becomes calibration evidence.",
            "source_kind": "forecast_market",
            "object_ref": "unresolved_contracts",
            "suggested_owner_role": "research_director",
            "review_question": "Which open contract should be closed, rescored, or retired before the next attention cycle?",
            "source_refs": fm.get("source_health_refs") or [],
            "proposed_payload": {"unresolved_contracts": fm.get("unresolved_contracts")},
            "observer_only": True,
        })
    for row in (payload.get("scientific_yield") or {}).get("top_bottlenecks", [])[:5]:
        name = str(row.get("name") or "")
        if not name:
            continue
        candidates.append({
            "candidate_id": candidate_id("route_or_routine_review", name),
            "transition_kind": "route_or_routine_review",
            "severity": "normal",
            "rationale": f"Recurring GP-233 bottleneck appears {row.get('count')} times.",
            "source_kind": "scientific_yield",
            "object_ref": name,
            "suggested_owner_role": "operator",
            "review_question": "Is this a true research obstruction, an apparatus routine to improve, or a branch to retire?",
            "source_refs": [(payload.get("scientific_yield") or {}).get("source")],
            "proposed_payload": {"bottleneck": name, "count": row.get("count")},
            "observer_only": True,
        })
    return candidates[:16]


def build(repo: Path = REPO, *, freshness_days: int = 14, max_projects: int = 30) -> dict[str, Any]:
    del max_projects  # retained for CLI compatibility with the earlier project extractor.
    gp233 = parse_gp233(repo)
    experiment_ledger = parse_experiment_ledger(repo)
    forecast = summarize_forecast_market(repo)
    catch = summarize_catches(repo)
    source_health = read_json(repo / ACTION_HEALTH, {"issues": [], "counts": {}})
    action_state = read_json(repo / ACTION_STATE, {})
    dashboard_sources = summarize_dashboard_sources(repo)
    activity_yield = summarize_activity_yield(repo, experiment_ledger)
    recursive_learning = summarize_reflexive(repo)
    focus_tracks = extract_focus_tracks(
        repo,
        gp233.get("rows") or [],
        forecast.get("latest_aggregates") or [],
        read_jsonl(repo / CATCH),
        experiment_ledger.get("rows") or [],
        freshness_days=freshness_days,
    )
    payload: dict[str, Any] = {
        "schema": "ztare-intelligence-surface-v1",
        "generated_at": utc_now(),
        "headline": {
            "active_focus_tracks": focus_tracks["summary"].get("active"),
            "strong_focus_linkage": focus_tracks["summary"].get("strong_linkage"),
            "forecast_contracts": forecast.get("contracts"),
            "forecast_unresolved": forecast.get("unresolved_contracts"),
            "gp233_rows": gp233.get("row_count"),
            "experiment_rows": experiment_ledger.get("row_count"),
            "finding_rows": experiment_ledger.get("finding_rows"),
            "catch_rows": catch.get("rows"),
            "source_health_blockers": (source_health.get("counts") or {}).get("blocking"),
            "dashboard_sources_present": dashboard_sources.get("present"),
            "forecast_decision_use_rate": forecast.get("decision_use_rate"),
            "activity_yield_verdict": activity_yield.get("verdict"),
        },
        "focus_tracks": focus_tracks,
        "forecast_market": forecast,
        "scientific_yield": {k: v for k, v in gp233.items() if k != "rows"},
        "experiment_ledger": {k: v for k, v in experiment_ledger.items() if k != "rows"},
        "reflexive_intelligence": recursive_learning,
        "catch_and_risk": catch,
        "telemetry": summarize_telemetry(repo),
        "source_health": source_health,
        "source_health_summary": summarize_source_health(source_health, repo),
        "action_intelligence": action_state,
        "dashboard_sources": dashboard_sources,
        "activity_yield": activity_yield,
        "recurrence_suppression_candidates": recurrence_suppression_candidates(catch, gp233),
        "metric_caveats": metric_caveats(),
        "research_ops_metric_areas": metric_area_interface(),
    }
    payload["attention"] = build_attention(payload)
    payload["learning_candidates"] = learning_candidates(payload)
    payload["learning_candidate_lifecycle"] = summarize_learning_candidate_lifecycle(repo, payload["learning_candidates"])
    payload["source_map"] = build_source_map(payload)
    payload["source_improvement_backlog"] = source_improvement_backlog(payload["source_map"])
    payload["etl_manifest"] = build_etl_manifest(payload)
    payload["source_readiness"] = build_source_readiness(payload)
    payload["process_input_metrics"] = build_process_input_metrics(payload)
    payload["executive_brief"] = build_executive_brief(payload)
    return payload


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    lines = [
        "# ZTARE Intelligence Surface",
        "",
        f"Generated: `{payload.get('generated_at')}`",
        "",
        "This is a private read model. It does not replace source ledgers or write official state.",
        "",
    ]
    brief = payload.get("executive_brief") or {}
    first_action = brief.get("first_action") or {}
    lines.extend(["## Executive Brief", ""])
    lines.append(f"- operating status: `{brief.get('operating_status')}`")
    lines.append(f"- reason: {brief.get('status_reason')}")
    lines.append(f"- first action: `{first_action.get('priority')}` `{first_action.get('kind')}` - {first_action.get('action')}")
    lines.append(f"- why: {first_action.get('why')}")
    lines.append(f"- source readiness: `{brief.get('source_readiness')}`")
    lines.append("- do not use for:")
    for item in brief.get("do_not_use_for") or []:
        lines.append(f"  - {item}")
    lines.append("- operator questions:")
    for item in brief.get("operator_questions") or []:
        lines.append(f"  - {item}")
    lines.extend(["", "## Headline", ""])
    for key, value in (payload.get("headline") or {}).items():
        lines.append(f"- `{key}`: {value}")
    lines.extend(["", "## Attention", ""])
    for item in payload.get("attention") or []:
        lines.append(f"- **{item.get('priority')} / {item.get('kind')}**: {item.get('title')} - {item.get('why')}")
    lines.extend(["", "## Learning Candidates", ""])
    for item in payload.get("learning_candidates") or []:
        lines.append(
            f"- `{item.get('transition_kind')}` `{item.get('candidate_id')}`: {item.get('review_question')} "
            f"(observer_only={item.get('observer_only')})"
        )
    lines.extend(["", "## Focus Tracks", ""])
    lines.append("| Track | State | Linkage | Forecast | GP-233 | Experiments | Latest |")
    lines.append("|---|---|---|---:|---:|---:|---|")
    for row in (payload.get("focus_tracks") or {}).get("rows", []):
        sig = row.get("signals") or {}
        lines.append(
            f"| `{row.get('track_id')}` | {row.get('activity_state')} | {row.get('linkage_quality')} | "
            f"{sig.get('forecast_refs')} | {sig.get('gp233_refs')} | {sig.get('experiment_refs')} | "
            f"`{row.get('latest_touch_source')}` |"
        )
    lines.extend(["", "## Scientific Yield Bottlenecks", ""])
    for row in (payload.get("scientific_yield") or {}).get("top_bottlenecks", [])[:10]:
        lines.append(f"- `{row.get('name')}`: {row.get('count')}")
    lines.extend(["", "## Forecast Market", ""])
    fm = payload.get("forecast_market") or {}
    lines.append(f"- contracts: {fm.get('contracts')}")
    lines.append(f"- unresolved contracts: {fm.get('unresolved_contracts')}")
    lines.append(f"- decision-use rows: {fm.get('decision_use_rows')}")
    lines.append(f"- decision-use gap: {fm.get('decision_use_gap')}")
    lines.append(f"- decision-use rate: {fm.get('decision_use_rate')}")
    lines.extend(["", "## Activity vs Yield", ""])
    ay = payload.get("activity_yield") or {}
    lines.append(f"- verdict: `{ay.get('verdict')}`")
    lines.append(f"- activity delta pct: {ay.get('activity_delta_pct')}")
    lines.append(f"- yield delta pct: {ay.get('yield_delta_pct')}")
    lines.extend(["", "## Research Ops Metric Areas", ""])
    for area in (payload.get("research_ops_metric_areas") or {}).get("areas", []):
        lines.append(f"- `{area.get('area_id')}` `{area.get('status')}`: {area.get('source_gap')}")
    lines.extend(["", "## Process/Input Metrics", ""])
    pim = payload.get("process_input_metrics") or {}
    lines.append(f"- status counts: `{pim.get('status_counts')}`")
    for row in pim.get("rows", []):
        lines.append(
            f"- `{row.get('metric_id')}` `{row.get('metric_kind')}` `{row.get('status')}`: "
            f"current={row.get('current')} denominator={row.get('denominator')} -> {row.get('downstream_output')}"
        )
    lines.extend(["", "## Learning Candidate Lifecycle", ""])
    lifecycle = payload.get("learning_candidate_lifecycle") or {}
    lines.append(f"- candidates: {lifecycle.get('candidate_count')}")
    lines.append(f"- referenced proxy count: {lifecycle.get('referenced_count')}")
    lines.append(f"- unresolved: {lifecycle.get('unresolved_count')}")
    lines.extend(["", "## Experiment Ledger", ""])
    el = payload.get("experiment_ledger") or {}
    lines.append(f"- rows: {el.get('row_count')}")
    lines.append(f"- finding rows: {el.get('finding_rows')}")
    lines.extend(["", "## Dashboard Source Feeds", ""])
    for row in (payload.get("dashboard_sources") or {}).get("rows", []):
        lines.append(f"- `{row.get('name')}`: present={row.get('present')} records={row.get('record_count')} source=`{row.get('source')}`")
    lines.extend(["", "## Source Map", ""])
    source_map = payload.get("source_map") or {}
    lines.append(f"- gap count: {source_map.get('gap_count')}")
    for row in (source_map.get("rows") or [])[:10]:
        lines.append(f"- `{row.get('source_id')}` -> {', '.join(row.get('feeds') or [])}; gaps={len(row.get('source_gaps') or [])}")
    lines.extend(["", "## Source Readiness", ""])
    source_readiness = payload.get("source_readiness") or {}
    lines.append(f"- summary: `{source_readiness.get('summary')}`")
    lines.append("| Source | Readiness | Use Now | Gaps | Blocking | Next Source Fix |")
    lines.append("|---|---|---|---:|---:|---|")
    for row in source_readiness.get("rows", []):
        lines.append(
            f"| `{row.get('source_id')}` | {row.get('readiness')} | {row.get('use_now')} | "
            f"{row.get('gap_count')} | {row.get('blocking_validation_issues')} | {row.get('next_source_fix') or ''} |"
        )
    lines.extend(["", "## ETL Manifest", ""])
    etl = payload.get("etl_manifest") or {}
    validation = etl.get("validate") or {}
    lines.append(f"- sources: {len((etl.get('extract') or {}).get('sources') or [])}")
    lines.append(f"- validation issues: {validation.get('issue_count')}")
    lines.append(f"- blocking validation issues: {validation.get('blocking_count')}")
    lines.extend(["", "## Source Improvement Backlog", ""])
    for row in payload.get("source_improvement_backlog") or []:
        lines.append(f"- `{row.get('priority')}` `{row.get('source_id')}`: {row.get('gap')}")
    lines.extend(["", "## Recurrence Suppression Candidates", ""])
    for row in (payload.get("recurrence_suppression_candidates") or {}).get("rows", [])[:8]:
        lines.append(f"- `{row.get('priority')}` `{row.get('category')}`: total={row.get('total_count')} recent={row.get('recent_count_last40')}")
    lines.extend(["", "## Metric Caveats", ""])
    for row in payload.get("metric_caveats") or []:
        lines.append(f"- `{row.get('metric')}`: {row.get('failure_mode')}")
    lines.extend(["", "## Source Health", ""])
    for issue in (payload.get("source_health") or {}).get("issues", [])[:10]:
        lines.append(f"- `{issue.get('severity')}` `{issue.get('issue_type')}`: {issue.get('blocking_rule')}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_html(payload: dict[str, Any], path: Path) -> None:
    payload_json = json.dumps(payload, ensure_ascii=True, sort_keys=True).replace("</", "<\\/")
    doc = f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ZTARE Intelligence Surface</title>
<style>
* {{ box-sizing: border-box; }}
:root {{
  --bg: #f4f1eb;
  --panel: #fffaf2;
  --panel2: #ffffff;
  --ink: #1d1a16;
  --muted: #766d60;
  --line: #d8cec0;
  --p0: #ad2f2f;
  --p1: #9a6a12;
  --p2: #57677a;
  --ok: #2e6e4c;
  --blue: #315f8c;
}}
body {{ margin: 0; font: 14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color: var(--ink); background: var(--bg); }}
button, input {{ font: inherit; }}
.shell {{ max-width: 1440px; margin: 0 auto; padding: 24px; }}
.top {{ display: grid; grid-template-columns: 1fr auto; gap: 16px; align-items: end; margin-bottom: 14px; }}
h1 {{ font-size: 30px; margin: 0; letter-spacing: 0; }}
.sub {{ color: var(--muted); margin-top: 4px; max-width: 780px; }}
.stamp {{ text-align: right; color: var(--muted); font-size: 12px; }}
.toolbar {{ display: flex; gap: 10px; align-items: center; margin: 16px 0; flex-wrap: wrap; }}
.tabs {{ display: flex; gap: 8px; flex-wrap: wrap; }}
.tab {{ border: 1px solid var(--line); background: var(--panel); border-radius: 8px; padding: 7px 11px; cursor: pointer; color: var(--ink); }}
.tab.active {{ background: var(--ink); color: var(--panel); border-color: var(--ink); }}
.search {{ min-width: 260px; flex: 1; border: 1px solid var(--line); border-radius: 8px; padding: 8px 10px; background: var(--panel2); }}
.grid {{ display: grid; grid-template-columns: repeat(12, 1fr); gap: 12px; }}
.card {{ grid-column: span 3; min-height: 92px; border: 1px solid var(--line); border-radius: 8px; background: var(--panel); padding: 13px; }}
.card.wide {{ grid-column: span 6; }}
.card.full {{ grid-column: 1 / -1; }}
.k {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }}
.v {{ font-size: 25px; font-weight: 700; margin-top: 6px; }}
.note {{ color: var(--muted); font-size: 12px; margin-top: 5px; }}
.section {{ display: none; }}
.section.active {{ display: block; }}
h2 {{ font-size: 19px; margin: 22px 0 10px; }}
h3 {{ font-size: 15px; margin: 0 0 8px; }}
.rowlist {{ display: grid; gap: 8px; }}
.item {{ border: 1px solid var(--line); border-radius: 8px; background: var(--panel2); padding: 10px 12px; }}
.item-head {{ display: flex; gap: 8px; align-items: center; justify-content: space-between; }}
.pill {{ display: inline-flex; align-items: center; height: 22px; padding: 0 7px; border-radius: 999px; border: 1px solid var(--line); background: var(--panel); font-size: 12px; white-space: nowrap; }}
.p0 {{ color: var(--p0); border-color: #d59b9b; }}
.p1 {{ color: var(--p1); border-color: #d2b46d; }}
.p2 {{ color: var(--p2); }}
.ok {{ color: var(--ok); }}
table {{ width: 100%; border-collapse: collapse; background: var(--panel2); border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }}
th, td {{ padding: 8px 10px; border-bottom: 1px solid #e8e0d7; text-align: left; vertical-align: top; }}
th {{ color: var(--muted); font-size: 12px; background: var(--panel); }}
tr:last-child td {{ border-bottom: 0; }}
.barrow {{ display: grid; grid-template-columns: 210px 1fr 72px; gap: 10px; align-items: center; margin: 8px 0; }}
.bar {{ height: 12px; background: #ece4d8; border-radius: 99px; overflow: hidden; }}
.bar > i {{ display: block; height: 100%; background: var(--blue); }}
.bar.p0bar > i {{ background: var(--p0); }}
.bar.p1bar > i {{ background: var(--p1); }}
.pipe {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }}
.stage {{ border: 1px solid var(--line); border-radius: 8px; background: var(--panel2); padding: 12px; min-height: 120px; }}
.stage-title {{ font-weight: 700; margin-bottom: 8px; }}
.sources {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 10px; }}
.source {{ border: 1px solid var(--line); border-radius: 8px; background: var(--panel2); padding: 12px; }}
.source ul {{ margin: 8px 0 0; padding-left: 18px; }}
.mini {{ color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }}
pre {{ white-space: pre-wrap; overflow: auto; background: #191714; color: #f7f3ec; border-radius: 8px; padding: 14px; max-height: 520px; }}
@media (max-width: 1000px) {{ .card, .card.wide {{ grid-column: span 6; }} .pipe {{ grid-template-columns: 1fr; }} }}
@media (max-width: 640px) {{ .shell {{ padding: 14px; }} .top {{ grid-template-columns: 1fr; }} .stamp {{ text-align: left; }} .card, .card.wide {{ grid-column: 1 / -1; }} .barrow {{ grid-template-columns: 1fr; }} }}
</style>
<main class="shell">
  <div class="top">
    <div>
      <h1>ZTARE Intelligence Dashboard</h1>
      <div class="sub">Private operating view for research attention: what to act on, what is blocked, which inputs can be improved, and which tracks need interpretation.</div>
    </div>
    <div class="stamp" id="stamp"></div>
  </div>
  <div class="toolbar">
    <div class="tabs" id="tabs"></div>
    <input class="search" id="search" placeholder="Filter visible rows">
  </div>
  <div id="app"></div>
</main>
<script id="payload" type="application/json">{payload_json}</script>
<script>
const data = JSON.parse(document.getElementById("payload").textContent);
const $ = (sel) => document.querySelector(sel);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, c => ({{"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}}[c]));
const rows = (xs, fn) => (xs || []).map(fn).join("");
const pct = (n) => Number.isFinite(Number(n)) ? `${{(Number(n) * 100).toFixed(1)}}%` : "n/a";
const tabs = [
  ["brief", "Brief"],
  ["actions", "Actions"],
  ["tracks", "Tracks"],
  ["risks", "Risks"],
  ["inputs", "Inputs"],
  ["provenance", "Provenance"],
  ["raw", "Raw"]
];
let active = "brief";
$("#stamp").innerHTML = `Generated<br><b>${{esc(data.generated_at)}}</b>`;
$("#tabs").innerHTML = tabs.map(([id, label]) => `<button class="tab ${{id === active ? "active" : ""}}" data-tab="${{id}}">${{label}}</button>`).join("");
$("#tabs").addEventListener("click", e => {{
  const btn = e.target.closest("button[data-tab]");
  if (!btn) return;
  active = btn.dataset.tab;
  render();
}});
$("#search").addEventListener("input", () => filterRows());

function statusClass(v) {{
  const s = String(v || "").toLowerCase();
  if (s.includes("p0") || s.includes("block")) return "p0";
  if (s.includes("p1") || s.includes("gap") || s.includes("partial") || s.includes("warning")) return "p1";
  if (s.includes("ok") || s.includes("strong") || s.includes("active")) return "ok";
  return "p2";
}}
function card(k, v, note = "", cls = "") {{
  return `<section class="card ${{cls}}"><div class="k">${{esc(k)}}</div><div class="v">${{esc(v)}}</div><div class="note">${{esc(note)}}</div></section>`;
}}
function item(title, meta, body, pri = "") {{
  return `<div class="item filterable"><div class="item-head"><b>${{esc(title)}}</b><span class="pill ${{statusClass(pri || meta)}}">${{esc(meta)}}</span></div><div class="note">${{esc(body)}}</div></div>`;
}}
function table(headers, xs, fn) {{
  return `<table><thead><tr>${{headers.map(h => `<th>${{esc(h)}}</th>`).join("")}}</tr></thead><tbody>${{rows(xs, fn)}}</tbody></table>`;
}}
function bars(xs, label, value, cls = "") {{
  const max = Math.max(1, ...((xs || []).map(x => Number(value(x)) || 0)));
  return rows(xs, x => {{
    const n = Number(value(x)) || 0;
    return `<div class="barrow filterable"><div>${{esc(label(x))}}</div><div class="bar ${{cls}}"><i style="width:${{Math.max(2, (n / max) * 100)}}%"></i></div><div>${{esc(n)}}</div></div>`;
  }});
}}
function topSourceGaps() {{
  return (data.source_improvement_backlog || []).slice(0, 5).map(x => `${{x.priority}} ${{x.source_id}}: ${{x.gap}}`);
}}
function brief() {{
  const h = data.headline || {{}};
  const eb = data.executive_brief || {{}};
  const fa = eb.first_action || {{}};
  const sr = data.source_readiness?.summary || {{}};
  const validation = data.etl_manifest?.validate || {{}};
  const decisionRate = Number(h.forecast_decision_use_rate || 0);
  const firstAction = (data.attention || [])[0] || {{}};
  return `
    <section class="grid">
      ${{card("Operating status", eb.operating_status || "unknown", eb.status_reason || "read the source packet", "wide")}}
      ${{card("Source readiness", `${{sr.ready ?? 0}} ready / ${{sr.partial ?? 0}} partial / ${{sr.blocked ?? 0}} blocked`, "read-model source state", "wide")}}
      ${{card("Decision-use rate", pct(h.forecast_decision_use_rate), "forecast aggregates with logged action")}}
      ${{card("Blocking issues", validation.blocking_count ?? 0, "must fix before trusting recommendations")}}
      ${{card("Source gaps", data.source_map?.gap_count ?? 0, "gaps to fix upstream")}}
      ${{card("Active tracks", h.active_focus_tracks ?? 0, `${{h.strong_focus_linkage ?? 0}} strong joins`)}}
      ${{card("Experiments", h.experiment_rows ?? 0, `${{h.finding_rows ?? 0}} finding rows`, "wide")}}
      ${{card("Forecast contracts", h.forecast_contracts ?? 0, `${{h.forecast_unresolved ?? 0}} unresolved`, "wide")}}
    </section>
    <h2>Interpretation</h2>
    <div class="rowlist">
      ${{item("Market signal is not yet allocation evidence", decisionRate < 0.05 ? "p0" : "p1", "Forecasts exist, but logged decision use is too sparse. The immediate operational gain is source-side decision-use logging.", decisionRate < 0.05 ? "p0" : "p1")}}
      ${{item("Brief first action", `${{fa.priority || "p1"}} / ${{fa.kind || "attention"}}`, fa.action ? `${{fa.action}} - ${{fa.why}}` : "No brief action emitted.", fa.priority || "p1")}}
      ${{item("First action", `${{firstAction.priority || "p1"}} / ${{firstAction.kind || "attention"}}`, firstAction.title ? `${{firstAction.title}} - ${{firstAction.why}}` : "No attention row emitted.", firstAction.priority || "p1")}}
      ${{item("Activity vs yield", data.activity_yield?.verdict || "unknown", `activity ${{pct(data.activity_yield?.activity_delta_pct)}} vs yield ${{pct(data.activity_yield?.yield_delta_pct)}}`, data.activity_yield?.verdict)}}
    </div>
    <h2>Not For</h2>
    <div class="rowlist">${{rows(eb.do_not_use_for, x => item(x, "boundary", "Read the source ledgers before using this surface for that decision.", "p1"))}}</div>
    <h2>Top Source Gaps</h2>
    <div class="rowlist">${{rows(topSourceGaps(), x => item(x, "source gap", "Fix at the emitter or schema so every downstream agent sees better intelligence.", "p1"))}}</div>
  `;
}}
function actions() {{
  return `
    <h2>Attention Queue</h2>
    <div class="rowlist">${{rows(data.attention, x => item(x.title, `${{x.priority}} / ${{x.kind}}`, x.why, x.priority))}}</div>
    <h2>Source Improvement Backlog</h2>
    <div class="rowlist">${{rows(data.source_improvement_backlog, x => item(x.gap, `${{x.priority}} / ${{x.source_id}}`, x.why_source_not_report, x.priority))}}</div>
    <h2>Learning Candidates</h2>
    <div class="rowlist">${{rows(data.learning_candidates, x => item(x.review_question, `${{x.transition_kind}} / ${{x.severity}}`, x.rationale, x.severity))}}</div>
  `;
}}
function inputs() {{
  const pim = data.process_input_metrics || {{}};
  return `
    <section class="grid">
      ${{card("Input metric rows", (pim.rows || []).length, "controllable inputs and processes")}}
      ${{card("Status counts", JSON.stringify(pim.status_counts || {{}}), "current instrumentation")}}
      ${{card("Activity/yield", data.activity_yield?.verdict || "n/a", `activity ${{pct(data.activity_yield?.activity_delta_pct)}} vs yield ${{pct(data.activity_yield?.yield_delta_pct)}}`, "wide")}}
    </section>
    <h2>Process/Input Metrics</h2>
    ${{table(["Metric", "Kind", "Status", "Current", "Denominator", "Downstream output"], pim.rows, x =>
      `<tr class="filterable"><td><b>${{esc(x.metric_id)}}</b><div class="mini">${{esc(x.definition)}}</div></td><td>${{esc(x.metric_kind)}}</td><td><span class="pill ${{statusClass(x.status)}}">${{esc(x.status)}}</span></td><td>${{esc(x.current)}}</td><td>${{esc(x.denominator)}}</td><td>${{esc(x.downstream_output)}}</td></tr>`)}}
    <h2>Metric Areas</h2>
    ${{table(["Area", "Status", "Implemented", "Source gap"], data.research_ops_metric_areas?.areas, x =>
      `<tr class="filterable"><td><b>${{esc(x.area_id)}}</b><div class="mini">${{esc(x.purpose)}}</div></td><td><span class="pill ${{statusClass(x.status)}}">${{esc(x.status)}}</span></td><td>${{esc((x.implemented_metrics || []).join(", "))}}</td><td>${{esc(x.source_gap)}}</td></tr>`)}}
  `;
}}
function etl() {{
  const e = data.etl_manifest || {{}};
  const v = e.validate || {{}};
  return `
    <div class="pipe">
      <div class="stage"><div class="stage-title">Extract</div><div class="mini">${{esc((e.extract?.sources || []).join(", "))}}</div></div>
      <div class="stage"><div class="stage-title">Transform</div><div class="mini">${{esc((e.transform?.aggregates || []).join(", "))}}</div></div>
      <div class="stage"><div class="stage-title">Validate</div><div><b>${{esc(v.issue_count ?? 0)}}</b> issues</div><div class="mini">${{esc(v.blocking_count ?? 0)}} blocking</div></div>
      <div class="stage"><div class="stage-title">Load</div><div class="mini">${{esc((e.load?.default_outputs || []).join(", "))}}</div></div>
    </div>
    <h2>Validation Issues</h2>
    <div class="rowlist">${{rows(v.issues, x => item(x.issue, `${{x.severity}} / ${{x.source_id}}`, x.stage, x.severity))}}</div>
  `;
}}
function provenance() {{
  return `
    <h2>Pipeline Provenance</h2>
    ${{etl()}}
    <h2>Source Readiness</h2>
    ${{table(["Source", "Readiness", "Use now", "Gaps", "Blocking", "Next fix"], data.source_readiness?.rows, x =>
      `<tr class="filterable"><td><b>${{esc(x.source_id)}}</b></td><td><span class="pill ${{statusClass(x.readiness)}}">${{esc(x.readiness)}}</span></td><td>${{esc(x.use_now)}}</td><td>${{esc(x.gap_count)}}</td><td>${{esc(x.blocking_validation_issues)}}</td><td class="mini">${{esc(x.next_source_fix || "")}}</td></tr>`)}}
    <h2>Source Map</h2>
    <div class="sources">${{rows(data.source_map?.rows, s => `
      <div class="source filterable"><h3>${{esc(s.source_id)}}</h3>
        <div class="mini">Feeds: ${{esc((s.feeds || []).join(", "))}}</div>
        <div class="mini">Fields: ${{esc((s.aggregate_fields || []).join(", "))}}</div>
        <ul>${{rows(s.source_gaps, g => `<li>${{esc(g)}}</li>`)}}</ul>
      </div>`)}}
    </div>
    <h2>Dashboard Feeds</h2>
    ${{table(["Feed", "Present", "Records", "Latest", "Source"], data.dashboard_sources?.rows, x =>
      `<tr class="filterable"><td><b>${{esc(x.name)}}</b></td><td>${{esc(x.present)}}</td><td>${{esc(x.record_count)}}</td><td>${{esc(x.latest_touch)}}</td><td class="mini">${{esc(x.source)}}</td></tr>`)}}
  `;
}}
function tracks() {{
  return `
    <h2>Focus Tracks</h2>
    ${{table(["Track", "State", "Linkage", "Forecast", "GP-233", "Experiments", "Latest"], data.focus_tracks?.rows, x => {{
      const s = x.signals || {{}};
      return `<tr class="filterable"><td><b>${{esc(x.track_id)}}</b><div class="mini">${{esc(x.label)}}</div></td><td>${{esc(x.activity_state)}}</td><td><span class="pill ${{statusClass(x.linkage_quality)}}">${{esc(x.linkage_quality)}}</span></td><td>${{esc(s.forecast_refs)}}</td><td>${{esc(s.gp233_refs)}}</td><td>${{esc(s.experiment_refs)}}</td><td class="mini">${{esc(x.latest_touch_source)}}</td></tr>`;
    }})}}
  `;
}}
function risks() {{
  const xs = data.recurrence_suppression_candidates?.rows || [];
  return `
    <section class="grid">
      ${{card("Catch rows", data.catch_and_risk?.rows ?? 0, `${{data.catch_and_risk?.ratified ?? 0}} ratified`)}}
      ${{card("Consequential", data.catch_and_risk?.consequential ?? 0, "catch/action candidates")}}
      ${{card("Suppression candidates", xs.length, "needs avoidance labels")}}
      ${{card("Recent narrative inflation", xs.find(x => x.category === "narrative_inflation")?.recent_count_last40 ?? 0, "last 40 catch rows")}}
    </section>
    <h2>Recurrence Candidates</h2>
    ${{bars(xs, x => `${{x.priority}} / ${{x.category}}`, x => x.total_count, "p0bar")}}
    <h2>Recent Catch Categories</h2>
    ${{bars(data.catch_and_risk?.recent_categories || [], x => x.name, x => x.count, "p1bar")}}
    <h2>Metric Caveats</h2>
    <div class="rowlist">${{rows(data.metric_caveats, x => item(x.metric, "caveat", x.failure_mode, "p1"))}}</div>
  `;
}}
function raw() {{
  return `<h2>Raw Packet</h2><pre>${{esc(JSON.stringify(data, null, 2))}}</pre>`;
}}
function render() {{
  document.querySelectorAll(".tab").forEach(b => b.classList.toggle("active", b.dataset.tab === active));
  const views = {{brief, actions, tracks, risks, inputs, provenance, raw}};
  $("#app").innerHTML = `<section class="section active">${{views[active]()}}</section>`;
  filterRows();
}}
function filterRows() {{
  const q = $("#search").value.trim().toLowerCase();
  document.querySelectorAll(".filterable").forEach(el => {{
    el.style.display = !q || el.textContent.toLowerCase().includes(q) ? "" : "none";
  }});
}}
render();
</script>
</html>
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(doc, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the private ZTARE intelligence surface.")
    parser.add_argument("--repo", default=str(REPO))
    parser.add_argument("--out", default=str(DEFAULT_JSON_OUT))
    parser.add_argument("--markdown", default=str(DEFAULT_MD_OUT))
    parser.add_argument("--html", default=None, help="Optional private HTML output path.")
    parser.add_argument("--freshness-days", type=int, default=14)
    parser.add_argument("--max-projects", type=int, default=30)
    parser.add_argument("--no-markdown", action="store_true")
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    payload = build(repo, freshness_days=args.freshness_days, max_projects=args.max_projects)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.no_markdown:
        write_markdown(payload, Path(args.markdown))
    if args.html:
        write_html(payload, Path(args.html))
    print(f"wrote ZTARE intelligence surface -> {rel(repo, out)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
