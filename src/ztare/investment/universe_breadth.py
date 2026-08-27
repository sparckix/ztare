"""Read-only breadth and selection-funnel audit for public-market research."""

from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from ztare.common.equivariance import stable_sha256


AUDIT_SCHEMA = "jaggedthoughts-universe-breadth-audit-v1"
_ELIGIBLE_SECURITY_KINDS = {"common_equity", "exchange_traded_fund"}
_CAP_BANDS = (
    ("below_micro", 0.0, 50_000_000.0),
    ("micro", 50_000_000.0, 300_000_000.0),
    ("small", 300_000_000.0, 2_000_000_000.0),
    ("mid", 2_000_000_000.0, 10_000_000_000.0),
    ("large", 10_000_000_000.0, 200_000_000_000.0),
    ("mega", 200_000_000_000.0, math.inf),
)


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def equity_size_band(market_cap: Any) -> str:
    """Return the catalog's coarse equity size band, preserving missing data."""
    value = _number(market_cap)
    if value is None or value < 0:
        return "unknown"
    return next(name for name, low, high in _CAP_BANDS if low <= value < high)


def _coordinate(row: Mapping[str, Any], dimension: str) -> str:
    if dimension == "size":
        return equity_size_band(row.get("market_cap")) if row.get("entity_kind") == "public_equity" else "unknown"
    if dimension == "style":
        # Intent labels and name fragments are not entity classifications.
        return _text(row.get("style")) or "unknown"
    return _text(row.get(dimension)) or "unknown"


def _distribution(rows: Iterable[Mapping[str, Any]], dimension: str) -> dict[str, Any]:
    values = [_coordinate(row, dimension) for row in rows]
    counts = Counter(values)
    known = len(values) - counts["unknown"]
    known_counts = {key: value for key, value in counts.items() if key != "unknown"}
    hhi = (
        sum((count / known) ** 2 for count in known_counts.values())
        if known else None
    )
    largest = sorted(known_counts, key=lambda key: (-known_counts[key], key))[0] if known_counts else None
    return {
        "counts": dict(sorted(counts.items())),
        "known_count": known,
        "unknown_count": counts["unknown"],
        "coverage_ratio": known / len(values) if values else 0.0,
        "known_hhi": hhi,
        "largest_known_category": largest,
        "largest_known_share": known_counts[largest] / known if largest else None,
    }


