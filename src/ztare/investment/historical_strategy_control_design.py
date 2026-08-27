"""Compile control acquisition from source-bound historical strategy episodes."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from itertools import combinations
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping
import zipfile

import yaml

from ztare.common.equivariance import stable_sha256
from ztare.strategy import (
    CandidateEvaluation, FrontierScope, Neighborhood, OperatorGrammar,
    RepresentationAudit, TypedOperator, TypedTerminal, build_typed_program,
    compile_enumeration_result, compile_jaggedthoughts_frontier,
)

from .company_quality import compile_company_quality_histories
from .contracts import canonical_timestamp, timestamp_key
from .historical_strategy_event_replay import HISTORICAL_STRATEGY_EVENT_REPLAY_SCHEMA
from .historical_strategy_bulk_outcomes import _SELECTIONS
from .sources import parse_sec_companyfacts


HISTORICAL_STRATEGY_CONTROL_DESIGN_SCHEMA = (
    "jaggedthoughts-historical-strategy-control-design-v1"
)
HISTORICAL_STRATEGY_CONTROL_ACQUISITION_SCHEMA = (
    "jaggedthoughts-historical-strategy-control-acquisition-v1"
)
HISTORICAL_STRATEGY_MODERATOR_DIMENSIONS = (
    "implementation_mode", "transaction_form", "operating_object_scope", "issuer_role",
)
_MIN_TREATED_UNITS = 4
_MIN_EVENT_YEARS = 2
_DEFAULT_MAX_REQUESTS = 32


def _checked_hash(payload: Mapping[str, Any], field: str, label: str) -> str:
    body = dict(payload)
    declared = str(body.pop(field, ""))
    if declared != stable_sha256(body):
        raise ValueError(f"{label} content hash mismatch")
    return declared


def _phenotype_value(episode: Mapping[str, Any], field: str) -> str:
    if field == "implementation_mode":
        return str(episode.get(field) or "indeterminate")
    return str((episode.get("transaction_phenotype") or {}).get(field) or "indeterminate")


def enumerate_historical_strategy_moderator_programs(
    dimensions: tuple[str, ...] = HISTORICAL_STRATEGY_MODERATOR_DIMENSIONS,
) -> tuple[OperatorGrammar, list[Any], dict[str, tuple[str, ...]]]:
    """Enumerate every bounded moderator projection in the shared strategy grammar."""
    if not dimensions or len(dimensions) != len(set(dimensions)):
        raise ValueError("historical strategy moderator dimensions must be unique")
    grammar = OperatorGrammar(
        grammar_id="jaggedthoughts-historical-strategy-moderator-projection",
        version="1",
        terminals=(TypedTerminal("all_typed_events", "historical_strategy_projection"),),
        operators=tuple(
            TypedOperator(
                f"condition_on_{field}", ("historical_strategy_projection",),
                "historical_strategy_projection",
            )
            for field in dimensions
        ),
    )
    base = build_typed_program(grammar, terminal_id="all_typed_events")
    programs, fields_by_program = [], {}
    for depth in range(len(dimensions) + 1):
        for fields in combinations(dimensions, depth):
            program = base
            for field in fields:
                program = build_typed_program(
                    grammar, operator_id=f"condition_on_{field}", children=(program,),
                )
            programs.append(program)
            fields_by_program[program.program_id] = fields
    return grammar, programs, fields_by_program


def _projection_cells(
    episodes: Iterable[Mapping[str, Any]], fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, ...], list[Mapping[str, Any]]] = defaultdict(list)
    for episode in episodes:
        groups[tuple(_phenotype_value(episode, field) for field in fields)].append(episode)
    cells = []
    for values, members in sorted(groups.items()):
        phenotype = dict(zip(fields, values))
        entities = sorted({str(row["entity_id"]) for row in members})
        years = sorted({int(str(row["occurred_at"])[:4]) for row in members})
        body = {
            "moderators": phenotype,
            "episode_sha256s": sorted(str(row["episode_sha256"]) for row in members),
            "entity_ids": entities, "event_years": years,
            "episode_count": len(members), "entity_count": len(entities),
            "event_year_count": len(years),
            "treated_support_ready": (
                len(entities) >= _MIN_TREATED_UNITS and len(years) >= _MIN_EVENT_YEARS
            ),
        }
        cells.append({**body, "cell_sha256": stable_sha256(body)})
    return cells


def _moderator_frontier(replay: Mapping[str, Any]) -> dict[str, Any]:
    grammar, programs, fields_by_program = enumerate_historical_strategy_moderator_programs()
    episodes = tuple(replay.get("episodes") or ())
    enumeration = compile_enumeration_result(
        grammar, programs=programs,
        max_depth=len(HISTORICAL_STRATEGY_MODERATOR_DIMENSIONS),
        max_programs=2 ** len(HISTORICAL_STRATEGY_MODERATOR_DIMENSIONS),
    )
    rows, evaluations = [], []
    total = max(1, len(episodes))
    for program in programs:
        fields = fields_by_program[program.program_id]
        cells = _projection_cells(episodes, fields)
        supported = {
            episode_sha
            for cell in cells if cell["treated_support_ready"]
            for episode_sha in cell["episode_sha256s"]
        }
        replicated = {
            episode_sha
            for cell in cells if cell["entity_count"] >= 2
            for episode_sha in cell["episode_sha256s"]
        }
        timed = {
            episode_sha
            for cell in cells if cell["event_year_count"] >= _MIN_EVENT_YEARS
            for episode_sha in cell["episode_sha256s"]
        }
        objectives = (
            len(supported) / total,
            len(fields) / len(HISTORICAL_STRATEGY_MODERATOR_DIMENSIONS),
            len(replicated) / total,
            len(timed) / total,
        )
        evaluations.append(CandidateEvaluation(
            program_id=program.program_id,
            objective_values=objectives,
            behavior_signature=tuple(
                f"{cell['cell_sha256']}:{','.join(cell['episode_sha256s'])}" for cell in cells
            ),
            evidence_refs=(str(replay["replay_sha256"]),),
        ))
        rows.append({
            "program_id": program.program_id,
            "moderator_fields": list(fields), "specificity": objectives[1],
            "treated_support_coverage": objectives[0],
            "replicated_episode_coverage": objectives[2],
            "multi_timing_episode_coverage": objectives[3],
            "cell_count": len(cells), "cells": cells,
        })
    edges = []
    for left in programs:
        left_fields = set(fields_by_program[left.program_id])
        for right in programs:
            right_fields = set(fields_by_program[right.program_id])
            if left_fields < right_fields and len(right_fields) == len(left_fields) + 1:
                edges.append((left.program_id, right.program_id))
    neighborhood = Neighborhood("one-historical-moderator-edit", tuple(edges))
    scope = FrontierScope(
        grammar_id=grammar.grammar_id, grammar_version=grammar.version,
        grammar_digest=grammar.grammar_digest,
        target_type="historical_strategy_projection",
        max_depth=len(HISTORICAL_STRATEGY_MODERATOR_DIMENSIONS),
        max_programs=2 ** len(HISTORICAL_STRATEGY_MODERATOR_DIMENSIONS),
        evaluation_model_id="source-support-before-outcome-v1", landscape_mode="fixed",
        evidence_epoch=str(replay["evidence_as_of"]),
        objective_names=(
            "treated_support_coverage", "specificity",
            "replicated_episode_coverage", "multi_timing_episode_coverage",
        ),
        neighborhood_id=neighborhood.neighborhood_id,
    )
    certificate = compile_jaggedthoughts_frontier(
        scope=scope, enumeration=enumeration, evaluations=evaluations,
        neighborhood=neighborhood,
        representation_audit=RepresentationAudit(
            "historical-strategy-causal-representation", status="residual",
            residuals=(
                "bounded_control_histories_missing",
                "event_time_environment_missing",
                "pretrend_fit_unmeasured",
                "outcome_stability_unmeasured",
            ),
        ),
    )
    frontier_ids = set(certificate.frontier_program_ids)
    body = {
        "grammar": grammar.to_dict(), "enumeration": enumeration.to_dict(),
        "projection_count": len(rows),
        "projections": [
            {**row, "frontier_status": (
                "frontier" if row["program_id"] in frontier_ids else "dominated"
            )}
            for row in rows
        ],
        "certificate": certificate.to_dict(),
        "selection_status": "structural_frontier_only",
    }
    return {**body, "moderator_frontier_sha256": stable_sha256(body)}


def _history_status(root: Path, replay: Mapping[str, Any]) -> list[dict[str, Any]]:
    histories = compile_company_quality_histories(
        entity_ids={str(row["entity_id"]) for row in replay.get("episodes") or ()},
        observations_path=root / "data" / "observations.csv",
        as_of=str(replay["evidence_as_of"]), min_years=3,
    )
    rows = []
    for episode in replay.get("episodes") or ():
        reports = histories.get(str(episode["entity_id"]).upper(), ())
        periods = sorted({int(str(row["history"][-1]["observed_at"])[:4]) for row in reports})
        event_at = timestamp_key(str(episode["occurred_at"]))
        fiscal_heads = [timestamp_key(str(row["history"][-1]["observed_at"])) for row in reports]
        same_year = [value for value in fiscal_heads if value.year == event_at.year]
        if same_year:
            partial = event_at.year + (max(same_year) < event_at)
        elif fiscal_heads:
            month_day = max(value.strftime("%m-%d") for value in fiscal_heads)
            partial = event_at.year + (event_at.strftime("%m-%d") > month_day)
        else:
            partial = event_at.year
        treatment = partial + 1
        pre = sum(period < treatment for period in periods)
        post = sum(period >= treatment for period in periods)
        body = {
            "episode_sha256": episode["episode_sha256"],
            "entity_id": episode["entity_id"], "periods": periods,
            "treatment_period": treatment,
            "treatment_period_basis": "first_full_entity_fiscal_year_after_exact_event",
            "pre_period_count": pre, "post_period_count": post,
            "status": (
                "treated_history_ready" if pre >= 3 and post >= 1
                else "treated_history_underpowered"
            ),
        }
        rows.append({**body, "history_status_sha256": stable_sha256(body)})
    return sorted(rows, key=lambda row: (row["entity_id"], row["episode_sha256"]))


def _activation_cells(frontier: Mapping[str, Any]) -> list[dict[str, Any]]:
    cells = {}
    for projection in frontier.get("projections") or ():
        if projection.get("frontier_status") != "frontier":
            continue
        for cell in projection.get("cells") or ():
            if not cell.get("treated_support_ready"):
                continue
            row = {
                **dict(cell), "program_id": projection["program_id"],
                "moderator_fields": list(projection["moderator_fields"]),
            }
            cells.setdefault(str(cell["cell_sha256"]), row)
    return sorted(cells.values(), key=lambda row: (
        -len(row["moderator_fields"]), -row["entity_count"],
        -row["event_year_count"], row["cell_sha256"],
    ))


def _control_requests(
    replay: Mapping[str, Any], catalog: Mapping[str, Any], frontier: Mapping[str, Any],
    *, max_requests: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    episodes = {str(row["episode_sha256"]): row for row in replay.get("episodes") or ()}
    activation_cells = _activation_cells(frontier)
    cell_by_episode: dict[str, set[str]] = defaultdict(set)
    for cell in activation_cells:
        for episode_sha in cell["episode_sha256s"]:
            cell_by_episode[str(episode_sha)].add(str(cell["cell_sha256"]))
    uncovered = {str(row["cell_sha256"]) for row in activation_cells}
    anchors = []
    while uncovered and len(anchors) < max(1, math.ceil(max_requests / 4)):
        remaining = [sha for sha in episodes if sha not in anchors]
        if not remaining:
            break
        selected = max(remaining, key=lambda sha: (
            len(cell_by_episode.get(sha, set()) & uncovered),
            len(cell_by_episode.get(sha, set())), sha,
        ))
        if not (cell_by_episode.get(selected, set()) & uncovered):
            break
        anchors.append(selected)
        uncovered -= cell_by_episode[selected]

    equity_rows = [
        row for row in catalog.get("securities") or ()
        if row.get("entity_kind") == "public_equity"
        and row.get("security_kind") == "common_equity"
        and row.get("country") == "United States"
        and float(row.get("market_cap") or 0) > 0
    ]
    by_symbol = {str(row["symbol"]).upper(): row for row in equity_rows}
    excluded = {str(row["entity_id"]).upper() for row in episodes.values()}
    requests, blocks = [], []
    for episode_sha in anchors:
        episode = episodes[episode_sha]
        symbol = str(episode["entity_id"]).upper()
        focal = by_symbol.get(symbol)
        if not focal or not str(focal.get("industry") or ""):
            blocks.append({
                "episode_sha256": episode_sha, "entity_id": symbol,
                "reason": "current_public_industry_proxy_unavailable",
            })
            continue
        focal_cap = float(focal["market_cap"])
        occurred = timestamp_key(str(episode["occurred_at"]))
        latest_usable_ipo_year = occurred.year - 3
        candidates = sorted(
            (
                row for row in equity_rows
                if str(row.get("industry") or "") == str(focal["industry"])
                and str(row["symbol"]).upper() not in excluded
                and int(row.get("ipo_year") or 9999) <= latest_usable_ipo_year
            ),
            key=lambda row: (
                abs(math.log(float(row["market_cap"])) - math.log(focal_cap)),
                str(row["symbol"]),
            ),
        )[:8]
        start = (occurred - timedelta(days=3 * 365)).isoformat(timespec="seconds").replace(
            "+00:00", "Z"
        )
        for peer in candidates:
            body = {
                "schema": "jaggedthoughts-historical-strategy-control-source-request-v1",
                "treated_episode_sha256": episode_sha,
                "treated_entity_id": symbol, "peer_entity_id": str(peer["symbol"]).upper(),
                "activation_cell_sha256s": sorted(cell_by_episode[episode_sha]),
                "search_start_at": start, "search_end_at": episode["due_at"],
                "outcome_metric_id": "owner_earnings_margin", "minimum_pre_periods": 3,
                "minimum_post_periods": 1,
                "required_source_classes": ["sec_submissions", "sec_companyfacts"],
                "required_evidence": [
                    "bounded_no_selected_transaction_phenotype",
                    "point_in_time_owner_earnings_history",
                    "pretrend_fit", "event_time_environment_compatibility",
                ],
                "current_catalog_priority_proxy": {
                    "industry": peer["industry"], "sector": peer.get("sector") or "",
                    "market_cap": float(peer["market_cap"]),
                    "available_at": peer["available_at"],
                    "catalog_sha256": catalog["catalog_sha256"],
                },
                "admission_status": "screened_not_admitted",
                "capital_authority": False,
            }
            requests.append({**body, "request_sha256": stable_sha256(body)})
            if len(requests) >= max_requests:
                break
        if len(requests) >= max_requests:
            break
    return requests, blocks


def _verified_source_payload(root: Path, receipt: Mapping[str, Any]) -> Mapping[str, Any]:
    path = (root / str(receipt.get("raw_path") or "")).resolve()
    path.relative_to(root)
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != receipt.get("content_sha256"):
        raise ValueError("historical control source content hash mismatch")
    payload = json.loads(content)
    if not isinstance(payload, Mapping):
        raise ValueError("historical control source payload must be an object")
    return payload


def _receipt_or_cache(
    root: Path, heads: Mapping[str, Mapping[str, Any]], source_id: str,
) -> Mapping[str, Any] | None:
    if source_id in heads:
        return heads[source_id]
    candidates = sorted((root / "sources" / "raw" / source_id).glob("*.json"))
    if not candidates:
        return None
    path = candidates[-1]
    content = path.read_bytes()
    body = {
        "source_id": source_id,
        "content_sha256": hashlib.sha256(content).hexdigest(),
        "raw_path": path.relative_to(root).as_posix(),
        "lineage_status": "content_bound_cache_awaiting_canonical_receipt_head",
    }
    return {**body, "receipt_sha256": stable_sha256(body)}


def _pretrend_distance(left: Mapping[int, float], right: Mapping[int, float], before: int) -> dict[str, Any]:
    years = sorted(set(left) & set(right) & set(range(before)))
    deltas = [
        abs((left[b] - left[a]) - (right[b] - right[a]))
        for a, b in zip(years, years[1:]) if b == a + 1
    ]
    return {
        "common_pre_periods": years,
        "common_pre_period_count": len(years),
        "mean_absolute_trend_gap": sum(deltas) / len(deltas) if deltas else None,
        "trend_difference_count": len(deltas),
    }


def _filing_rows(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    columns = {
        key: list(value) for key, value in payload.items() if isinstance(value, list)
    }
    count = max((len(value) for value in columns.values()), default=0)
    return [
        {key: values[index] for key, values in columns.items() if index < len(values)}
        for index in range(count)
    ]


def _bulk_control_evidence(
    root: Path, requests: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    submissions_receipt = json.loads((
        root / "sources" / "bulk" / "sec_submissions" / "latest.json"
    ).read_text(encoding="utf-8"))
    companyfacts_receipt = json.loads((
        root / "sources" / "bulk" / "sec_companyfacts" / "latest.json"
    ).read_text(encoding="utf-8"))
    submission_receipt_sha = _checked_hash(
        submissions_receipt, "receipt_sha256", "bulk submissions receipt",
    )
    companyfacts_receipt_sha = _checked_hash(
        companyfacts_receipt, "receipt_sha256", "bulk Company Facts receipt",
    )
    registry_path = max(
        (root / "sources" / "registry").glob("sec-company-tickers-*.json"),
        key=lambda path: path.stat().st_mtime_ns,
    )
    registry_bytes = registry_path.read_bytes()
    registry = json.loads(registry_bytes)
    cik_by_ticker = {
        str(row.get("ticker") or "").upper(): str(row.get("cik_str") or "").zfill(10)
        for row in registry.values() if isinstance(row, Mapping)
    }
    submission_path = (root / str(submissions_receipt["raw_path"])).resolve()
    companyfacts_path = (root / str(companyfacts_receipt["raw_path"])).resolve()
    submission_path.relative_to(root)
    companyfacts_path.relative_to(root)
    rows = []
    with (
        zipfile.ZipFile(submission_path) as submissions,
        zipfile.ZipFile(companyfacts_path) as companyfacts,
    ):
        submission_names = set(submissions.namelist())
        companyfacts_names = set(companyfacts.namelist())
        for request in requests:
            entity = str(request["peer_entity_id"]).upper()
            cik = cik_by_ticker.get(entity)
            if not cik:
                rows.append({
                    "request_sha256": request["request_sha256"],
                    "peer_entity_id": entity, "status": "ticker_cik_unresolved",
                })
                continue
            base_name = f"CIK{cik}.json"
            if base_name not in submission_names or base_name not in companyfacts_names:
                rows.append({
                    "request_sha256": request["request_sha256"],
                    "peer_entity_id": entity, "cik": cik,
                    "status": "bulk_member_missing",
                })
                continue
            base = json.loads(submissions.read(base_name))
            filing_sets = [dict((base.get("filings") or {}).get("recent") or {})]
            start, end = request["search_start_at"][:10], request["search_end_at"][:10]
            member_names = [base_name]
            for descriptor in (base.get("filings") or {}).get("files") or ():
                name = str(descriptor.get("name") or "")
                if (
                    name in submission_names
                    and str(descriptor.get("filingFrom") or "9999-99-99") <= end
                    and str(descriptor.get("filingTo") or "0000-00-00") >= start
                ):
                    filing_sets.append(json.loads(submissions.read(name)))
                    member_names.append(name)
            filing_rows = [row for payload in filing_sets for row in _filing_rows(payload)]
            filing_dates = sorted(str(row.get("filingDate") or "") for row in filing_rows)
            events = [
                {
                    "filing_date": str(row.get("filingDate") or ""),
                    "accession_number": str(row.get("accessionNumber") or ""),
                    "primary_document": str(row.get("primaryDocument") or ""),
                    "items": str(row.get("items") or ""),
                }
                for row in filing_rows
                if start <= str(row.get("filingDate") or "") <= end
                and row.get("form") == "8-K"
                and "2.01" in str(row.get("items") or "").split(",")
            ]
            observations = list(parse_sec_companyfacts(
                companyfacts.read(base_name),
                {
                    "id": f"sec_bulk_companyfacts_{cik}",
                    "entity_id": entity, "selections": _SELECTIONS,
                },
            ))
            earliest = {}
            for observation in observations:
                key = (observation.observed_at, observation.metric_id)
                current = earliest.get(key)
                if current is None or (observation.available_at, observation.observation_id) < (
                    current.available_at, current.observation_id,
                ):
                    earliest[key] = observation
            annual_history = []
            for observed in sorted({key[0] for key in earliest}):
                facts = {
                    metric: earliest.get((observed, metric))
                    for metric in (
                        "revenue_fy", "operating_cash_flow_fy", "capital_expenditure_fy",
                    )
                }
                if not all(facts.values()) or not float(facts["revenue_fy"].value):
                    continue
                margin = (
                    float(facts["operating_cash_flow_fy"].value)
                    - float(facts["capital_expenditure_fy"].value)
                ) / float(facts["revenue_fy"].value)
                annual_history.append({
                    "observed_at": observed,
                    "available_at": max(row.available_at for row in facts.values()),
                    "owner_earnings_margin": margin,
                    "observation_ids": sorted(row.observation_id for row in facts.values()),
                })
            body = {
                "request_sha256": request["request_sha256"],
                "peer_entity_id": entity, "cik": cik,
                "status": "bulk_evidence_ready",
                "evidence_transform_revision": "full_history_selection_bounded_v2",
                "bounded_submission_coverage": {
                    "earliest_filing_date": min(filing_dates, default=None),
                    "latest_filing_date": max(filing_dates, default=None),
                    "requested_start_at": request["search_start_at"],
                    "requested_end_at": request["search_end_at"],
                    "covers_requested_window": bool(
                        filing_dates and min(filing_dates) <= start and max(filing_dates) >= end
                    ),
                },
                "related_transaction_events": events,
                "annual_history": annual_history,
                "source_binding": {
                    "bulk_submissions_receipt_sha256": submission_receipt_sha,
                    "bulk_companyfacts_receipt_sha256": companyfacts_receipt_sha,
                    "submission_members": sorted(member_names),
                    "companyfacts_member": base_name,
                    "registry_sha256": hashlib.sha256(registry_bytes).hexdigest(),
                },
            }
            rows.append({**body, "evidence_sha256": stable_sha256(body)})
    return rows


def _known_strategy_events(root: Path) -> dict[str, list[dict[str, Any]]]:
    by_entity: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    result_root = root / "institutional_learning" / "strategy_cohorts" / "results"
    for path in sorted(result_root.glob("*.json")):
        result = json.loads(path.read_text(encoding="utf-8"))
        if not result.get("result_sha256"):
            continue
        result_sha = _checked_hash(result, "result_sha256", "strategy cohort result")
        entity = str(result.get("peer_entity_id") or "").upper()
        if not entity:
            continue
        for event in result.get("events") or ():
            event_sha = str(event.get("event_sha256") or "")
            if not event_sha:
                continue
            by_entity[entity][event_sha] = {
                "event_sha256": event_sha,
                "occurred_at": event.get("occurred_at"),
                "available_at": event.get("available_at"),
                "implementation_mode": event.get("implementation_mode"),
                "implementation_state": event.get("implementation_state"),
                "cohort_result_sha256": result_sha,
            }
    return {
        entity: [events[key] for key in sorted(events)]
        for entity, events in sorted(by_entity.items())
    }


def _screen_control_sources(
    root: Path, replay: Mapping[str, Any], histories: Iterable[Mapping[str, Any]],
    requests: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    heads_path = root / "data" / "source_receipt_heads.json"
    if not heads_path.exists():
        return []
    heads = {
        str(row["source_id"]): row
        for row in json.loads(heads_path.read_text(encoding="utf-8")).get("receipts") or ()
    }
    episodes = {str(row["episode_sha256"]): row for row in replay.get("episodes") or ()}
    evidence_path = (
        root / "institutional_learning" / "historical_strategy_event_replay"
        / "control-evidence-latest.json"
    )
    evidence_payload = (
        json.loads(evidence_path.read_text(encoding="utf-8"))
        if evidence_path.is_file() else {}
    )
    bulk_evidence = {
        str(row.get("request_sha256") or ""): row
        for row in evidence_payload.get("evidence") or ()
    }
    known_events = _known_strategy_events(root)
    treatment_periods = {
        str(row["episode_sha256"]): int(row["treatment_period"]) for row in histories
    }
    treated_report_index = compile_company_quality_histories(
        entity_ids={str(row["entity_id"]) for row in episodes.values()},
        observations_path=root / "data" / "observations.csv",
        as_of=str(replay["evidence_as_of"]), min_years=2,
    )
    peer_report_index = compile_company_quality_histories(
        entity_ids={str(row["peer_entity_id"]) for row in requests},
        observations_path=root / "data" / "observations.csv",
        as_of=str(replay["evidence_as_of"]), min_years=2,
    )
    treated_histories = {
        episode_sha: {
            int(str(report["history"][-1]["observed_at"])[:4]):
            float(report["history"][-1]["owner_earnings_margin"])
            for report in treated_report_index.get(str(episode["entity_id"]).upper(), ())
            if report["history"][-1].get("owner_earnings_margin") is not None
            and str(report["available_at"]) <= str(episode["available_at"])
        }
        for episode_sha, episode in episodes.items()
    }
    rows = []
    for request in requests:
        peer = str(request["peer_entity_id"]).upper()
        episode_sha = str(request["treated_episode_sha256"])
        treated_episode = episodes[episode_sha]
        start, end = request["search_start_at"][:10], request["search_end_at"][:10]
        cross_corpus_events = [
            event for event in known_events.get(peer, ())
            if str(event.get("implementation_mode") or "")
            == str(treated_episode.get("implementation_mode") or "")
            and str(event.get("implementation_state") or "") in {
                "operational", "completed",
            }
            and start <= str(event.get("occurred_at") or "")[:10] <= end
            and str(event.get("available_at") or "")[:10] <= end
        ]
        bulk = bulk_evidence.get(str(request["request_sha256"]))
        submissions_receipt = _receipt_or_cache(
            root, heads, f"sec_{peer.lower()}_submissions",
        )
        facts_receipt = _receipt_or_cache(
            root, heads, f"sec_{peer.lower()}_companyfacts",
        )
        reasons = []
        events = []
        coverage = {}
        source_receipt_sha256s = []
        if bulk and bulk.get("status") == "bulk_evidence_ready":
            coverage = dict(bulk["bounded_submission_coverage"])
            events = list(bulk.get("related_transaction_events") or ())
            source_receipt_sha256s = [
                str(value) for value in (bulk.get("source_binding") or {}).values()
                if isinstance(value, str) and len(value) == 64
            ] + [str(bulk["evidence_sha256"])]
            if not coverage.get("covers_requested_window"):
                reasons.append("bounded_submission_history_incomplete")
            if events:
                reasons.append("related_material_transaction_found")
        elif not submissions_receipt or not facts_receipt:
            reasons.append("required_source_receipt_missing")
        else:
            payload = _verified_source_payload(root, submissions_receipt)
            recent = (payload.get("filings") or {}).get("recent") or {}
            dates = list(recent.get("filingDate") or ())
            coverage = {
                "earliest_filing_date": min(dates, default=None),
                "latest_filing_date": max(dates, default=None),
                "requested_start_at": request["search_start_at"],
                "requested_end_at": request["search_end_at"],
            }
            coverage["covers_requested_window"] = bool(
                dates and min(dates) <= start and max(dates) >= end
            )
            if not coverage["covers_requested_window"]:
                reasons.append("bounded_submission_history_incomplete")
            for index, form in enumerate(recent.get("form") or ()):
                date = str(dates[index])
                if not (start <= date <= end and form == "8-K"):
                    continue
                if "2.01" not in str((recent.get("items") or ())[index]).split(","):
                    continue
                events.append({
                    "filing_date": date,
                    "accession_number": str(recent["accessionNumber"][index]),
                    "primary_document": str(recent["primaryDocument"][index]),
                    "items": str(recent["items"][index]),
                })
            if events:
                reasons.append("related_material_transaction_found")
            source_receipt_sha256s = sorted({
                str(row.get("receipt_sha256") or "")
                for row in (submissions_receipt, facts_receipt) if row
            })
        if cross_corpus_events:
            reasons.append("cross_corpus_same_mode_strategy_event_found")
        treatment_period = treatment_periods[episode_sha]
        peer_history = (
            {
                int(str(row["observed_at"])[:4]): float(row["owner_earnings_margin"])
                for row in bulk.get("annual_history") or ()
                if str(row.get("available_at") or "") <= str(request["search_end_at"])
            }
            if bulk and bulk.get("status") == "bulk_evidence_ready"
            else {
                int(str(report["history"][-1]["observed_at"])[:4]):
                float(report["history"][-1]["owner_earnings_margin"])
                for report in peer_report_index.get(peer, ())
                if report["history"][-1].get("owner_earnings_margin") is not None
                and str(report["available_at"]) <= str(request["search_end_at"])
            }
        )
        pretrend = _pretrend_distance(
            treated_histories[episode_sha], peer_history, treatment_period,
        )
        if pretrend["common_pre_period_count"] < int(request["minimum_pre_periods"]):
            reasons.append("common_pretrend_history_incomplete")
        status = (
            "excluded_related_transaction" if any(reason in reasons for reason in (
                "related_material_transaction_found",
                "cross_corpus_same_mode_strategy_event_found",
            ))
            else "source_gap" if reasons
            else "candidate_ready_for_pretrend_ranking"
        )
        body = {
            "request_sha256": request["request_sha256"],
            "treated_episode_sha256": episode_sha,
            "peer_entity_id": peer, "status": status,
            "bounded_submission_coverage": coverage,
            "related_transaction_events": events,
            "cross_corpus_strategy_events": cross_corpus_events,
            "pretrend": pretrend,
            "source_receipt_sha256s": sorted(set(source_receipt_sha256s)),
            "kill_reasons": sorted(set(reasons)),
            "admissible_control": False,
            "remaining_admission_gate": (
                "event_time_environment_and_joint_pretrend_selection"
                if not reasons else None
            ),
        }
        rows.append({**body, "screen_sha256": stable_sha256(body)})
    return sorted(rows, key=lambda row: (
        row["status"] != "candidate_ready_for_pretrend_ranking",
        (row["pretrend"].get("mean_absolute_trend_gap") is None),
        row["pretrend"].get("mean_absolute_trend_gap") or 0,
        row["peer_entity_id"], row["request_sha256"],
    ))


def compile_workspace_historical_strategy_control_design(
    workspace: str | Path, *, max_requests: int = _DEFAULT_MAX_REQUESTS,
) -> dict[str, Any]:
    """Freeze moderator selection and the next source acquisition frontier."""
    if max_requests < 1:
        raise ValueError("historical strategy control request cap must be positive")
    root = Path(workspace).expanduser().resolve()
    replay = json.loads((
        root / "institutional_learning" / "historical_strategy_event_replay" / "latest.json"
    ).read_text(encoding="utf-8"))
    if replay.get("schema") != HISTORICAL_STRATEGY_EVENT_REPLAY_SCHEMA:
        raise ValueError("historical strategy control design requires the typed replay")
    replay_sha = _checked_hash(replay, "replay_sha256", "historical strategy replay")
    catalog = json.loads((root / "universe" / "catalog-latest.json").read_text(encoding="utf-8"))
    catalog_sha = _checked_hash(catalog, "catalog_sha256", "public market catalog")
    frontier = _moderator_frontier(replay)
    histories = _history_status(root, replay)
    requests, blocks = _control_requests(
        replay, catalog, frontier, max_requests=max_requests,
    )
    screens = _screen_control_sources(root, replay, histories, requests)
    ready_histories = sum(row["status"] == "treated_history_ready" for row in histories)
    ready_controls = sum(
        row["status"] == "candidate_ready_for_pretrend_ranking" for row in screens
    )
    activation_cells = _activation_cells(frontier)
    body = {
        "schema": HISTORICAL_STRATEGY_CONTROL_DESIGN_SCHEMA,
        "generated_at": canonical_timestamp(
            str(catalog["retrieved_at"]), "historical control design generated_at",
        ),
        "replay_sha256": replay_sha, "market_catalog_sha256": catalog_sha,
        "moderator_frontier": frontier,
        "activation_cell_count": len(activation_cells),
        "activation_cells": activation_cells,
        "treated_history_status": histories,
        "treated_history_ready_count": ready_histories,
        "control_source_request_count": len(requests),
        "control_source_requests": requests, "source_blocks": blocks,
        "control_screen_count": len(screens), "control_screens": screens,
        "pretrend_rankable_control_count": ready_controls,
        "estimation_contract": {
            "primary": "unadjusted_group_time_att_with_never_or_not_yet_treated_controls",
            "diagnostic_robustness": [
                "untreated_observation_imputation_event_study",
                "synthetic_difference_in_differences_when_preperiod_support_allows",
                "parallel_trend_violation_sensitivity",
            ],
            "implemented_primary": "ztare.investment.institutional_learning.group_time_att_v3",
            "run_status": "blocked_until_controls_admitted",
        },
        "selection_boundary": {
            "outcome_used_for_moderator_selection": False,
            "structural_inputs": [
                "typed_transaction_phenotype", "entity_replication", "event_timing_support",
            ],
            "catalog_use": "retrieval_only_control_acquisition_priority",
            "historical_result_use": "conjecture_generation_and_design_diagnostics_only",
        },
        "causal_estimate_ran": False, "promotion_eligible": False,
        "next_activation": (
            f"Resolve event-time environment and jointly select {ready_controls} pretrend-ranked candidates."
            if ready_controls else
            f"Hydrate and deterministically screen {len(requests)} ranked control candidates."
            if requests else "Expand source-bound environment coverage before selecting controls."
        ),
        "paper_policy_authority": False, "capital_authority": False,
    }
    design = {**body, "control_design_sha256": stable_sha256(body)}
    destination = (
        root / "institutional_learning" / "historical_strategy_event_replay"
        / "control-design-latest.json"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(
        json.dumps(design, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return design


def acquire_workspace_historical_strategy_controls(
    workspace: str | Path, *, design: Mapping[str, Any] | None = None,
    limit: int = 4,
) -> dict[str, Any]:
    """Hydrate a bounded batch from the typed historical-control frontier."""
    if limit < 1:
        raise ValueError("historical strategy control acquisition limit must be positive")
    root = Path(workspace).expanduser().resolve()
    before = dict(design or compile_workspace_historical_strategy_control_design(root))
    if before.get("schema") != HISTORICAL_STRATEGY_CONTROL_DESIGN_SCHEMA:
        raise ValueError("historical strategy control acquisition requires a control design")
    before_sha = _checked_hash(before, "control_design_sha256", "historical control design")
    requests = {
        str(row["request_sha256"]): row
        for row in before.get("control_source_requests") or ()
    }
    selected = []
    seen: set[str] = set()
    for screen in before.get("control_screens") or ():
        request = requests.get(str(screen.get("request_sha256") or ""))
        entity = str(screen.get("peer_entity_id") or "").upper()
        if (
            not request or not entity or entity in seen
            or "required_source_receipt_missing" not in (screen.get("kill_reasons") or ())
        ):
            continue
        selected.append(request)
        seen.add(entity)
        if len(selected) >= limit:
            break

    try:
        acquired_rows = _bulk_control_evidence(root, selected) if selected else []
    except (FileNotFoundError, KeyError, OSError, TypeError, ValueError, zipfile.BadZipFile) as error:
        acquired_rows = [{
            "request_sha256": request["request_sha256"],
            "peer_entity_id": request["peer_entity_id"],
            "status": "failed",
            "error": f"{type(error).__name__}: {error}"[:1_000],
        } for request in selected]
    evidence_path = (
        root / "institutional_learning" / "historical_strategy_event_replay"
        / "control-evidence-latest.json"
    )
    prior_evidence = (
        json.loads(evidence_path.read_text(encoding="utf-8"))
        if evidence_path.is_file() else {}
    )
    evidence_by_request = {
        str(row.get("request_sha256") or ""): row
        for row in prior_evidence.get("evidence") or ()
    }
    evidence_by_request.update({
        str(row.get("request_sha256") or ""): row for row in acquired_rows
    })
    evidence_body = {
        "schema": "jaggedthoughts-historical-strategy-control-evidence-v1",
        "evidence_transform_revision": "full_history_selection_bounded_v2",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
            "+00:00", "Z"
        ),
        "control_design_sha256": before_sha,
        "evidence": [evidence_by_request[key] for key in sorted(evidence_by_request)],
        "authority": "public_source_evidence_only",
        "capital_authority": False,
    }
    evidence_payload = {
        **evidence_body, "evidence_set_sha256": stable_sha256(evidence_body),
    }
    temporary = evidence_path.with_name(f".{evidence_path.name}.tmp")
    temporary.write_text(
        json.dumps(evidence_payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(evidence_path)
    actions = [{
        "peer_entity_id": row.get("peer_entity_id"),
        "request_sha256": row.get("request_sha256"),
        "status": row.get("status"),
        "evidence_sha256": row.get("evidence_sha256"),
        "error": row.get("error"),
    } for row in acquired_rows]

    after = compile_workspace_historical_strategy_control_design(root)
    acquired = sum(row["status"] == "bulk_evidence_ready" for row in actions)
    body = {
        "schema": HISTORICAL_STRATEGY_CONTROL_ACQUISITION_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace(
            "+00:00", "Z"
        ),
        "before_control_design_sha256": before_sha,
        "after_control_design_sha256": after["control_design_sha256"],
        "batch_limit": limit,
        "selected_request_count": len(selected),
        "attempted_entity_count": acquired,
        "actions": actions,
        "before": {
            "pretrend_rankable_control_count": int(
                before.get("pretrend_rankable_control_count") or 0
            ),
            "source_gap_count": sum(
                row.get("status") == "source_gap"
                for row in before.get("control_screens") or ()
            ),
        },
        "after": {
            "pretrend_rankable_control_count": int(
                after.get("pretrend_rankable_control_count") or 0
            ),
            "source_gap_count": sum(
                row.get("status") == "source_gap"
                for row in after.get("control_screens") or ()
            ),
        },
        "status": "advanced" if acquired else "no_public_source_request_due",
        "source_mode": "existing_sec_bulk_archives",
        "next_activation": after.get("next_activation"),
        "subscription_provider_called": False,
        "causal_estimate_ran": False,
        "capital_authority": False,
    }
    receipt = {**body, "acquisition_sha256": stable_sha256(body)}
    destination = (
        root / "institutional_learning" / "historical_strategy_event_replay"
        / "control-acquisition-latest.json"
    )
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_text(
        json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)
    return {"acquisition": receipt, "design": after}


__all__ = [
    "HISTORICAL_STRATEGY_CONTROL_ACQUISITION_SCHEMA",
    "HISTORICAL_STRATEGY_CONTROL_DESIGN_SCHEMA",
    "HISTORICAL_STRATEGY_MODERATOR_DIMENSIONS",
    "acquire_workspace_historical_strategy_controls",
    "enumerate_historical_strategy_moderator_programs",
    "compile_workspace_historical_strategy_control_design",
]
