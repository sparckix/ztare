"""Acquire exact strategy-event timing without rewriting the authored move."""

from __future__ import annotations

from datetime import timedelta
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256

from .contracts import canonical_timestamp, require_text, timestamp_key
from .strategy_options import IMPLEMENTATION_MODES


STRATEGY_EVENT_REFINEMENT_REQUEST_SCHEMA = (
    "jaggedthoughts-strategy-event-refinement-request-v1"
)
STRATEGY_EVENT_REFINEMENT_RESULT_SCHEMA = (
    "jaggedthoughts-strategy-event-refinement-result-v1"
)
STRATEGY_EVENT_REFINEMENT_JOB_KIND = "jaggedthoughts_strategy_event_refinement_research"
_CLASSIFICATIONS = {
    "exact_implementation_event_found",
    "interval_remains_censored",
    "insufficient_source_coverage",
}
_REFINEMENT_RECHECK_DAYS = {
    "interval_remains_censored": 90,
    "insufficient_source_coverage": 30,
}


def effective_exact_implementation_event(
    move: Mapping[str, Any],
) -> dict[str, Any] | None:
    """Lower authored or refinement-derived exact timing into one event ABI."""
    authored = move.get("implementation_event")
    if isinstance(authored, Mapping) and authored.get(
        "treatment_timing_status"
    ) == "exact_adoption_event":
        body = dict(authored)
        declared = str(body.pop("implementation_event_sha256", ""))
        if declared == stable_sha256(body):
            return dict(authored)

    refinement = move.get("timing_refinement")
    if not isinstance(refinement, Mapping) or refinement.get(
        "classification"
    ) != "exact_implementation_event_found":
        return None
    exact = refinement.get("exact_event")
    if not isinstance(exact, Mapping):
        return None
    exact_body = dict(exact)
    exact_sha = str(exact_body.pop("event_sha256", ""))
    request_sha = str(refinement.get("request_sha256") or "")
    result_sha = str(refinement.get("result_sha256") or "")
    if (
        exact_sha != stable_sha256(exact_body)
        or any(len(value) != 64 for value in (request_sha, result_sha))
    ):
        return None
    body = {
        "event_id": require_text(exact.get("event_id"), "refined event id"),
        "event_kind": "adoption",
        "implementation_mode": require_text(
            exact.get("implementation_mode"), "refined implementation mode",
        ),
        "status_after": (
            "completed" if exact.get("implementation_state") == "completed" else "underway"
        ),
        "occurred_at": canonical_timestamp(exact.get("occurred_at"), "refined event occurred_at"),
        "available_at": canonical_timestamp(exact.get("available_at"), "refined event available_at"),
        "timing_precision": "date",
        "treatment_timing_status": "exact_adoption_event",
        "source_refs": sorted(map(str, exact.get("source_urls") or ())),
        "refinement_request_sha256": request_sha,
        "refinement_result_sha256": result_sha,
        "refinement_event_sha256": exact_sha,
    }
    if exact.get("mechanism_effective_until") is not None:
        body["mechanism_effective_until"] = canonical_timestamp(
            exact.get("mechanism_effective_until"),
            "refined event mechanism_effective_until",
        )
    return {**body, "implementation_event_sha256": stable_sha256(body)}


def _checked(payload: Mapping[str, Any], field: str, label: str) -> str:
    body = dict(payload)
    declared = require_text(body.pop(field, ""), field)
    if declared != stable_sha256(body):
        raise ValueError(f"{label} content hash mismatch")
    return declared