def _stage_profile(rows: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    materialized = list(rows)
    return {
        "count": len(materialized),
        "entity_kinds": dict(sorted(Counter(
            _text(row.get("entity_kind")) or "unknown" for row in materialized
        ).items())),
        "dimensions": {
            dimension: _distribution(materialized, dimension)
            for dimension in ("entity_kind", "size", "style", "sector", "industry")
        },
    }


def _source_rows(
    candidates: Iterable[Mapping[str, Any]],
    catalog_by_symbol: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in candidates:
        symbol = str(candidate.get("entity_id") or candidate.get("symbol") or "").upper()
        source = dict(catalog_by_symbol.get(symbol) or {})
        source["entity_kind"] = candidate.get("entity_kind") or source.get("entity_kind")
        source["entity_id"] = symbol
        rows.append(source)
    return rows


def _strict_threshold(value: float, operator: str, direction: int) -> float:
    """Move a threshold 10% toward (+1) or away from (-1) strictness."""
    delta = abs(value) * 0.1 if value else 0.01
    return value + direction * delta if operator in {"ge", "gt"} else value - direction * delta


def _passes(observed: float, operator: str, threshold: float) -> bool:
    return {
        "ge": observed >= threshold,
        "gt": observed > threshold,
        "le": observed <= threshold,
        "lt": observed < threshold,
    }[operator]


def _sensitivity(
    candidates: Iterable[Mapping[str, Any]],
    policy: Mapping[str, Any],
    entity_kind: str,
) -> dict[str, Any]:
    section = policy.get("equities" if entity_kind == "public_equity" else "funds") or {}
    configured = list(section.get("criteria") or ())
    minimum_score = _number(section.get("minimum_score"))
    rows = [row for row in candidates if row.get("entity_kind") == entity_kind]
    evaluable: list[tuple[Mapping[str, Any], float, dict[str, tuple[float, str, float]]]] = []
    for row in rows:
        score = _number(row.get("rank_score"))
        observations = {
            str(item.get("criterion_id")): (
                _number(item.get("observed")),
                str(item.get("operator") or ""),
                _number(item.get("threshold")),
            )
            for item in row.get("criteria") or ()
            if isinstance(item, Mapping)
        }
        needed: dict[str, tuple[float, str, float]] = {}
        for criterion in configured:
            criterion_id = str(criterion.get("id") or "")
            item = observations.get(criterion_id)
            if not item or None in item or item[1] not in {"ge", "gt", "le", "lt"}:
                break
            needed[criterion_id] = item  # type: ignore[assignment]
        else:
            if score is not None and minimum_score is not None:
                evaluable.append((row, score, needed))

    selected: dict[str, list[dict[str, Any]]] = {}
    for label, direction in (("relaxed_10pct", -1), ("base", 0), ("tightened_10pct", 1)):
        members = []
        score_floor = _strict_threshold(minimum_score or 0.0, "ge", direction)
        for row, score, observations in evaluable:
            if score < score_floor:
                continue
            if all(_passes(observed, operator, _strict_threshold(threshold, operator, direction))
                   for observed, operator, threshold in observations.values()):
                members.append({"entity_id": row.get("entity_id"), "rank": row.get("rank")})
        selected[label] = sorted(members, key=lambda item: (item["rank"] or math.inf, item["entity_id"]))

    source_ids = sorted(str(row.get("entity_id")) for row in rows if row.get("screen_status") == "qualified")
    base_ids = {str(row["entity_id"]) for row in selected["base"]}
    comparisons = {}
    for label in ("relaxed_10pct", "tightened_10pct"):
        alternative = {str(row["entity_id"]) for row in selected[label]}
        union = base_ids | alternative
        comparisons[label] = {
            "jaccard_to_base": len(base_ids & alternative) / len(union) if union else 1.0,
            "entrants": sorted(alternative - base_ids),
            "exits": sorted(base_ids - alternative),
        }
    return {
        "candidate_count": len(rows),
        "evaluable_count": len(evaluable),
        "unknown_coordinate_count": len(rows) - len(evaluable),
        "source_qualified_ids": source_ids,
        "base_matches_source": sorted(base_ids) == source_ids,
        "selected_at_existing_ranks": selected,
        "comparisons": comparisons,
        "perturbation": "minimum score and declared criterion thresholds moved 10% in strictness; ranks unchanged",
    }


def _count_by_kind(rows: Iterable[Mapping[str, Any]], kind: str) -> int:
    return sum(row.get("entity_kind") == kind for row in rows)


def _scout_rows(run: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Normalize the candidate collection carried by each supported scout schema."""
    source = run.get("candidates")
    inferred_kind = None
    if not isinstance(source, list):
        source = run.get("selected")
        inferred_kind = "public_fund"
    return [
        {
            **dict(row),
            "entity_kind": row.get("entity_kind") or inferred_kind,
            "entity_id": row.get("entity_id") or row.get("symbol"),
        }
        for row in source or () if isinstance(row, Mapping)
    ]


def _known_counts(values: Mapping[str, Any] | None) -> dict[str, int]:
    return {
        str(key): int(value)
        for key, value in (values or {}).items()
        if str(key) != "unknown" and int(value) > 0
    }


def _attrition(parent: int, child: int) -> dict[str, Any]:
    return {
        "parent_count": parent,
        "child_count": child,
        "attrited_count": max(parent - child, 0),
        "retention_ratio": child / parent if parent else None,
    }


def compile_universe_breadth_audit(
    *,
    catalog: Mapping[str, Any],
    discovery_policy: Mapping[str, Any],
    discovery_run: Mapping[str, Any],
    opportunity_book: Mapping[str, Any],
    scout_policy: Mapping[str, Any] | None = None,
    scout_cycle: Mapping[str, Any] | None = None,
    scout_runs: Iterable[Mapping[str, Any]] = (),
    enrichment_cycle: Mapping[str, Any] | None = None,
    watchlists: Iterable[Mapping[str, Any]] = (),
    drafts: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Compile breadth, attrition, concentration, and stability without mutation."""
    catalog_rows = [dict(row) for row in catalog.get("securities") or () if isinstance(row, Mapping)]
    eligible = [row for row in catalog_rows if row.get("security_kind") in _ELIGIBLE_SECURITY_KINDS]
    by_symbol = {str(row.get("symbol") or "").upper(): row for row in eligible}
    candidates = [dict(row) for row in discovery_run.get("candidates") or () if isinstance(row, Mapping)]
    book_rows = [dict(row) for row in opportunity_book.get("candidates") or () if isinstance(row, Mapping)]
    qualified = [row for row in candidates if row.get("screen_status") == "qualified"]
    ready = [row for row in book_rows if row.get("activation_class") in {"underwriting_ready", "fund_review_ready"}]
    enrichment_rows = [dict(row) for row in (enrichment_cycle or {}).get("candidates") or () if isinstance(row, Mapping)]
    watchlist_rows = [dict(row) for watchlist in watchlists for row in watchlist.get("candidates") or () if isinstance(row, Mapping)]
    watchlist_source_rows = _source_rows(watchlist_rows, by_symbol)
    draft_rows = [dict(row.get("entity") or {}) for row in drafts if isinstance(row.get("entity"), Mapping)]
    draft_ids = {str(row.get("id") or "").upper() for row in draft_rows}
    discovery_ids = {str(row.get("entity_id") or "").upper() for row in candidates}
    qualified_ids = {str(row.get("entity_id") or "").upper() for row in qualified}

    scout_results = list((scout_cycle or {}).get("results") or ())
    run_by_id = {run.get("run_id"): run for run in scout_runs}
    rows_by_id = {run_id: _scout_rows(run) for run_id, run in run_by_id.items()}
    run_rows = [row for rows in rows_by_id.values() for row in rows]
    scout_scope = []
    for result in scout_results:
        run = run_by_id.get(result.get("run_id"), {})
        mode = str(result.get("mode") or "language")
        intent = run.get("intent") or {}
        inferred_kinds = (
            ["public_equity"] if mode == "broad_equity"
            else ["public_fund"] if mode == "broad_fund"
            else list(intent.get("entity_kinds") or ())
        )
        if mode == "broad_equity":
            selected_profile = ((run.get("coverage") or {}).get("selected") or {})
            dimension_counts = {
                "size": _known_counts(selected_profile.get("size_counts")),
                "geography": _known_counts(selected_profile.get("country_counts")),
                "sector": _known_counts(selected_profile.get("sector_counts")),
            }
        elif mode == "broad_fund":
            selected_coverage = run.get("selected_coverage") or {}
            dimension_counts = {
                "size": _known_counts(selected_coverage.get("size")),
                "geography": _known_counts(selected_coverage.get("region")),
                "sector": {},
            }
        else:
            profile = _stage_profile(rows_by_id.get(result.get("run_id"), ()))
            dimension_counts = {
                "size": _known_counts((profile.get("dimensions") or {}).get("size", {}).get("counts")),
                "geography": {},
                "sector": _known_counts((profile.get("dimensions") or {}).get("sector", {}).get("counts")),
            }
        scout_scope.append({
            "intent_id": result.get("intent_id"),
            "mode": mode,
            "eligible_count": result.get("eligible_count"),
            "returned_count": result.get("returned_count"),
            "entity_kinds": inferred_kinds,
            "capitalization": intent.get("capitalization"),
            "styles": list(intent.get("styles") or ()),
            "selected_dimension_counts": dimension_counts,
        })
    active_mid_value = bool(scout_scope) and all(
        row["capitalization"] == "mid" and "value" in row["styles"] for row in scout_scope
    )
    active_modes = {row["mode"] for row in scout_scope}
    active_identity_kinds = sorted({
        kind for row in scout_scope for kind in row["entity_kinds"]
    })
    active_dimensions = {
        dimension: sorted({
            value for row in scout_scope
            for value in row["selected_dimension_counts"][dimension]
        })
        for dimension in ("size", "geography", "sector")
    }
    active_orthogonal = (
        {"broad_equity", "broad_fund"} <= active_modes
        and {"public_equity", "public_fund"} <= set(active_identity_kinds)
        and all(active_dimensions.values())
    )
    declared_modes = {
        str(row.get("mode") or "language")
        for row in (scout_policy or {}).get("intents") or ()
        if isinstance(row, Mapping) and bool(row.get("enabled", True))
    }
    declared_orthogonal = {"broad_equity", "broad_fund"} <= declared_modes
    full_catalog_deep = {
        discovery_policy.get("equities", {}).get("universe"),
        discovery_policy.get("funds", {}).get("universe"),
    } <= {"public_market_catalog", "catalog"}

    deep_profiles = {
        "discovery_candidates": _stage_profile(_source_rows(candidates, by_symbol)),
        "qualified": _stage_profile(_source_rows(qualified, by_symbol)),
        "opportunity_ready": _stage_profile(_source_rows(ready, by_symbol)),
        "watchlist_candidates": _stage_profile(watchlist_source_rows),
        "drafts": _stage_profile(_source_rows([
            {"entity_id": row.get("id"), "entity_kind": row.get("kind")} for row in draft_rows
        ], by_symbol)),
    }
    branches = {}
    for kind in ("public_equity", "public_fund"):
        counts = {
            "catalog_eligible": _count_by_kind(eligible, kind),
            "scout_eligible": sum(int(row.get("eligible_count") or 0) for row in scout_scope
                                  if kind in row.get("entity_kinds", [])),
            "scout_returned": _count_by_kind(run_rows, kind),
            "enrichment_candidates": _count_by_kind(enrichment_rows, kind),
            "enrichment_selected": sum(row.get("entity_kind") == kind and row.get("selection_status") == "selected"
                                       for row in enrichment_rows),
            "watchlist_candidates": _count_by_kind(watchlist_source_rows, kind),
            "discovery_candidates": _count_by_kind(candidates, kind),
            "ranked": sum(row.get("entity_kind") == kind and _number(row.get("rank")) is not None for row in candidates),
            "qualified": _count_by_kind(qualified, kind),
            "opportunity_ready": _count_by_kind(ready, kind),
            "drafts": sum(row.get("kind") == kind for row in draft_rows),
        }
        acquisition = ("catalog_eligible", "scout_eligible", "scout_returned",
                       "enrichment_candidates", "enrichment_selected")
        deep = (("watchlist_candidates", "discovery_candidates", "ranked", "qualified", "opportunity_ready")
                if kind == "public_fund" else
                ("discovery_candidates", "ranked", "qualified", "opportunity_ready"))
        branches[kind] = {
            **counts,
            "acquisition_attrition": {
                f"{parent}_to_{child}": _attrition(counts[parent], counts[child])
                for parent, child in zip(acquisition, acquisition[1:])
            },
            "deep_attrition": {
                f"{parent}_to_{child}": _attrition(counts[parent], counts[child])
                for parent, child in zip(deep, deep[1:])
            },
        }

    body = {
        "schema": AUDIT_SCHEMA,
        "authority": "read_only_research_audit",
        "source_universe": {
            "catalog_count": len(catalog_rows),
            "eligible_count": len(eligible),
            "excluded_other_listed_count": len(catalog_rows) - len(eligible),
            "profile": _stage_profile(eligible),
        },
        "active_scout_scope": scout_scope,
        "active_ingress_boundary": {
            "declared_periodic_modes": sorted(declared_modes),
            "declared_orthogonal_policy": declared_orthogonal,
            "latest_cycle_modes": sorted(active_modes),
            "latest_cycle_identity_kinds": active_identity_kinds,
            "latest_cycle_selected_dimensions": active_dimensions,
            "latest_cycle_is_orthogonal": active_orthogonal,
            "deep_screen_scope": (
                "complete_catalog" if full_catalog_deep else "cumulative_enrolled_population"
            ),
            "boundary": (
                "Periodic scouts create diverse research queues. Their coverage does not imply that "
                "every catalog identity reached fundamentals, valuation, underwriting, or allocation."
            ),
        },
        "funnel": {
            "branches": branches,
            "draft_lineage": {
                "draft_count": len(draft_rows),
                "current_discovery_intersection": len(draft_ids & discovery_ids),
                "current_qualified_intersection": len(draft_ids & qualified_ids),
            },
            "comparability": "Scout/enrichment is the latest acquisition branch; discovery/book is the cumulative enrolled branch.",
        },
        "stage_concentration": {
            "scout_returned": _stage_profile(run_rows),
            "enrichment_candidates": _stage_profile(enrichment_rows),
            **deep_profiles,
        },
        "threshold_sensitivity": {
            kind: _sensitivity(candidates, discovery_policy, kind)
            for kind in ("public_equity", "public_fund")
        },
        "breadth_verdict": {
            "source_catalog_is_broad": len({row.get("entity_kind") for row in eligible}) > 1,
            "active_ingress_is_mid_cap_value_only": active_mid_value,
            "declared_orthogonal_periodic_policy": declared_orthogonal,
            "latest_cycle_is_orthogonal": active_orthogonal,
            "full_catalog_reaches_deep_screen": full_catalog_deep,
            "deep_screen_fraction_of_eligible_catalog": len(candidates) / len(eligible) if eligible else 0.0,
            "verdict": (
                "broad_catalog_narrow_mid_value_ingress"
                if active_mid_value and not full_catalog_deep else
                "broad_catalog_broad_deep_scan"
                if full_catalog_deep else
                "broad_catalog_orthogonal_periodic_ingress_bounded_deep_screen"
                if active_orthogonal else "bounded_non_mid_value_ingress"
            ),
        },
        "classification_boundary": (
            "Size derives only from sourced equity market cap. Style, sector, and industry are unknown when absent; "
            "fund names and research-intent labels are not promoted to entity classifications."
        ),
    }
    return {**body, "audit_sha256": stable_sha256(body)}


def audit_workspace_breadth(workspace: str | Path) -> dict[str, Any]:
    """Read the latest workspace artifacts and print/return no changed state."""
    root = Path(workspace).expanduser().resolve()

    def read_json(relative: str) -> dict[str, Any]:
        return json.loads((root / relative).read_text(encoding="utf-8"))

    scout_cycle = read_json("research_jobs/scheduled/latest.json")
    scout_runs = [read_json(str(result["run_path"])) for result in scout_cycle.get("results") or ()]
    drafts = [yaml.safe_load(path.read_text(encoding="utf-8")) for path in sorted((root / "profiles/drafts").glob("*.yaml"))]
    watchlists = [json.loads(path.read_text(encoding="utf-8")) for path in sorted((root / "watchlists/results").glob("*.json"))]
    return compile_universe_breadth_audit(
        catalog=read_json("universe/catalog-latest.json"),
        discovery_policy=yaml.safe_load((root / "discovery.yaml").read_text(encoding="utf-8")),
        discovery_run=read_json("discovery/latest.json"),
        opportunity_book=read_json("opportunity_books/latest.json"),
        scout_policy=yaml.safe_load((root / "research_jobs/intents.yaml").read_text(encoding="utf-8")),
        scout_cycle=scout_cycle,
        scout_runs=scout_runs,
        enrichment_cycle=read_json("research_jobs/enrichment/latest.json"),
        watchlists=watchlists,
        drafts=drafts,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace")
    print(json.dumps(audit_workspace_breadth(parser.parse_args().workspace), indent=2, sort_keys=True))
