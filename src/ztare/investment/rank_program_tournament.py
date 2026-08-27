"""Prospective paired evaluation of fixed opportunity-ranking programs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

from ztare.common.equivariance import stable_sha256
from ztare.worldmodel.evaluation import (
    EvaluationScore,
    compile_evaluation_integrity_receipt,
    conservative_paired_survivor_set,
)

from .closed_book import overlap_cluster_ids
from .contracts import canonical_timestamp, require_refs, require_text, timestamp_key
from .golden_store import GoldenEdge, GoldenLeaf, GoldenStore
from .portfolio_policy import _price_series, _score_ranking_ticket
from .prospective_return_window import (
    bind_prospective_return_window,
    compile_prospective_return_window,
    settle_prospective_return_window,
)


RANK_PROGRAM_INPUT_SCHEMA = "jaggedthoughts-rank-program-input-v1"
RANK_PROGRAM_RUN_SCHEMA = "jaggedthoughts-rank-program-tournament-run-v1"
RANK_PROGRAM_SETTLEMENT_SCHEMA = "jaggedthoughts-rank-program-tournament-settlement-v1"
RANK_PROGRAM_STATUS_SCHEMA = "jaggedthoughts-rank-program-tournament-status-v1"
MINIMUM_INFERENCE_BLOCKS = 8
PRIMARY_HORIZON_DAYS = 365
DIAGNOSTIC_HORIZON_DAYS = 30
_PROGRAM_IDS_BY_KIND = {
    "public_equity": (
        "coordinate_equal_v4", "family_weighted_v5",
        "quality_expectations_balanced_v1", "quality_only_v1", "expectations_only_v1",
    ),
    "public_fund": (
        "coordinate_equal_v5", "family_weighted_v6", "factor_return_after_fee_v1",
    ),
}
_ADMISSION_CHECKS = ("component_contract_complete", "evidence_contract_pass")
_OBSERVED_LABELS = ("screen_thresholds_pass",)
_COMPONENTS = {
    "public_equity": (
        "durable_earnings_power",
        "price_implied_excess_return",
        "earnings_power_margin",
        "low_implied_growth",
    ),
    "public_fund": (
        "earnings_yield",
        "book_to_price",
        "factor_return_after_fee",
        "factor_return_per_volatility",
        "drawdown_resilience",
        "fee_efficiency",
    ),
}
_WEIGHTS = {
    "coordinate_equal_v4": {
        "public_equity": (0.25,) * 4,
    },
    "coordinate_equal_v5": {
        "public_fund": (0.2, 0.2, 0.0, 0.2, 0.2, 0.2),
    },
    "family_weighted_v5": {
        "public_equity": (0.45, 0.55 / 3, 0.55 / 3, 0.55 / 3),
    },
    "family_weighted_v6": {
        "public_fund": (0.25, 0.25, 0.0, 0.20, 0.20, 0.10),
    },
    "factor_return_after_fee_v1": {
        "public_fund": (0.0, 0.0, 1.0, 0.0, 0.0, 0.0),
    },
    "quality_expectations_balanced_v1": {
        "public_equity": (0.50, 1 / 6, 1 / 6, 1 / 6),
    },
    "quality_only_v1": {
        "public_equity": (1.0, 0.0, 0.0, 0.0),
    },
    "expectations_only_v1": {
        "public_equity": (0.0, 1 / 3, 1 / 3, 1 / 3),
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    return value if isinstance(value, dict) else None


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(dict(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _supersession_path(base: Path, run_id: str) -> Path:
    return base / "supersessions" / f"{run_id}.json"


def _signed(payload: Mapping[str, Any], field: str, schema: str) -> dict[str, Any]:
    body = dict(payload)
    digest = str(body.pop(field, ""))
    if body.get("schema") != schema or not digest or stable_sha256(body) != digest:
        raise ValueError(f"invalid {schema} identity")
    return body


def rank_program_definitions() -> list[dict[str, Any]]:
    """Return fixed, outcome-blind comparator identities."""

    rows = []
    for program_id in _WEIGHTS:
        body = {
            "program_id": program_id,
            "generation_process": "deterministic",
            "component_weights": {
                kind: dict(zip(_COMPONENTS[kind], weights))
                for kind, weights in _WEIGHTS[program_id].items()
            },
            "score_semantics": "ordinal_research_hypothesis",
            "expected_return_claim": False,
        }
        rows.append({**body, "program_sha256": stable_sha256(body)})
    return rows


def _score(entity_kind: str, program_id: str, components: Mapping[str, Any]) -> float:
    names = _COMPONENTS[entity_kind]
    if entity_kind not in _WEIGHTS[program_id]:
        raise ValueError(f"rank program {program_id} does not apply to {entity_kind}")
    values = tuple(float(components[name]) for name in names)
    if any(not math.isfinite(value) or not 0 <= value <= 1 for value in values):
        raise ValueError("rank-program components must be finite values in [0,1]")
    return sum(weight * value for weight, value in zip(_WEIGHTS[program_id][entity_kind], values))


def compile_rank_program_input(
    *,
    discovery_run_id: str,
    as_of: str,
    compiler_version: str,
    eligibility_policy_id: str,
    lanes: Iterable[Mapping[str, Any]],
    enumerated_candidate_count: int,
    source_refs: Iterable[str],
) -> dict[str, Any]:
    """Compile the full pre-truncation, score-independent comparison population."""

    normalized_lanes = []
    seen_candidates: set[str] = set()
    for raw_lane in lanes:
        lane_id = require_text(raw_lane.get("lane_id"), "rank lane_id")
        entity_kind = require_text(raw_lane.get("entity_kind"), "rank lane entity_kind")
        if entity_kind not in _COMPONENTS:
            raise ValueError("rank lane entity_kind must be public_equity or public_fund")
        if (entity_kind == "public_equity") != (lane_id == "public_equity"):
            raise ValueError("equities require the public_equity lane")
        if entity_kind == "public_fund" and not lane_id.startswith("public_fund:"):
            raise ValueError("fund lanes must name their implementation sleeve")
        benchmark_id = require_text(raw_lane.get("benchmark_id"), "rank lane benchmark_id").upper()
        candidates = []
        for raw in raw_lane.get("candidates") or ():
            candidate_id = require_text(raw.get("candidate_id"), "rank candidate_id")
            if candidate_id in seen_candidates:
                raise ValueError(f"duplicate rank candidate_id: {candidate_id}")
            seen_candidates.add(candidate_id)
            eligible = raw.get("rank_program_eligible")
            if not isinstance(eligible, bool):
                raise ValueError("every rank candidate needs an explicit rank_program_eligible boolean")
            components = {
                str(key): float(value)
                for key, value in (raw.get("components") or {}).items()
            }
            if eligible:
                if set(components) != set(_COMPONENTS[entity_kind]):
                    raise ValueError(f"eligible {entity_kind} candidate has incomplete rank components")
                for program_id in _PROGRAM_IDS_BY_KIND[entity_kind]:
                    _score(entity_kind, program_id, components)
            raw_checks = raw.get("eligibility_checks") or {}
            if not isinstance(raw_checks, Mapping) or any(
                not isinstance(value, bool) for value in raw_checks.values()
            ):
                raise ValueError("rank eligibility_checks must contain only booleans")
            if not set((*_ADMISSION_CHECKS, *_OBSERVED_LABELS)).issubset(raw_checks):
                raise ValueError("rank eligibility is missing a score-independent admission check")
            if eligible != all(raw_checks[name] for name in _ADMISSION_CHECKS):
                raise ValueError("rank eligibility must equal the score-independent admission checks")
            candidate_body = {
                "candidate_id": candidate_id,
                "entity_id": require_text(raw.get("entity_id"), "rank entity_id").upper(),
                "rank_program_eligible": eligible,
                "eligibility_checks": dict(sorted(
                    (str(key), value) for key, value in raw_checks.items()
                )),
                "components": dict(sorted(components.items())),
                "source_refs": list(require_refs(raw.get("source_refs") or (), "rank candidate source ref")),
            }
            candidate_sha = require_text(raw.get("candidate_sha256"), "candidate_sha256")
            if candidate_sha != stable_sha256(candidate_body):
                raise ValueError("rank candidate_sha256 does not bind its candidate bytes")
            candidates.append({**candidate_body, "candidate_sha256": candidate_sha})
        if len({row["entity_id"] for row in candidates}) != len(candidates):
            raise ValueError(f"rank lane {lane_id} contains duplicate entities")
        if benchmark_id in {row["entity_id"] for row in candidates}:
            raise ValueError("rank lane benchmark cannot also be a candidate")
        normalized_lanes.append({
            "lane_id": lane_id,
            "entity_kind": entity_kind,
            "benchmark_id": benchmark_id,
            "candidates": sorted(candidates, key=lambda row: row["candidate_id"]),
        })
    if not normalized_lanes or len(seen_candidates) != int(enumerated_candidate_count):
        raise ValueError("rank-program input must contain the full enumerated pre-truncation population")
    body = {
        "schema": RANK_PROGRAM_INPUT_SCHEMA,
        "discovery_run_id": require_text(discovery_run_id, "discovery_run_id"),
        "as_of": canonical_timestamp(as_of, "rank-program input as_of"),
        "compiler_version": require_text(compiler_version, "discovery compiler_version"),
        "pre_truncation": True,
        "enumerated_candidate_count": int(enumerated_candidate_count),
        "eligibility_policy": {
            "policy_id": require_text(eligibility_policy_id, "eligibility_policy_id"),
            "score_independent": True,
            "admission_checks": list(_ADMISSION_CHECKS),
            "observed_non_admission_labels": list(_OBSERVED_LABELS),
            "forbidden_inputs": ["rank", "rank_score", "potential_rank", "screen_status"],
        },
        "lanes": sorted(normalized_lanes, key=lambda row: row["lane_id"]),
        "source_refs": list(require_refs(source_refs, "rank-program input source ref")),
        "capital_authority": False,
    }
    return {**body, "rank_program_input_sha256": stable_sha256(body)}


def _embedded_input(discovery_run: Mapping[str, Any]) -> dict[str, Any]:
    run = _signed(discovery_run, "run_sha256", "jaggedthoughts-discovery-run-v1")
    value = discovery_run.get("rank_program_input")
    if not isinstance(value, Mapping):
        raise ValueError("discovery run lacks embedded rank_program_input")
    payload = dict(value)
    body = _signed(payload, "rank_program_input_sha256", RANK_PROGRAM_INPUT_SCHEMA)
    if (
        body["pre_truncation"] is not True
        or body["discovery_run_id"] != run.get("run_id")
        or body["as_of"] != run.get("as_of")
        or body["compiler_version"] != run.get("compiler_version")
        or (body.get("eligibility_policy") or {}).get("score_independent") is not True
        or body.get("enumerated_candidate_count")
        != (run.get("enumeration") or {}).get("enumerated_count")
    ):
        raise ValueError("embedded rank-program input differs from its discovery run")
    rebuilt = compile_rank_program_input(
        discovery_run_id=str(body["discovery_run_id"]),
        as_of=str(body["as_of"]),
        compiler_version=str(body["compiler_version"]),
        eligibility_policy_id=str(body["eligibility_policy"]["policy_id"]),
        lanes=body["lanes"],
        enumerated_candidate_count=int(body["enumerated_candidate_count"]),
        source_refs=body["source_refs"],
    )
    if rebuilt["rank_program_input_sha256"] != payload["rank_program_input_sha256"]:
        raise ValueError("embedded rank-program input fails canonical recompilation")
    return payload


def _ticket(
    *, lane: Mapping[str, Any], program: Mapping[str, Any], candidates: list[dict[str, Any]],
    source_cutoff: str, sealed_at: str, end_at: str, input_sha256: str,
) -> dict[str, Any]:
    ranked = sorted(
        ({
            "entity_id": row["entity_id"],
            "entity_kind": lane["entity_kind"],
            "candidate_sha256": row["candidate_sha256"],
            "score": _score(str(lane["entity_kind"]), str(program["program_id"]), row["components"]),
            "source_refs": row["source_refs"],
            "mechanism_refs": [str(program["program_sha256"])],
        } for row in candidates),
        key=lambda row: (-row["score"], row["entity_id"]),
    )
    ranked = [{**row, "rank": index} for index, row in enumerate(ranked, 1)]
    body = {
        "schema": "jaggedthoughts-opportunity-ranking-ticket-v1",
        "claim_id": f"rank_program::{lane['lane_id']}::{program['program_id']}",
        "program_id": program["program_id"],
        "program_sha256": program["program_sha256"],
        "lane_id": lane["lane_id"],
        "source_cutoff": source_cutoff,
        "outcome_window": {"earliest_start_at": sealed_at, "nominal_end_at": end_at},
        "benchmark_id": lane["benchmark_id"],
        "ranked_candidates": ranked,
        "score_semantics": "research_priority_not_expected_return",
        "source_refs": [f"rank-program-input:{input_sha256}"],
        "settlement_contract": {
            "outcome": "benchmark_relative_adjusted_close_return_net_of_cost",
            "calibration": "mean_absolute_rank_percentile_error",
            "regret": "top_1_active_return_regret",
        },
        "status": "unresolved",
        "candidate_set_sha256": stable_sha256(sorted(row["candidate_sha256"] for row in ranked)),
        "authority": "prospective_shadow",
        "capital_authority": False,
    }
    return {**body, "ticket_id": stable_sha256(body), "ticket_sha256": stable_sha256(body)}


def open_rank_program_tournament(
    root: Path,
    *,
    owner: str,
    store_path: Path,
    discovery_run: Mapping[str, Any],
    horizon_days: int = PRIMARY_HORIZON_DAYS,
    opened_at: str | None = None,
    sealed_at: str | None = None,
    transaction_cost_bps: float = 10.0,
) -> dict[str, Any]:
    """Freeze every applicable program on identical lane populations before outcomes begin."""

    if not 7 <= int(horizon_days) <= 730:
        raise ValueError("rank-program horizon_days must be in [7,730]")
    rank_input = _embedded_input(discovery_run)
    eligibility_policy_id = str(rank_input["eligibility_policy"]["policy_id"])
    opened = canonical_timestamp(opened_at or _utc_now(), "rank-program opened_at")
    sealed = canonical_timestamp(sealed_at or _utc_now(), "rank-program sealed_at")
    completed = canonical_timestamp(
        discovery_run.get("completed_at"), "discovery completed_at",
    )
    if not (
        timestamp_key(rank_input["as_of"])
        <= timestamp_key(completed)
        <= timestamp_key(opened)
        <= timestamp_key(sealed)
    ):
        raise ValueError(
            "rank-program chronology must be input as_of <= discovery completion "
            "<= opened_at <= sealed_at"
        )
    base = root / "rank_program_tournament"
    price_scope = {
        str(lane["benchmark_id"]).upper()
        for lane in rank_input["lanes"]
    } | {
        str(row["entity_id"]).upper()
        for lane in rank_input["lanes"] for row in lane["candidates"]
        if row["rank_program_eligible"]
    }
    prices = _price_series(root, opened, price_scope)
    programs = rank_program_definitions()
    program_family_sha256 = stable_sha256([
        row["program_sha256"] for row in programs
    ])
    end_at = (
        datetime.fromisoformat(sealed.replace("Z", "+00:00")) + timedelta(days=int(horizon_days))
    ).isoformat(timespec="seconds").replace("+00:00", "Z")
    lanes, deferred_lanes = [], []
    for lane in rank_input["lanes"]:
        benchmark = str(lane["benchmark_id"])
        eligible = [row for row in lane["candidates"] if row["rank_program_eligible"]]
        if len(eligible) < 2:
            deferred_lanes.append({
                "lane_id": lane["lane_id"], "entity_kind": lane["entity_kind"],
                "benchmark_id": benchmark, "input_candidate_count": len(lane["candidates"]),
                "eligible_candidate_count": len(eligible),
                "reason": "fewer_than_two_score_independent_eligible_candidates",
            })
            continue
        if not prices.get(benchmark):
            deferred_lanes.append({
                "lane_id": lane["lane_id"], "entity_kind": lane["entity_kind"],
                "benchmark_id": benchmark, "input_candidate_count": len(lane["candidates"]),
                "eligible_candidate_count": len(eligible),
                "reason": "benchmark_price_history_unavailable_at_freeze",
            })
            continue
        excluded = [
            {"candidate_id": row["candidate_id"], "reason": "price_history_unavailable_at_freeze"}
            for row in eligible if not prices.get(str(row["entity_id"]))
        ]
        candidates = [row for row in eligible if prices.get(str(row["entity_id"]))]
        if len(candidates) < 2:
            deferred_lanes.append({
                "lane_id": lane["lane_id"], "entity_kind": lane["entity_kind"],
                "benchmark_id": benchmark, "input_candidate_count": len(lane["candidates"]),
                "eligible_candidate_count": len(eligible),
                "priced_candidate_count": len(candidates), "excluded": excluded,
                "reason": "fewer_than_two_priced_eligible_candidates",
            })
            continue
        lane_programs = [
            program for program in programs
            if str(lane["entity_kind"]) in program["component_weights"]
        ]
        tickets = [
            _ticket(
                lane=lane, program=program, candidates=candidates,
                source_cutoff=str(rank_input["as_of"]), sealed_at=sealed, end_at=end_at,
                input_sha256=str(rank_input["rank_program_input_sha256"]),
            )
            for program in lane_programs
        ]
        if len({row["candidate_set_sha256"] for row in tickets}) != 1:
            raise ValueError("rank programs do not share the same lane candidate set")
        lanes.append({
            "lane_id": lane["lane_id"], "entity_kind": lane["entity_kind"],
            "benchmark_id": benchmark, "candidate_count": len(candidates),
            "candidate_set_sha256": tickets[0]["candidate_set_sha256"],
            "excluded": excluded, "ranking_tickets": tickets,
            "prospective_return_window": compile_prospective_return_window(
                sealed_at=sealed, horizon_days=int(horizon_days),
                entity_ids=(benchmark, *(row["entity_id"] for row in candidates)),
                transaction_cost_bps=float(transaction_cost_bps),
            ),
        })
    if not lanes:
        raise ValueError("rank-program tournament has no comparable lane with two priced candidates")
    run_identity = {
        "input_sha256": rank_input["rank_program_input_sha256"],
        "sealed_at": sealed, "horizon_days": int(horizon_days),
        "program_sha256s": [row["program_sha256"] for row in programs],
    }
    run_id = f"rank-program-{stable_sha256(run_identity)[:20]}"
    new_lane_sets = {
        str(lane["lane_id"]): set(lane["prospective_return_window"]["entity_ids"])
        - {str(lane["benchmark_id"])}
        for lane in lanes
    }
    superseded_priors: list[tuple[dict[str, Any], str]] = []
    for path in sorted((base / "runs").glob("*.json")):
        prior = _read(path)
        if (
            not prior or prior.get("schema") != RANK_PROGRAM_RUN_SCHEMA
            or int(prior.get("horizon_days") or 0) != int(horizon_days)
            or (base / "settlements" / f"{prior['run_id']}.json").is_file()
            or _supersession_path(base, str(prior["run_id"])).is_file()
        ):
            continue
        if prior.get("run_id") == run_id:
            return {**prior, "ok": True, "replayed": True, "activation_status": "blocked_overlap"}
        bound = any(
            ((_read(binding_path) or {}).get("binding") or {}).get("status") == "bound"
            for binding_path in (base / "return_windows").glob(f"{prior['run_id']}-*.json")
        )
        prior_lane_sets = {
            str(lane["lane_id"]): set(lane["prospective_return_window"]["entity_ids"])
            - {str(lane["benchmark_id"])}
            for lane in prior.get("lanes") or ()
        }
        expands = (
            all(values <= new_lane_sets.get(lane_id, set()) for lane_id, values in prior_lane_sets.items())
            and any(new_lane_sets.get(lane_id, set()) != values for lane_id, values in prior_lane_sets.items())
            or any(lane_id not in prior_lane_sets for lane_id in new_lane_sets)
        )
        policy_changed = prior.get("eligibility_policy_id") != eligibility_policy_id
        program_family_changed = (
            prior.get("program_family_sha256") != program_family_sha256
        )
        if bound and program_family_changed:
            # A separately sealed family may coexist with an older bound family.
            # Their overlapping outcome windows later collapse into one inference block.
            continue
        if bound or not (expands or policy_changed or program_family_changed):
            return {**prior, "ok": True, "replayed": True, "activation_status": "blocked_overlap"}
        superseded_priors.append((
            prior,
            (
                "eligibility_policy_change_before_entry_binding"
                if policy_changed else
                "program_family_change_before_entry_binding"
                if program_family_changed else
                "strict_candidate_coverage_expansion_before_entry_binding"
            ),
        ))
    body = {
        "schema": RANK_PROGRAM_RUN_SCHEMA,
        "run_id": run_id, "status": "pending_outcome",
        "opened_at": opened, "sealed_at": sealed, "end_at": end_at,
        "horizon_days": int(horizon_days),
        "estimand_role": (
            "primary_patient_capital_rank_evidence"
            if int(horizon_days) == PRIMARY_HORIZON_DAYS else "diagnostic_only"
        ),
        "discovery_run_id": discovery_run["run_id"],
        "discovery_run_sha256": discovery_run["run_sha256"],
        "rank_program_input_sha256": rank_input["rank_program_input_sha256"],
        "eligibility_policy_id": eligibility_policy_id,
        "program_family_sha256": program_family_sha256,
        "programs": programs, "lanes": lanes, "deferred_lanes": deferred_lanes,
        "evaluation_integrity": compile_evaluation_integrity_receipt(
            temporal_design="prospective_sealed", generation_processes=("deterministic",),
            seal_rows=tuple({
                "episode_id": f"{run_id}:{lane['lane_id']}:{program['program_id']}",
                "sealed_at": sealed, "episode_start_at": sealed,
            } for lane in lanes for program in lane["ranking_tickets"]),
        ),
        "minimum_inference_blocks": MINIMUM_INFERENCE_BLOCKS,
        "automatic_policy_change": False,
        "portfolio_mutation_authority": False,
        "capital_authority": False,
    }
    run = {**body, "run_sha256": stable_sha256(body)}
    path = base / "runs" / f"{run_id}.json"
    _write(path, run)
    leaf = GoldenLeaf(
        owner=owner, object_kind="rank_program_tournament_run", object_id=run_id,
        epoch=run["run_sha256"], occurred_at=opened, available_at=sealed, payload=run,
        source_refs=(
            f"discovery-run:{discovery_run['run_sha256']}",
            f"rank-input:{rank_input['rank_program_input_sha256']}",
        ),
    )
    GoldenStore(store_path).append_leaf(leaf)
    for prior, reason in superseded_priors:
        supersession_body = {
            "schema": "jaggedthoughts-rank-program-tournament-supersession-v1",
            "prior_run_id": prior["run_id"],
            "prior_run_sha256": prior["run_sha256"],
            "successor_run_id": run_id,
            "successor_run_sha256": run["run_sha256"],
            "recorded_at": sealed,
            "reason": reason,
            "capital_authority": False,
        }
        supersession = {
            **supersession_body,
            "supersession_sha256": stable_sha256(supersession_body),
        }
        _write(_supersession_path(base, str(prior["run_id"])), supersession)
        GoldenStore(store_path).append_leaf(GoldenLeaf(
            owner=owner, object_kind="rank_program_tournament_supersession",
            object_id=str(prior["run_id"]), epoch=supersession["supersession_sha256"],
            occurred_at=sealed, available_at=sealed, payload=supersession,
            source_refs=(
                f"rank-program-run:{prior['run_sha256']}",
                f"rank-program-run:{run['run_sha256']}",
            ),
        ))
    return {
        **run, "ok": True, "replayed": False,
        "run_path": path.relative_to(root).as_posix(),
        "golden_leaf_sha256": leaf.leaf_sha256,
    }


def _binding_path(root: Path, run_id: str, lane_id: str) -> Path:
    return root / "rank_program_tournament" / "return_windows" / f"{run_id}-{stable_sha256(lane_id)[:12]}.json"


def rank_program_price_refresh_entity_ids(
    root: Path, *, as_of: str | None = None,
) -> list[str]:
    """Return entities whose next entry or due exit observation can advance a run."""
    evaluated = canonical_timestamp(
        as_of or _utc_now(), "rank-program price refresh as_of",
    )
    base = root / "rank_program_tournament"
    superseded = {
        str(row.get("prior_run_id") or "")
        for path in (base / "supersessions").glob("*.json")
        if (row := _read(path))
    }
    settled = {
        str(row.get("run_id") or "")
        for path in (base / "settlements").glob("*.json")
        if (row := _read(path))
    }
    entity_ids: set[str] = set()
    for path in sorted((base / "runs").glob("*.json")):
        run = _read(path)
        if not run or str(run.get("run_id") or "") in superseded | settled:
            continue
        _signed(run, "run_sha256", RANK_PROGRAM_RUN_SCHEMA)
        for lane in run.get("lanes") or ():
            envelope = _read(_binding_path(
                root, str(run["run_id"]), str(lane["lane_id"]),
            )) or {}
            if isinstance(envelope.get("settlement"), Mapping):
                continue
            binding = envelope.get("binding")
            if (
                isinstance(binding, Mapping)
                and binding.get("status") == "bound"
                and timestamp_key(evaluated) < timestamp_key(str(binding["scheduled_exit_at"]))
            ):
                continue
            contract = lane["prospective_return_window"]
            entity_ids.update(str(value).upper() for value in contract["entity_ids"])
    return sorted(entity_ids)


def settle_rank_program_tournaments(
    root: Path, *, owner: str, store_path: Path, as_of: str | None = None,
) -> dict[str, Any]:
    """Settle every fully matured paired rank-program run without changing policy."""

    evaluated = canonical_timestamp(as_of or _utc_now(), "rank-program settlement as_of")
    base = root / "rank_program_tournament"
    prices = _price_series(
        root, evaluated,
        rank_program_price_refresh_entity_ids(root, as_of=evaluated),
    )
    settled, pending = [], []
    for path in sorted((base / "runs").glob("*.json")):
        run = _read(path)
        if not run:
            continue
        if _supersession_path(base, str(run.get("run_id") or "")).is_file():
            continue
        _signed(run, "run_sha256", RANK_PROGRAM_RUN_SCHEMA)
        settlement_path = base / "settlements" / f"{run['run_id']}.json"
        prior = _read(settlement_path)
        if prior:
            _signed(prior, "settlement_sha256", RANK_PROGRAM_SETTLEMENT_SCHEMA)
            settled.append(prior)
            continue
        lane_results, blockers = [], []
        for lane in run["lanes"]:
            contract = lane["prospective_return_window"]
            points = {entity_id: prices.get(str(entity_id), ()) for entity_id in contract["entity_ids"]}
            binding_path = _binding_path(root, str(run["run_id"]), str(lane["lane_id"]))
            envelope = _read(binding_path) or {}
            binding = envelope.get("binding")
            if not isinstance(binding, Mapping):
                binding = bind_prospective_return_window(contract, points=points, as_of=evaluated)
                if binding["status"] == "bound":
                    _write(binding_path, {"contract": contract, "binding": binding})
            if binding["status"] != "bound":
                blockers.append({"lane_id": lane["lane_id"], "reason": "entry_price_unavailable"})
                continue
            window = envelope.get("settlement")
            if not isinstance(window, Mapping):
                window = settle_prospective_return_window(
                    contract, binding, points=points, as_of=evaluated,
                )
                if window["status"] == "settled":
                    _write(binding_path, {
                        "contract": contract, "binding": binding, "settlement": window,
                    })
            if window["status"] != "settled":
                blockers.append({
                    "lane_id": lane["lane_id"], "reason": window["status"],
                    "missing_entity_ids": list(window.get("missing_entity_ids") or ()),
                })
                continue
            benchmark_return = float(window["returns"][lane["benchmark_id"]])
            returns = {
                entity_id: float(value) for entity_id, value in window["returns"].items()
                if entity_id != lane["benchmark_id"]
            }
            scores = [{
                "program_id": ticket["program_id"],
                "score": _score_ranking_ticket(ticket, returns, benchmark_return),
            } for ticket in lane["ranking_tickets"]]
            lane_results.append({
                "lane_id": lane["lane_id"], "entity_kind": lane["entity_kind"],
                "benchmark_id": lane["benchmark_id"],
                "candidate_set_sha256": lane["candidate_set_sha256"],
                "return_window_binding": dict(binding),
                "return_window_settlement": window,
                "actual_returns": returns, "benchmark_return": benchmark_return,
                "ranking_scores": scores,
            })
        if blockers:
            pending.append({"run_id": run["run_id"], "blockers": blockers})
            continue
        maturity_rows = tuple({
            "episode_id": f"{run['run_id']}:{lane['lane_id']}",
            "episode_end_at": lane["return_window_settlement"]["exit_observed_at"],
            "outcome_available_at": max(
                point["available_at"] for point in lane["return_window_settlement"]["exit_points"].values()
            ),
            "evaluated_at": evaluated,
        } for lane in lane_results)
        body = {
            "schema": RANK_PROGRAM_SETTLEMENT_SCHEMA,
            "settlement_id": f"{run['run_id']}::settlement",
            "run_id": run["run_id"], "run_sha256": run["run_sha256"],
            "program_family_sha256": run.get("program_family_sha256", "legacy-two-program-family"),
            "horizon_days": int(run["horizon_days"]),
            "estimand_role": run.get("estimand_role"),
            "evaluated_at": evaluated, "lane_results": lane_results,
            "evaluation_integrity": compile_evaluation_integrity_receipt(
                temporal_design="prospective_sealed", generation_processes=("deterministic",),
                seal_rows=tuple({
                    "episode_id": f"{run['run_id']}:{lane['lane_id']}:{program['program_id']}",
                    "sealed_at": run["sealed_at"],
                    "episode_start_at": lane["return_window_binding"]["entry_observed_at"],
                } for lane in lane_results
                for program in next(
                    source_lane["ranking_tickets"] for source_lane in run["lanes"]
                    if source_lane["lane_id"] == lane["lane_id"]
                )),
                maturity_rows=maturity_rows,
            ),
            "automatic_policy_change": False,
            "portfolio_mutation_authority": False,
            "capital_authority": False,
        }
        settlement = {**body, "settlement_sha256": stable_sha256(body)}
        _write(settlement_path, settlement)
        leaf = GoldenLeaf(
            owner=owner, object_kind="rank_program_tournament_settlement",
            object_id=body["settlement_id"], epoch=run["run_sha256"],
            occurred_at=evaluated, available_at=evaluated, payload=settlement,
            source_refs=(f"rank-program-run:{run['run_sha256']}",),
        )
        store = GoldenStore(store_path)
        run_leaf = store.head(owner, "rank_program_tournament_run", str(run["run_id"]))
        store.append_bundle((leaf,), (GoldenEdge(leaf.leaf_sha256, run_leaf["leaf_sha256"], "settles"),))
        settled.append(settlement)
    return {
        "ok": True, "evaluated_at": evaluated, "settled": settled, "pending": pending,
        "status": rank_program_tournament_status(root),
        "capital_authority": False,
    }


def _review(settlements: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not settlements:
        return None
    horizons = {int(row.get("horizon_days") or 0) for row in settlements}
    if len(horizons) != 1:
        raise ValueError("rank-program review cannot pool different outcome horizons")
    horizon_days = horizons.pop()
    program_families = {
        str(row.get("program_family_sha256") or "legacy-two-program-family")
        for row in settlements
    }
    if len(program_families) != 1:
        raise ValueError("rank-program review cannot pool different program families")
    program_family_sha256 = program_families.pop()
    proxies, scores_by_kind = [], {}
    for settlement in settlements:
        for lane in settlement["lane_results"]:
            episode_id = f"{settlement['run_id']}::{lane['lane_id']}"
            proxies.append({
                "run_id": episode_id,
                "return_window_binding": lane["return_window_binding"],
                "return_window_settlement": lane["return_window_settlement"],
            })
    blocks = overlap_cluster_ids(proxies)
    for settlement in settlements:
        for lane in settlement["lane_results"]:
            episode_id = f"{settlement['run_id']}::{lane['lane_id']}"
            for result in lane["ranking_scores"]:
                score = result["score"]
                scores_by_kind.setdefault(str(lane["entity_kind"]), []).append(EvaluationScore(
                    model_id=result["program_id"], episode_id=episode_id,
                    inference_block_id=blocks[episode_id],
                    losses={
                        "rank_calibration_error": float(score["rank_calibration"]["value"]),
                        "top_1_regret": float(score["regret"]["value"]),
                        "pairwise_rank_error": 1.0 - float(score["pairwise_rank_accuracy"]),
                    },
                ))
    reviews_by_kind = {}
    for entity_kind, scores in sorted(scores_by_kind.items()):
        episode_ids = sorted({row.episode_id for row in scores})
        model_ids = sorted({row.model_id for row in scores})
        survivor = conservative_paired_survivor_set(
            scores=scores, model_ids=model_ids, episode_ids=episode_ids,
            dimensions=("rank_calibration_error", "top_1_regret", "pairwise_rank_error"),
            min_inference_blocks=MINIMUM_INFERENCE_BLOCKS,
        )
        statistical_unique = (
            survivor["survivor_model_ids"][0]
            if survivor["inference_sufficient"] and len(survivor["survivor_model_ids"]) == 1
            else None
        )
        reviews_by_kind[entity_kind] = {
            "program_ids": model_ids,
            "survivor_set": survivor,
            "recommended_rank_program_id": (
                statistical_unique if horizon_days == PRIMARY_HORIZON_DAYS else None
            ),
        }
    primary_kind = "public_equity" if "public_equity" in reviews_by_kind else next(iter(reviews_by_kind))
    primary_review = reviews_by_kind[primary_kind]
    unique = primary_review["recommended_rank_program_id"]
    survivor = primary_review["survivor_set"]
    all_sufficient = all(
        row["survivor_set"]["inference_sufficient"] for row in reviews_by_kind.values()
    )
    body = {
        "schema": "jaggedthoughts-rank-program-review-v1",
        "horizon_days": horizon_days,
        "program_family_sha256": program_family_sha256,
        "evaluated_through": max(str(row.get("evaluated_at") or "") for row in settlements),
        "estimand_role": (
            "primary_patient_capital_rank_evidence"
            if horizon_days == PRIMARY_HORIZON_DAYS else "diagnostic_only"
        ),
        "settlement_sha256s": sorted(row["settlement_sha256"] for row in settlements),
        "reviews_by_entity_kind": reviews_by_kind,
        "primary_review_entity_kind": primary_kind,
        "survivor_set": survivor,
        "recommended_rank_program_id": unique,
        "status": (
            "diagnostic_horizon_only" if horizon_days != PRIMARY_HORIZON_DAYS
            else
            "collecting_independent_blocks" if not all_sufficient
            else "eligible_for_operator_review" if unique
            else "no_unique_statistical_survivor"
        ),
        "automatic_policy_change": False,
        "portfolio_mutation_authority": False,
        "capital_authority": False,
    }
    return {**body, "review_sha256": stable_sha256(body)}


def rank_program_tournament_status(root: Path) -> dict[str, Any]:
    """Project runs, settlements, and the paired evidence gate."""

    base = root / "rank_program_tournament"
    all_runs = [row for path in sorted((base / "runs").glob("*.json")) if (row := _read(path))]
    superseded_ids = {
        str(row.get("prior_run_id") or "")
        for path in sorted((base / "supersessions").glob("*.json"))
        if (row := _read(path))
    }
    runs = [row for row in all_runs if str(row.get("run_id") or "") not in superseded_ids]
    settlements = [
        row for path in sorted((base / "settlements").glob("*.json")) if (row := _read(path))
    ]
    settled_ids = {str(row["run_id"]) for row in settlements}
    settlements_by_family: dict[tuple[int, str], list[dict[str, Any]]] = {}
    for settlement in settlements:
        settlements_by_family.setdefault(
            (
                int(settlement.get("horizon_days") or 0),
                str(settlement.get("program_family_sha256") or "legacy-two-program-family"),
            ), [],
        ).append(settlement)
    review_history_by_horizon: dict[str, list[dict[str, Any]]] = {}
    for (horizon, _family), rows in sorted(settlements_by_family.items()):
        value = _review(rows)
        if value:
            review_history_by_horizon.setdefault(str(horizon), []).append(value)
    latest_primary_run = max(
        (row for row in runs if int(row.get("horizon_days") or 0) == PRIMARY_HORIZON_DAYS),
        key=lambda row: str(row.get("opened_at") or ""), default=None,
    )
    latest_diagnostic_run = max(
        (row for row in runs if int(row.get("horizon_days") or 0) != PRIMARY_HORIZON_DAYS),
        key=lambda row: str(row.get("opened_at") or ""), default=None,
    )
    latest_run = latest_primary_run or latest_diagnostic_run
    reviews_by_horizon = {
        horizon: max(rows, key=lambda row: row["evaluated_through"])
        for horizon, rows in review_history_by_horizon.items()
    }
    primary_reviews = review_history_by_horizon.get(str(PRIMARY_HORIZON_DAYS), [])
    preferred_family = str((latest_primary_run or {}).get("program_family_sha256") or "")
    review = next(
        (row for row in primary_reviews if row["program_family_sha256"] == preferred_family),
        reviews_by_horizon.get(str(PRIMARY_HORIZON_DAYS)),
    )
    latest_settlement = max(
        settlements, key=lambda row: str(row.get("evaluated_at") or ""), default=None,
    )
    pending_runs = [row for row in runs if str(row.get("run_id")) not in settled_ids]
    pending_lane_count = bound_lane_count = 0
    for run in pending_runs:
        for lane in run.get("lanes") or ():
            envelope = _read(_binding_path(
                root, str(run["run_id"]), str(lane["lane_id"]),
            )) or {}
            if (envelope.get("binding") or {}).get("status") == "bound":
                bound_lane_count += 1
            else:
                pending_lane_count += 1
    if review:
        next_activation = review["status"]
    elif pending_lane_count:
        next_activation = "bind_next_postseal_common_price"
    elif bound_lane_count:
        next_activation = "await_first_rank_outcome_maturity"
    elif settlements:
        next_activation = "open_next_nonoverlapping_primary_rank_block"
    else:
        next_activation = "open_first_paired_rank_blocks"
    body = {
        "schema": RANK_PROGRAM_STATUS_SCHEMA,
        "run_count": len(runs), "superseded_count": len(superseded_ids),
        "settled_count": len(settlements),
        "pending_count": sum(str(row.get("run_id")) not in settled_ids for row in runs),
        "minimum_inference_blocks": MINIMUM_INFERENCE_BLOCKS,
        "primary_horizon_days": PRIMARY_HORIZON_DAYS,
        "reviews_by_horizon": reviews_by_horizon,
        "review_history_by_horizon": review_history_by_horizon,
        "latest_run": latest_run,
        "latest_primary_run": latest_primary_run,
        "latest_diagnostic_run": latest_diagnostic_run,
        "latest_settlement": latest_settlement,
        "review": review,
        "entry_binding": {
            "pending_lane_count": pending_lane_count,
            "bound_lane_count": bound_lane_count,
        },
        "next_activation": next_activation,
        "automatic_policy_change": False,
        "portfolio_mutation_authority": False,
        "capital_authority": False,
    }
    return {**body, "status_sha256": stable_sha256(body)}


__all__ = [
    "DIAGNOSTIC_HORIZON_DAYS", "MINIMUM_INFERENCE_BLOCKS", "PRIMARY_HORIZON_DAYS",
    "RANK_PROGRAM_INPUT_SCHEMA", "RANK_PROGRAM_RUN_SCHEMA",
    "RANK_PROGRAM_SETTLEMENT_SCHEMA", "RANK_PROGRAM_STATUS_SCHEMA",
    "compile_rank_program_input", "open_rank_program_tournament",
    "rank_program_price_refresh_entity_ids",
    "rank_program_definitions", "rank_program_tournament_status",
    "settle_rank_program_tournaments",
]