def compile_strategy_event_refinement_request(
    move: Mapping[str, Any], *, library_sha256: str, search_end_at: str,
) -> dict[str, Any]:
    """Freeze one exact-event search for an unresolved authored move."""
    if move.get("claim_status") != "supported":
        raise ValueError("strategy event refinement requires a supported move")
    if move.get("causal_panel_status") == "treatment_event_ready":
        raise ValueError("strategy event refinement cannot target an exact event")
    end = canonical_timestamp(search_end_at, "strategy event search end")
    evidence_epoch = canonical_timestamp(
        move.get("evidence_epoch"), "strategy event evidence epoch",
    )
    start = timestamp_key(evidence_epoch) - timedelta(days=3650)
    body = {
        "schema": STRATEGY_EVENT_REFINEMENT_REQUEST_SCHEMA,
        "request_id": f"strategy-event-refinement:{str(move['move_sha256'])[:24]}",
        "created_at": end,
        "library_sha256": require_text(library_sha256, "strategy move library hash"),
        "move_sha256": require_text(move.get("move_sha256"), "strategy move hash"),
        "strategy_frontier_sha256": require_text(
            move.get("strategy_frontier_sha256"), "strategy frontier hash",
        ),
        "entity_id": require_text(move.get("entity_id"), "strategy move entity"),
        "option_id": require_text(move.get("option_id"), "strategy move option"),
        "move_description": require_text(
            move.get("description"), "strategy move description",
        ),
        "mechanism_signature": dict(move.get("mechanism_signature") or {}),
        "mechanism_phenotype": dict(move.get("mechanism_phenotype") or {}),
        "current_implementation_event": dict(move.get("implementation_event") or {}),
        "search_start_at": start.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "search_end_at": end,
        "required_source_classes": ["sec_filings", "issuer_investor_materials"],
        "classification_set": sorted(_CLASSIFICATIONS),
        "expected_exit": "exact_source_bound_event_or_preserved_interval",
        "authority": "event_timing_research_only",
        "capital_authority": False,
    }
    return {**body, "request_sha256": stable_sha256(body)}


