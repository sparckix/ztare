#!/usr/bin/env python3
"""Acquire concrete Manifold candidates for the Law 3 cutoff-validity slate.

This is a read-only corpus acquisition tool. It does not write the master DB.
It turns the abstract 27-row acquisition manifest into candidate contract rows
that can later be reviewed and ingested.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from cutoff_candidate_report import question_length_bucket, topic_bucket
from src.ztare.research_director.source_currency_discriminator import (
    classify_forecast_source_currency,
)


REPO = Path(__file__).resolve().parents[3]
PROGRAM_ROOT = REPO / "projects/llm_forecasting_calibration_program"
DEFAULT_DB = REPO / "analytics/public/calibration/forecaster_calibration.db"
DEFAULT_MANIFEST = PROGRAM_ROOT / "cutoff_validity_v1/workspace/cutoff_pre_cutoff_acquisition_manifest.jsonl"
DEFAULT_OUT = PROGRAM_ROOT / "cutoff_validity_v1/workspace"
API = "https://api.manifold.markets/v0/search-markets"
DEFAULT_TERMS = ("", "will", "2024", "2025", "election", "sports")
GENERAL_POLITICAL_CUES = (
    "russia",
    "ukraine",
    "china",
    "taiwan",
    "macron",
    "elected",
    "re-elected",
    "military",
    "conflict",
    "approval rating",
    "covid zero",
)
GENERAL_FINANCE_CUES = (
    "usd",
    "price",
    "stock",
    "token",
    "tokens",
    "nft",
    "revenue",
    "bit coin",
    "bitcoin",
)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        data = json.loads(line)
        if isinstance(data, dict):
            rows.append(data)
    return rows


def ms_to_date(ms: Any) -> str | None:
    if ms is None:
        return None
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=UTC).date().isoformat()
    except Exception:
        return None


def normalize_question(question: str | None) -> str:
    text = " ".join((question or "").lower().strip().split())
    keep = []
    for ch in text:
        if ch.isalnum() or ch.isspace():
            keep.append(ch)
    return " ".join("".join(keep).split())


def has_word_or_phrase(text: str, cue: str) -> bool:
    cue_l = cue.lower()
    if cue_l.isalnum():
        import re

        return re.search(rf"(?<![a-z0-9]){re.escape(cue_l)}(?![a-z0-9])", text) is not None
    return cue_l in text


def has_any(text: str, cues: tuple[str, ...]) -> bool:
    return any(has_word_or_phrase(text, cue) for cue in cues)


def event_core_id(question: str | None) -> str:
    norm = normalize_question(question)
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def existing_db_surface(db: Path) -> dict[str, set[str]]:
    con = sqlite3.connect(db)
    rows = list(con.execute("SELECT contract_id, question FROM contracts"))
    con.close()
    return {
        "contract_ids": {str(row[0]) for row in rows if row[0]},
        "event_cores": {event_core_id(str(row[1] or "")) for row in rows if row[1]},
    }


def request_markets(term: str, limit: int, offset: int, timeout: float) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    params = {
        "term": term,
        "sort": "resolve-date",
        "filter": "resolved",
        "contractType": "BINARY",
        "limit": str(limit),
        "offset": str(offset),
    }
    url = f"{API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "ztare-law3-cutoff-acquisition/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        body = response.read().decode("utf-8", errors="replace")
    try:
        data = json.loads(body)
    except Exception:
        return [], {"url": url, "ok": False, "error": "non_json_response", "body_sample": body[:240]}
    if not isinstance(data, list):
        return [], {"url": url, "ok": False, "error": "unexpected_json_shape", "body_sample": body[:240]}
    return [row for row in data if isinstance(row, dict)], {"url": url, "ok": True, "rows": len(data)}


def iter_json_array(stream: io.TextIOBase):
    decoder = json.JSONDecoder()
    buf = ""
    started = False
    eof = False
    while not eof:
        chunk = stream.read(65536)
        if chunk:
            buf += chunk
        else:
            eof = True
        while True:
            buf = buf.lstrip()
            if not started:
                if not buf:
                    break
                if buf[0] != "[":
                    raise ValueError("expected JSON array")
                buf = buf[1:]
                started = True
                continue
            if not buf:
                break
            if buf[0] == "]":
                return
            if buf[0] == ",":
                buf = buf[1:]
                continue
            try:
                obj, idx = decoder.raw_decode(buf)
            except json.JSONDecodeError:
                if eof:
                    raise
                break
            yield obj
            buf = buf[idx:]


def iter_market_rows_from_path(path: Path):
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as zf:
            names = [name for name in zf.namelist() if not name.endswith("/")]
            if not names:
                return
            with zf.open(names[0]) as raw:
                text = io.TextIOWrapper(raw, encoding="utf-8")
                yield from iter_json_array(text)
        return

    if path.suffix == ".jsonl":
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                yield json.loads(line)
        return

    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and isinstance(data.get("markets"), list):
        data = data["markets"]
    if not isinstance(data, list):
        raise ValueError("expected list or object with markets list")
    yield from data


def candidate_from_market(market: dict[str, Any], panel_cutoff_date: str) -> tuple[dict[str, Any] | None, str]:
    if market.get("outcomeType") != "BINARY":
        return None, "not_binary"
    if not market.get("isResolved"):
        return None, "not_resolved"
    resolution = str(market.get("resolution") or "").upper()
    if resolution not in {"YES", "NO"}:
        return None, "non_binary_resolution"
    resolve_date = ms_to_date(market.get("resolutionTime"))
    if not resolve_date:
        return None, "missing_resolution_time"
    relation = classify_forecast_source_currency(
        resolve_date=resolve_date,
        model_cutoff_date=panel_cutoff_date,
        stored_post_training_cutoff=None,
        prefer_computed_cutoff=True,
    )
    if relation.get("cutoff_relation") != "pre_cutoff":
        return None, "not_pre_cutoff"
    question = str(market.get("question") or "")
    raw_for_bucket = {
        "task_type": "manifold_binary",
        "groupSlugs": market.get("groupSlugs") or [],
    }
    row_for_bucket = {
        "question": question,
        "source": "manifold",
        "task_type": "manifold_binary",
    }
    y_known = 1 if resolution == "YES" else 0
    source_corpus = f"law3_cutoff_acquisition_manifold_{date.today().isoformat()}"
    candidate = {
        "contract_id": f"manifold_{market.get('id')}",
        "question": question,
        "source": "manifold",
        "source_corpus": source_corpus,
        "task_type": "manifold_binary",
        "y_known": y_known,
        "strict_resolve_date": resolve_date,
        "computed_cutoff_relation": relation.get("cutoff_relation"),
        "panel_cutoff_date": panel_cutoff_date,
        "topic": topic_bucket(row_for_bucket, raw_for_bucket),
        "question_length_bucket": question_length_bucket(question),
        "event_core_id": event_core_id(question),
        "raw_manifold": {
            "id": market.get("id"),
            "url": market.get("url"),
            "createdTime": market.get("createdTime"),
            "closeTime": market.get("closeTime"),
            "resolutionTime": market.get("resolutionTime"),
            "resolution": market.get("resolution"),
            "probability": market.get("probability"),
            "uniqueBettorCount": market.get("uniqueBettorCount"),
            "volume": market.get("volume"),
            "groupSlugs": market.get("groupSlugs") or [],
        },
    }
    return candidate, "candidate"


def quality_reject_reason(
    candidate: dict[str, Any],
    *,
    min_unique_bettors: int,
    min_volume: float,
    exclude_test_markets: bool,
    exclude_platform_self_reference: bool,
    exclude_general_topic_cues: bool,
) -> str | None:
    question = str(candidate.get("question") or "").lower()
    if exclude_test_markets and "test" in question:
        return "test_market"
    if exclude_platform_self_reference and (
        "mantic" in question
        or "manifold" in question
        or "polymarket" in question
    ):
        return "platform_self_reference"
    if "start right after january" in question:
        return "trivial_calendar"
    if exclude_general_topic_cues and candidate.get("topic") == "general":
        if has_any(question, GENERAL_POLITICAL_CUES):
            return "general_political_cue"
        if has_any(question, GENERAL_FINANCE_CUES):
            return "general_finance_cue"
    raw = candidate.get("raw_manifold") or {}
    unique = raw.get("uniqueBettorCount")
    volume = raw.get("volume")
    try:
        if unique is not None and int(unique) < min_unique_bettors:
            return "low_unique_bettors"
    except Exception:
        return "invalid_unique_bettors"
    try:
        if volume is not None and float(volume) < min_volume:
            return "low_volume"
    except Exception:
        return "invalid_volume"
    return None


def assign_to_manifest(
    candidates: list[dict[str, Any]],
    manifest_rows: list[dict[str, Any]],
    existing: dict[str, set[str]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    needs = Counter(
        (
            row["target_source"],
            row["target_topic"],
            row["target_question_length_bucket"],
        )
        for row in manifest_rows
    )
    slot_ids: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for row in manifest_rows:
        key = (row["target_source"], row["target_topic"], row["target_question_length_bucket"])
        slot_ids[key].append(row["acquisition_id"])

    selected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_cores = set(existing["event_cores"])
    reject_counts: Counter[str] = Counter()
    for row in candidates:
        key = (row["source"], row["topic"], row["question_length_bucket"])
        if needs[key] <= 0:
            reject_counts["unneeded_stratum"] += 1
            continue
        if row["contract_id"] in existing["contract_ids"] or row["contract_id"] in seen_ids:
            reject_counts["duplicate_contract_id"] += 1
            continue
        if row["event_core_id"] in seen_cores:
            reject_counts["duplicate_event_core"] += 1
            continue
        seen_ids.add(row["contract_id"])
        seen_cores.add(row["event_core_id"])
        slot = slot_ids[key].pop(0)
        needs[key] -= 1
        selected.append({**row, "acquisition_id": slot, "target_key": "/".join(key)})
    return selected, {
        "selected": len(selected),
        "remaining_needs": {"/".join(key): n for key, n in sorted(needs.items()) if n > 0},
        "reject_counts_after_candidate_filter": dict(reject_counts),
    }


def manifest_state(manifest_rows: list[dict[str, Any]]) -> dict[str, Any]:
    needs = Counter(
        (
            row["target_source"],
            row["target_topic"],
            row["target_question_length_bucket"],
        )
        for row in manifest_rows
    )
    slot_ids: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for row in manifest_rows:
        key = (row["target_source"], row["target_topic"], row["target_question_length_bucket"])
        slot_ids[key].append(row["acquisition_id"])
    return {"needs": needs, "slot_ids": slot_ids}


def try_select_candidate(
    row: dict[str, Any],
    *,
    state: dict[str, Any],
    existing: dict[str, set[str]],
    selected: list[dict[str, Any]],
    seen_ids: set[str],
    seen_cores: set[str],
    reject_counts: Counter[str],
) -> None:
    key = (row["source"], row["topic"], row["question_length_bucket"])
    needs: Counter = state["needs"]
    slot_ids: dict[tuple[str, str, str], list[str]] = state["slot_ids"]
    if needs[key] <= 0:
        reject_counts["unneeded_stratum"] += 1
        return
    if row["contract_id"] in existing["contract_ids"] or row["contract_id"] in seen_ids:
        reject_counts["duplicate_contract_id"] += 1
        return
    if row["event_core_id"] in existing["event_cores"] or row["event_core_id"] in seen_cores:
        reject_counts["duplicate_event_core"] += 1
        return
    seen_ids.add(row["contract_id"])
    seen_cores.add(row["event_core_id"])
    slot = slot_ids[key].pop(0)
    needs[key] -= 1
    selected.append({**row, "acquisition_id": slot, "target_key": "/".join(key)})


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    manifest_rows = read_jsonl(args.manifest)
    panel_cutoff_date = str(manifest_rows[0].get("panel_cutoff_date") if manifest_rows else args.panel_cutoff_date)
    existing = existing_db_surface(args.db)
    state = manifest_state(manifest_rows)
    selected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_cores: set[str] = set()
    reject_counts: Counter[str] = Counter()
    assignment_rejects: Counter[str] = Counter()
    raw_markets_seen = 0
    candidate_rows = 0
    raw_statuses: list[dict[str, Any]] = []

    for path in args.raw_json:
        path_seen = 0
        path_candidates = 0
        try:
            for market in iter_market_rows_from_path(path):
                if not isinstance(market, dict):
                    continue
                raw_markets_seen += 1
                path_seen += 1
                candidate, reason = candidate_from_market(market, panel_cutoff_date)
                if candidate:
                    quality_reason = quality_reject_reason(
                        candidate,
                        min_unique_bettors=args.min_unique_bettors,
                        min_volume=args.min_volume,
                        exclude_test_markets=not args.include_test_markets,
                        exclude_platform_self_reference=not args.include_platform_self_reference,
                        exclude_general_topic_cues=not args.include_general_topic_cues,
                    )
                    if quality_reason:
                        reject_counts[quality_reason] += 1
                        continue
                    candidate_rows += 1
                    path_candidates += 1
                    try_select_candidate(
                        candidate,
                        state=state,
                        existing=existing,
                        selected=selected,
                        seen_ids=seen_ids,
                        seen_cores=seen_cores,
                        reject_counts=assignment_rejects,
                    )
                else:
                    reject_counts[reason] += 1
        except Exception as exc:
            raw_statuses.append({"path": str(path), "ok": False, "error": repr(exc), "rows_seen": path_seen})
            continue
        raw_statuses.append(
            {
                "path": str(path),
                "ok": True,
                "rows": path_seen,
                "candidate_rows": path_candidates,
            }
        )

    fetch_statuses: list[dict[str, Any]] = []
    terms = args.term or list(DEFAULT_TERMS)
    if not args.no_fetch:
        for term in terms:
            for page in range(args.max_pages):
                offset = page * args.limit
                try:
                    batch, status = request_markets(term, args.limit, offset, args.timeout)
                except Exception as exc:
                    fetch_statuses.append(
                        {"term": term, "offset": offset, "ok": False, "error": repr(exc)}
                    )
                    break
                status.update({"term": term, "offset": offset})
                fetch_statuses.append(status)
                for market in batch:
                    raw_markets_seen += 1
                    market_id = market.get("id")
                    if market_id and str(market_id) in seen_ids:
                        continue
                    candidate, reason = candidate_from_market(market, panel_cutoff_date)
                    if candidate:
                        quality_reason = quality_reject_reason(
                            candidate,
                            min_unique_bettors=args.min_unique_bettors,
                            min_volume=args.min_volume,
                            exclude_test_markets=not args.include_test_markets,
                            exclude_platform_self_reference=not args.include_platform_self_reference,
                            exclude_general_topic_cues=not args.include_general_topic_cues,
                        )
                        if quality_reason:
                            reject_counts[quality_reason] += 1
                            continue
                        candidate_rows += 1
                        try_select_candidate(
                            candidate,
                            state=state,
                            existing=existing,
                            selected=selected,
                            seen_ids=seen_ids,
                            seen_cores=seen_cores,
                            reject_counts=assignment_rejects,
                        )
                    else:
                        reject_counts[reason] += 1
                if len(batch) < args.limit:
                    break
                time.sleep(args.throttle)

    remaining = {"/".join(key): n for key, n in sorted(state["needs"].items()) if n > 0}
    return {
        "schema": "gp245-cutoff-manifold-acquisition-v1",
        "db": str(args.db),
        "manifest": str(args.manifest),
        "panel_cutoff_date": panel_cutoff_date,
        "api_source": API,
        "api_docs": "https://docs.manifold.markets/api",
        "manifest_rows": len(manifest_rows),
        "raw_markets_seen": raw_markets_seen,
        "candidate_rows": candidate_rows,
        "selected_rows": len(selected),
        "ready_for_contract_review": len(selected) > 0,
        "ready_for_minimum_ingest": len(selected) >= len(manifest_rows) and len(manifest_rows) > 0,
        "raw_file_statuses": raw_statuses,
        "fetch_statuses": fetch_statuses,
        "quality_filters": {
            "min_unique_bettors": args.min_unique_bettors,
            "min_volume": args.min_volume,
            "exclude_test_markets": not args.include_test_markets,
            "exclude_platform_self_reference": not args.include_platform_self_reference,
            "exclude_general_topic_cues": not args.include_general_topic_cues,
        },
        "candidate_reject_counts": dict(reject_counts),
        "assignment": {
            "selected": len(selected),
            "remaining_needs": remaining,
            "reject_counts_after_candidate_filter": dict(assignment_rejects),
        },
        "selected_candidates": selected,
        "interpretation": (
            "This report acquires candidate Manifold rows only. Review rows, "
            "then ingest accepted contracts and fire model calls before claiming "
            "Law 3 Stage B evidence."
        ),
    }


def run_selftest() -> dict[str, Any]:
    panel_cutoff_date = "2025-10-01"
    manifest = [
        {
            "acquisition_id": "selftest_general_short_001",
            "target_source": "manifold",
            "target_topic": "general",
            "target_question_length_bucket": "short",
        },
        {
            "acquisition_id": "selftest_general_medium_001",
            "target_source": "manifold",
            "target_topic": "general",
            "target_question_length_bucket": "medium",
        },
        {
            "acquisition_id": "selftest_sports_medium_001",
            "target_source": "manifold",
            "target_topic": "sports",
            "target_question_length_bucket": "medium",
        },
    ]
    markets = [
        {
            "id": "short_yes",
            "question": "Will it rain tomorrow?",
            "outcomeType": "BINARY",
            "isResolved": True,
            "resolution": "YES",
            "resolutionTime": 1_704_067_200_000,
        },
        {
            "id": "medium_no",
            "question": "Will the test acquisition script select this deliberately medium length resolved question?",
            "outcomeType": "BINARY",
            "isResolved": True,
            "resolution": "NO",
            "resolutionTime": 1_704_067_200_000,
        },
        {
            "id": "sports_no",
            "question": "Will the home team beat the away team in the series?",
            "outcomeType": "BINARY",
            "isResolved": True,
            "resolution": "NO",
            "resolutionTime": 1_704_067_200_000,
        },
        {
            "id": "future",
            "question": "Will this future market be rejected?",
            "outcomeType": "BINARY",
            "isResolved": True,
            "resolution": "YES",
            "resolutionTime": 1_767_225_600_000,
        },
        {
            "id": "multi",
            "question": "Which option wins?",
            "outcomeType": "MULTIPLE_CHOICE",
            "isResolved": True,
            "resolution": "A",
            "resolutionTime": 1_704_067_200_000,
        },
    ]
    candidates: list[dict[str, Any]] = []
    rejects: Counter[str] = Counter()
    for market in markets:
        candidate, reason = candidate_from_market(market, panel_cutoff_date)
        if candidate:
            candidates.append(candidate)
        else:
            rejects[reason] += 1
    selected, assignment = assign_to_manifest(
        candidates,
        manifest,
        {"contract_ids": set(), "event_cores": set()},
    )
    ok = (
        len(candidates) == 3
        and len(selected) == 3
        and not assignment["remaining_needs"]
        and rejects["not_pre_cutoff"] == 1
        and rejects["not_binary"] == 1
    )
    return {
        "schema": "gp245-cutoff-manifold-acquisition-selftest-v1",
        "ok": ok,
        "candidate_rows": len(candidates),
        "selected_rows": len(selected),
        "reject_counts": dict(rejects),
        "assignment": assignment,
    }


def write_outputs(report: dict[str, Any], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cutoff_manifold_acquisition_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (out_dir / "cutoff_manifold_acquisition_candidates.jsonl").open("w", encoding="utf-8") as f:
        for row in report["selected_candidates"]:
            f.write(json.dumps(row, sort_keys=True) + "\n")
    lines = [
        "# Cutoff Manifold Acquisition Report",
        "",
        f"- Schema: `{report['schema']}`",
        f"- Manifest rows: {report['manifest_rows']}",
        f"- Raw markets seen: {report['raw_markets_seen']}",
        f"- Candidate rows: {report['candidate_rows']}",
        f"- Selected rows: {report['selected_rows']}",
        f"- Ready for minimum ingest: `{report['ready_for_minimum_ingest']}`",
        "",
        "## Remaining Needs",
        "",
    ]
    remaining = report["assignment"].get("remaining_needs") or {}
    if not remaining:
        lines.append("- None.")
    for key, n in remaining.items():
        lines.append(f"- `{key}`: {n}")
    lines.extend(["", "## Fetch Status", ""])
    for status in report["fetch_statuses"][:20]:
        lines.append(f"- `{status.get('term')}` offset={status.get('offset')}: ok={status.get('ok')} {status.get('error', '')}")
    lines.extend(["", "## Interpretation", "", report["interpretation"], ""])
    (out_dir / "cutoff_manifold_acquisition_report.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--panel-cutoff-date", default="2025-10-01")
    parser.add_argument("--term", action="append", default=None)
    parser.add_argument("--raw-json", action="append", type=Path, default=[])
    parser.add_argument("--no-fetch", action="store_true")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=2)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--throttle", type=float, default=0.25)
    parser.add_argument("--min-unique-bettors", type=int, default=3)
    parser.add_argument("--min-volume", type=float, default=100.0)
    parser.add_argument("--include-test-markets", action="store_true")
    parser.add_argument("--include-platform-self-reference", action="store_true")
    parser.add_argument("--include-general-topic-cues", action="store_true")
    args = parser.parse_args()
    if args.selftest:
        result = run_selftest()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok"] else 1
    report = build_report(args)
    print(json.dumps(report, indent=2, sort_keys=True))
    write_outputs(report, args.out_dir)
    if not args.no_fetch and any(not status.get("ok") for status in report["fetch_statuses"]):
        print("cutoff-manifold-acquire: one or more API fetches failed; see report", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