def compile_strategy_event_refinement_result(
    raw: Mapping[str, Any], request: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate a primary-source event-timing answer against its frozen search."""
    if request.get("schema") != STRATEGY_EVENT_REFINEMENT_REQUEST_SCHEMA:
        raise ValueError("strategy event result requires a refinement request")
    request_sha = _checked(request, "request_sha256", "strategy event request")
    if raw.get("schema") != STRATEGY_EVENT_REFINEMENT_RESULT_SCHEMA:
        raise ValueError("unsupported strategy event refinement result schema")
    if (
        raw.get("request_sha256") != request_sha
        or raw.get("move_sha256") != request.get("move_sha256")
        or raw.get("entity_id") != request.get("entity_id")
    ):
        raise ValueError("strategy event result crossed its request identity")
    classification = require_text(raw.get("classification"), "event classification")
    if classification not in _CLASSIFICATIONS:
        raise ValueError("unsupported strategy event refinement classification")
    sources = []
    for raw_source in raw.get("sources") or ():
        source = dict(raw_source) if isinstance(raw_source, Mapping) else {}
        url = require_text(source.get("url"), "strategy event source URL")
        if not url.startswith("https://"):
            raise ValueError("strategy event sources must be HTTPS primary documents")
        kind = require_text(source.get("source_kind"), "strategy event source kind")
        if kind not in {"filing", "issuer"}:
            raise ValueError("strategy event sources must be filings or issuer documents")
        published = canonical_timestamp(
            source.get("published_at"), "strategy event source published_at",
        )
        if timestamp_key(published) > timestamp_key(str(request["search_end_at"])):
            raise ValueError("strategy event source postdates the frozen search")
        supports = sorted({
            require_text(value, "strategy event source support")
            for value in source.get("supports") or ()
        })
        if not supports:
            raise ValueError("strategy event source requires a supported claim")
        sources.append({
            "url": url, "source_kind": kind,
            "published_at": published, "supports": supports,
        })
    if not sources:
        raise ValueError("strategy event result requires opened primary sources")
    coverage = dict(raw.get("coverage") or {})
    if (
        coverage.get("search_start_at") != request.get("search_start_at")
        or coverage.get("search_end_at") != request.get("search_end_at")
    ):
        raise ValueError("strategy event result changed its search window")
    exact_event = None
    if isinstance(raw.get("exact_event"), Mapping):
        event = dict(raw["exact_event"])
        occurred = canonical_timestamp(event.get("occurred_at"), "exact event occurred_at")
        available = canonical_timestamp(event.get("available_at"), "exact event available_at")
        if timestamp_key(occurred) < timestamp_key(str(request["search_start_at"])):
            raise ValueError("exact event predates the frozen search")
        if timestamp_key(available) < timestamp_key(occurred):
            raise ValueError("exact event cannot be available before occurrence")
        if timestamp_key(available) > timestamp_key(str(request["search_end_at"])):
            raise ValueError("exact event postdates the frozen search")
        mode = require_text(event.get("implementation_mode"), "exact event implementation mode")
        if mode not in IMPLEMENTATION_MODES - {"unspecified"}:
            raise ValueError("exact event implementation mode is unsupported")
        state = require_text(event.get("implementation_state"), "exact event state")
        if state not in {"operational", "completed"}:
            raise ValueError("exact event must be operational or completed")
        refs = sorted({
            require_text(value, "exact event source URL")
            for value in event.get("source_urls") or ()
        })
        if not refs or not set(refs).issubset({row["url"] for row in sources}):
            raise ValueError("exact event must bind opened primary sources")
        effective_until = None
        if event.get("mechanism_effective_until") is not None:
            effective_until = canonical_timestamp(
                event.get("mechanism_effective_until"),
                "exact event mechanism_effective_until",
            )
            if timestamp_key(effective_until) < timestamp_key(occurred):
                raise ValueError("mechanism effective window ends before its event")
        if mode == "supply_commitment" and (
            effective_until is None
            or not any(
                row["url"] in refs
                and "mechanism_effective_until" in set(row["supports"])
                for row in sources
            )
        ):
            raise ValueError("supply commitment requires a source-bound effective_until")
        event_body = {
            "event_id": require_text(event.get("event_id"), "exact event id"),
            "description": require_text(event.get("description"), "exact event description"),
            "occurred_at": occurred, "available_at": available,
            "implementation_mode": mode, "implementation_state": state,
            "timing_precision": "date", "source_urls": refs,
        }
        if effective_until is not None:
            event_body["mechanism_effective_until"] = effective_until
        exact_event = {**event_body, "event_sha256": stable_sha256(event_body)}
    if (classification == "exact_implementation_event_found") != bool(exact_event):
        raise ValueError("exact-event classification and evidence differ")
    censored_interval = None
    interval_declared = "censored_interval" in raw
    if isinstance(raw.get("censored_interval"), Mapping):
        interval = dict(raw["censored_interval"])
        earliest = canonical_timestamp(
            interval.get("earliest_possible_at"), "censored interval earliest_possible_at",
        )
        latest = canonical_timestamp(
            interval.get("latest_possible_at"), "censored interval latest_possible_at",
        )
        if timestamp_key(latest) < timestamp_key(earliest):
            raise ValueError("censored event interval ends before it starts")
        if (
            timestamp_key(earliest) < timestamp_key(str(request["search_start_at"]))
            or timestamp_key(latest) > timestamp_key(str(request["search_end_at"]))
        ):
            raise ValueError("censored event interval crossed the frozen search window")
        refs = sorted({
            require_text(value, "censored interval source URL")
            for value in interval.get("source_urls") or ()
        })
        if not refs or not set(refs).issubset({row["url"] for row in sources}):
            raise ValueError("censored event interval must bind opened primary sources")
        censored_interval = {
            "earliest_possible_at": earliest,
            "latest_possible_at": latest,
            "source_urls": refs,
        }
    if interval_declared and (
        (classification == "interval_remains_censored") != bool(censored_interval)
    ):
        raise ValueError("censored-interval classification and evidence differ")
    full_coverage = bool(
        coverage.get("sec_filings_searched")
        and coverage.get("issuer_materials_searched")
    )
    if classification == "interval_remains_censored" and not full_coverage:
        raise ValueError("preserving an interval requires both primary-source classes")
    assessed = canonical_timestamp(raw.get("assessed_at"), "event refinement assessed_at")
    if timestamp_key(assessed) < timestamp_key(str(request["created_at"])):
        raise ValueError("event refinement assessment precedes its request")
    body = {
        "schema": STRATEGY_EVENT_REFINEMENT_RESULT_SCHEMA,
        "request_sha256": request_sha,
        "move_sha256": request["move_sha256"], "entity_id": request["entity_id"],
        "classification": classification, "assessed_at": assessed,
        "coverage": {
            "sec_filings_searched": bool(coverage.get("sec_filings_searched")),
            "issuer_materials_searched": bool(coverage.get("issuer_materials_searched")),
            "search_start_at": request["search_start_at"],
            "search_end_at": request["search_end_at"],
        },
        "exact_event": exact_event,
        "sources": sorted(sources, key=lambda row: row["url"]),
        "rationale": require_text(raw.get("rationale"), "event refinement rationale"),
        "residuals": [
            require_text(value, "event refinement residual")
            for value in raw.get("residuals") or ()
        ],
        "causal_timing_eligible": exact_event is not None,
        "authority": "subscription_agent_timing_evidence",
        "capital_authority": False,
    }
    if interval_declared:
        body["censored_interval"] = censored_interval
        body["interval_timing_eligible"] = censored_interval is not None
    result = {**body, "result_sha256": stable_sha256(body)}
    if raw.get("result_sha256") not in {None, result["result_sha256"]}:
        raise ValueError("strategy event refinement result content hash mismatch")
    return result


def due_strategy_event_refinement_requests(
    library: Mapping[str, Any], *, as_of: str,
    prior_requests: Iterable[Mapping[str, Any]] = (),
    results: Iterable[Mapping[str, Any]] = (), max_requests: int = 4,
) -> list[dict[str, Any]]:
    """Return a stable bounded queue of the highest-yield timing gaps."""
    if max_requests < 1:
        raise ValueError("strategy event refinement requires a positive request bound")
    now = timestamp_key(canonical_timestamp(as_of, "strategy event queue as_of"))
    requests_by_move: dict[str, list[dict[str, Any]]] = {}
    request_by_sha: dict[str, dict[str, Any]] = {}
    for row in prior_requests:
        if not isinstance(row, Mapping) or not row.get("request_sha256"):
            continue
        request = dict(row)
        move_sha = str(request.get("move_sha256") or "")
        requests_by_move.setdefault(move_sha, []).append(request)
        request_by_sha[str(request["request_sha256"])] = request
    result_by_request: dict[str, dict[str, Any]] = {}
    latest_result_by_move: dict[str, dict[str, Any]] = {}
    for row in results:
        if not isinstance(row, Mapping):
            continue
        request = request_by_sha.get(str(row.get("request_sha256") or ""))
        if request is None:
            continue
        result = compile_strategy_event_refinement_result(row, request)
        result_by_request[str(result["request_sha256"])] = result
        move_sha = str(result["move_sha256"])
        prior = latest_result_by_move.get(move_sha)
        if prior is None or (
            timestamp_key(str(result["assessed_at"])), str(result["result_sha256"])
        ) > (
            timestamp_key(str(prior["assessed_at"])), str(prior["result_sha256"])
        ):
            latest_result_by_move[move_sha] = result
    families = {
        str(row.get("mechanism_signature_sha256") or ""): row
        for row in library.get("move_families") or () if isinstance(row, Mapping)
    }
    current_epoch_by_entity: dict[str, str] = {}
    for row in library.get("moves") or ():
        if not isinstance(row, Mapping) or not row.get("entity_id"):
            continue
        entity = str(row["entity_id"])
        epoch = canonical_timestamp(row.get("evidence_epoch"), "strategy move evidence epoch")
        prior = current_epoch_by_entity.get(entity)
        if prior is None or timestamp_key(epoch) > timestamp_key(prior):
            current_epoch_by_entity[entity] = epoch
    candidates = []
    for move in library.get("moves") or ():
        if (
            not isinstance(move, Mapping) or move.get("claim_status") != "supported"
            or move.get("causal_panel_status") == "treatment_event_ready"
            or canonical_timestamp(
                move.get("evidence_epoch"), "strategy move evidence epoch",
            ) != current_epoch_by_entity.get(str(move.get("entity_id") or ""))
        ):
            continue
        move_sha = str(move.get("move_sha256") or "")
        latest_result = latest_result_by_move.get(move_sha)
        if latest_result:
            if latest_result["causal_timing_eligible"]:
                continue
            recheck_days = _REFINEMENT_RECHECK_DAYS[str(latest_result["classification"])]
            if now < timestamp_key(str(latest_result["assessed_at"])) + timedelta(days=recheck_days):
                continue
        family = families.get(str(move.get("mechanism_signature_sha256") or ""), {})
        outcome_contracts = tuple(
            row for row in move.get("outcome_contracts") or () if isinstance(row, Mapping)
        )
        priority = (
            1 if move.get("causal_panel_status") == "treatment_timing_interval_censored" else 0,
            1 if any(
                str(row.get("outcome_role") or "terminal_operating") == "terminal_operating"
                for row in outcome_contracts
            ) else 0,
            len(outcome_contracts),
            len(family.get("entity_ids") or ()), int(family.get("environment_count") or 0),
            int(move.get("frontier_bundle_count") or 0),
        )
        candidates.append((priority, dict(move)))
    candidates.sort(key=lambda row: (
        tuple(-value for value in row[0]), str(row[1].get("entity_id")),
        str(row[1].get("move_sha256")),
    ))
    diverse_candidates = []
    seen_entities = set()
    for candidate in candidates:
        entity_id = str(candidate[1].get("entity_id") or "")
        if entity_id in seen_entities:
            continue
        diverse_candidates.append(candidate)
        seen_entities.add(entity_id)
        if len(diverse_candidates) == max_requests:
            break
    if len(diverse_candidates) < max_requests:
        selected_moves = {
            str(candidate[1].get("move_sha256") or "")
            for candidate in diverse_candidates
        }
        diverse_candidates.extend(
            candidate for candidate in candidates
            if str(candidate[1].get("move_sha256") or "") not in selected_moves
        )
    requests = []
    for _, move in diverse_candidates[:max_requests]:
        move_requests = requests_by_move.get(str(move["move_sha256"]), [])
        open_requests = [
            row for row in move_requests
            if str(row["request_sha256"]) not in result_by_request
            and str(row.get("library_sha256") or "")
            == str(library.get("library_sha256") or "")
        ]
        request = max(
            open_requests,
            key=lambda row: (
                timestamp_key(str(row["search_end_at"])), str(row["request_sha256"]),
            ),
            default=None,
        ) or compile_strategy_event_refinement_request(
            move, library_sha256=str(library.get("library_sha256") or ""),
            search_end_at=as_of,
        )
        _checked(request, "request_sha256", "strategy event request")
        requests.append(request)
    return requests


def apply_strategy_event_refinements(
    moves: Iterable[dict[str, Any]], *, requests: Iterable[Mapping[str, Any]],
    results: Iterable[Mapping[str, Any]],
) -> int:
    """Attach separate timing receipts while preserving each move hash."""
    request_by_sha = {
        str(row.get("request_sha256") or ""): row for row in requests
        if isinstance(row, Mapping)
    }
    move_by_sha = {str(row.get("move_sha256") or ""): row for row in moves}
    latest: dict[str, dict[str, Any]] = {}
    for raw in results:
        request = request_by_sha.get(str(raw.get("request_sha256") or ""))
        if request is None:
            continue
        result = compile_strategy_event_refinement_result(raw, request)
        move_sha = str(result["move_sha256"])
        if move_sha not in move_by_sha:
            continue
        prior = latest.get(move_sha)
        if prior is None or (
            timestamp_key(str(result["assessed_at"])), str(result["result_sha256"])
        ) > (
            timestamp_key(str(prior["assessed_at"])), str(prior["result_sha256"])
        ):
            latest[move_sha] = result
    for move_sha, result in latest.items():
        move = move_by_sha[move_sha]
        move["timing_refinement"] = {
            "request_sha256": result["request_sha256"],
            "result_sha256": result["result_sha256"],
            "classification": result["classification"],
            "assessed_at": result["assessed_at"],
            "exact_event": result["exact_event"],
        }
        if "censored_interval" in result:
            move["timing_refinement"]["censored_interval"] = result["censored_interval"]
            move["timing_refinement"]["interval_timing_eligible"] = bool(
                result.get("interval_timing_eligible")
            )
        if result["causal_timing_eligible"]:
            move["causal_panel_status"] = "treatment_event_ready"
    return len(latest)


def compile_interval_treatment_period_frontier(
    move: Mapping[str, Any], *, fiscal_period_ends: Iterable[str],
) -> dict[str, Any] | None:
    """Map a source-bound event interval to every admissible annual treatment cohort."""
    refinement = move.get("timing_refinement")
    if not isinstance(refinement, Mapping):
        return None
    interval = refinement.get("censored_interval")
    if not isinstance(interval, Mapping):
        return None
    heads = sorted({
        timestamp_key(canonical_timestamp(value, "fiscal period end"))
        for value in fiscal_period_ends
    })
    if not heads:
        return None
    earliest = timestamp_key(str(interval["earliest_possible_at"]))
    latest = timestamp_key(str(interval["latest_possible_at"]))
    fiscal_month_day = max(value.strftime("%m-%d") for value in heads)

    def first_full_period(value: Any) -> int:
        partial = value.year + (value.strftime("%m-%d") > fiscal_month_day)
        return partial + 1

    lower = first_full_period(earliest)
    upper = first_full_period(latest)
    periods = list(range(min(lower, upper), max(lower, upper) + 1))
    body = {
        "schema": "jaggedthoughts-interval-treatment-period-frontier-v1",
        "entity_id": require_text(move.get("entity_id"), "interval move entity"),
        "move_sha256": require_text(move.get("move_sha256"), "interval move hash"),
        "timing_result_sha256": require_text(
            refinement.get("result_sha256"), "interval timing result hash",
        ),
        "earliest_possible_at": earliest.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "latest_possible_at": latest.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "fiscal_year_end_month_day": fiscal_month_day,
        "admissible_first_full_treatment_periods": periods,
        "coarse_period_identified": len(periods) == 1,
        "causal_effect_identified": False,
        "use_boundary": (
            "A singleton proves only that every date in the source-bound interval maps to "
            "the same annual treatment cohort. It does not establish parallel trends, "
            "causality, or an investment return."
        ),
    }
    return {**body, "frontier_sha256": stable_sha256(body)}


__all__ = [
    "STRATEGY_EVENT_REFINEMENT_REQUEST_SCHEMA",
    "STRATEGY_EVENT_REFINEMENT_RESULT_SCHEMA",
    "STRATEGY_EVENT_REFINEMENT_JOB_KIND",
    "apply_strategy_event_refinements",
    "compile_strategy_event_refinement_request",
    "compile_strategy_event_refinement_result",
    "compile_interval_treatment_period_frontier",
    "due_strategy_event_refinement_requests",
    "effective_exact_implementation_event",
]
