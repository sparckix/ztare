"""Pre-outcome closure over interpretable company-state partitions."""

from __future__ import annotations

from argparse import ArgumentParser
from bisect import bisect_right
from collections import Counter
from datetime import date
from hashlib import sha256
import json
import math
from pathlib import Path
from statistics import mean
from typing import Any, Mapping, Sequence

import yaml

from ztare.common.equivariance import stable_sha256
from ztare.fit.mdl import description_units
from ztare.strategy import (
    CandidateEvaluation,
    FrontierScope,
    Neighborhood,
    OperatorGrammar,
    ProgramInterpretation,
    RepresentationAudit,
    TypedOperator,
    TypedTerminal,
    TypedValue,
    compile_jaggedthoughts_frontier,
    enumerate_typed_programs,
    interpret_program,
)

from .company_state_flow import (
    COMPANY_STATE_FLOW_PROFILE_SCHEMA,
    _load_state_observations,
    _quarter_ends,
    _state_panel,
)
from .contracts import canonical_timestamp, require_text


COMPANY_STATE_PARTITION_FRONTIER_SCHEMA = "jaggedthoughts-company-state-partition-frontier-v1"
NEXT_TRANSITION_EVIDENCE_SCHEMA = "jaggedthoughts-company-state-next-transition-evidence-v1"
OBJECTIVES = (
    "state_granularity",
    "panel_coverage",
    "state_persistence",
    "transition_support",
    "transition_selectivity",
    "description_efficiency",
)
_VALUE_LABELS = {2: ("expensive", "cheap"), 3: ("expensive", "middle", "cheap")}
_DURABILITY_LABELS = {2: ("low", "high"), 3: ("low", "middle", "high")}


def _file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _cuts(values: Sequence[float], levels: int) -> tuple[float, ...]:
    ordered = sorted(float(value) for value in values)
    cuts = []
    for rank in range(1, levels):
        position = (len(ordered) - 1) * rank / levels
        lower, upper = math.floor(position), math.ceil(position)
        fraction = position - lower
        cuts.append(ordered[lower] * (1.0 - fraction) + ordered[upper] * fraction)
    return tuple(cuts)


def _partition_id(value_levels: int, durability_levels: int) -> str:
    parts = []
    if value_levels:
        parts.append(f"valuation_{value_levels}")
    if durability_levels:
        parts.append(f"durability_{durability_levels}")
    return "__x__".join(parts)


def _state_ids(value_levels: int, durability_levels: int) -> tuple[str, ...]:
    values = _VALUE_LABELS.get(value_levels, ("all",))
    durabilities = _DURABILITY_LABELS.get(durability_levels, ("all",))
    return tuple(
        "__".join(part for part in (
            f"valuation_{value}" if value_levels else "",
            f"durability_{durability}" if durability_levels else "",
        ) if part)
        for value in values
        for durability in durabilities
    )


def _partition_panel(
    panel: Mapping[str, Any], value_levels: int, durability_levels: int,
) -> dict[str, Any]:
    companies = list(panel["companies"])
    value_cuts = _cuts(
        [float(row["owner_earnings_yield"]) for row in companies], value_levels,
    ) if value_levels else ()
    durability_cuts = _cuts(
        [float(row["durable_earnings_score"]) for row in companies], durability_levels,
    ) if durability_levels else ()
    state_ids = _state_ids(value_levels, durability_levels)
    assignments = {}
    for row in companies:
        value_index = bisect_right(value_cuts, float(row["owner_earnings_yield"]))
        durability_index = bisect_right(
            durability_cuts, float(row["durable_earnings_score"]),
        )
        offset = value_index * max(1, durability_levels) + durability_index
        assignments[str(row["entity_id"])] = state_ids[offset]
    return {
        "epoch": str(panel["epoch"]),
        "thresholds": {
            "owner_earnings_yield": list(value_cuts),
            "durable_earnings_score": list(durability_cuts),
        },
        "assignments": assignments,
    }


def _candidate(
    panels: Sequence[Mapping[str, Any]], value_levels: int, durability_levels: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    partition_id = _partition_id(value_levels, durability_levels)
    state_ids = _state_ids(value_levels, durability_levels)
    partitioned = [
        _partition_panel(panel, value_levels, durability_levels) for panel in panels
    ]
    occupancy = [Counter(panel["assignments"].values()) for panel in partitioned]
    outgoing, cells = Counter(), Counter()
    transition_count = 0
    for source, target in zip(partitioned, partitioned[1:]):
        common = set(source["assignments"]) & set(target["assignments"])
        for entity_id in common:
            edge = (source["assignments"][entity_id], target["assignments"][entity_id])
            outgoing[edge[0]] += 1
            cells[edge] += 1
            transition_count += 1

    state_count = len(state_ids)
    minimum_coverage = min(len(row) / state_count for row in occupancy)
    minimum_persistence = min(
        sum(row[state_id] > 0 for row in occupancy) / len(occupancy)
        for state_id in state_ids
    )
    minimum_support = min(outgoing[state_id] for state_id in state_ids)
    support_floor = 4 * state_count
    definition_parts = []
    if value_levels:
        definition_parts.append(f"valuation=epoch_empirical_quantile_{value_levels}")
    if durability_levels:
        definition_parts.append(f"durability=epoch_empirical_quantile_{durability_levels}")
    if value_levels and durability_levels:
        definition_parts.append("composition=cartesian_product")
    definition = ";".join(definition_parts)
    units = description_units(definition)
    gates = {
        "business_interpretable": value_levels in {0, 2, 3} and durability_levels in {0, 2, 3},
        "panel_coverage": minimum_coverage + 1e-12 >= 1.0 - 1.0 / state_count,
        "state_persistence": minimum_persistence >= 0.75,
        "transition_support": minimum_support >= support_floor,
    }
    metrics = {
        "state_count": state_count,
        "panel_count": len(partitioned),
        "transition_count": transition_count,
        "minimum_panel_state_coverage": minimum_coverage,
        "mean_panel_state_coverage": mean(len(row) / state_count for row in occupancy),
        "minimum_state_panel_fraction": minimum_persistence,
        "minimum_state_occupancy": min(
            row[state_id] for row in occupancy for state_id in state_ids
        ),
        "minimum_outgoing_transition_support": minimum_support,
        "required_outgoing_transition_support": support_floor,
        "nonzero_transition_cell_count": len(cells),
        "transition_cell_density": len(cells) / (state_count * state_count),
        "description_units": units,
    }
    transition_counts = [
        [cells[(source, target)] for target in state_ids]
        for source in state_ids
    ]
    objectives = {
        "state_granularity": state_count / 9.0,
        "panel_coverage": minimum_coverage,
        "state_persistence": minimum_persistence,
        "transition_support": min(1.0, minimum_support / support_floor),
        "transition_selectivity": 1.0 - metrics["transition_cell_density"],
        "description_efficiency": 1.0 / units,
    }
    source = partitioned[-1]
    source_companies = {
        str(row["entity_id"]): row for row in panels[-1]["companies"]
    }
    return {
        "partition_id": partition_id,
        "value_levels": value_levels,
        "durability_levels": durability_levels,
        "definition": definition,
        "state_ids": list(state_ids),
        "transition_counts": transition_counts,
        "transition_counts_sha256": stable_sha256(transition_counts),
        "metrics": metrics,
        "objectives": objectives,
        "gates": gates,
        "support_valid": all(gates.values()),
    }, {
        "epoch": source["epoch"],
        "thresholds": source["thresholds"],
        "assignments": [
            {
                "entity_id": entity_id,
                "state_id": state_id,
                "evidence_sha256": source_companies[entity_id]["evidence_sha256"],
                "source_refs": source_companies[entity_id]["source_refs"],
            }
            for entity_id, state_id in sorted(source["assignments"].items())
        ],
    }


def _grammar() -> tuple[OperatorGrammar, ProgramInterpretation]:
    grammar = OperatorGrammar(
        grammar_id="jaggedthoughts.investment.company-state-partition",
        version="1",
        terminals=(
            TypedTerminal("valuation_2", "ValueResolution", description="valuation median split"),
            TypedTerminal("valuation_3", "ValueResolution", description="valuation terciles"),
            TypedTerminal("durability_2", "DurabilityResolution", description="durability median split"),
            TypedTerminal("durability_3", "DurabilityResolution", description="durability terciles"),
        ),
        operators=(
            TypedOperator("use_value", ("ValueResolution",), "CompanyStatePartition"),
            TypedOperator("use_durability", ("DurabilityResolution",), "CompanyStatePartition"),
            TypedOperator(
                "cross", ("ValueResolution", "DurabilityResolution"), "CompanyStatePartition",
            ),
        ),
    )
    interpretation = ProgramInterpretation(
        interpretation_id="company-state-partition-semantics-v1",
        grammar_digest=grammar.grammar_digest,
        terminal_values={
            "valuation_2": TypedValue("ValueResolution", 2),
            "valuation_3": TypedValue("ValueResolution", 3),
            "durability_2": TypedValue("DurabilityResolution", 2),
            "durability_3": TypedValue("DurabilityResolution", 3),
        },
        operator_functions={
            "use_value": lambda values: TypedValue("CompanyStatePartition", (values[0].value, 0)),
            "use_durability": lambda values: TypedValue(
                "CompanyStatePartition", (0, values[0].value),
            ),
            "cross": lambda values: TypedValue(
                "CompanyStatePartition", (values[0].value, values[1].value),
            ),
        },
    )
    return grammar, interpretation


def _neighbor(left: tuple[int, int], right: tuple[int, int]) -> bool:
    order = {0: 0, 2: 1, 3: 2}
    return sum(abs(order[a] - order[b]) for a, b in zip(left, right, strict=True)) == 1


def _next_quarter(epoch: str) -> str:
    current = date.fromisoformat(epoch)
    if current.month == 12:
        return date(current.year + 1, 3, 31).isoformat()
    month = current.month + 3
    return date(current.year, month, {3: 31, 6: 30, 9: 30, 12: 31}[month]).isoformat()


def _existing_audit(root: Path, experiment_id: str) -> dict[str, Any]:
    path = root / "experiments" / "results" / f"{experiment_id}.json"
    if not path.exists():
        return {"status": "missing_existing_company_state_evidence", "path": str(path)}
    body = json.loads(path.read_text(encoding="utf-8"))
    states = tuple(body.get("state_axes", {}).get("state_ids") or ())
    contains_frontier = bool(body.get("partition_frontier") or body.get("closure"))
    return {
        "status": "already_contains_pre_outcome_partition_frontier" if contains_frontier
        else "missing_pre_outcome_partition_frontier",
        "path": path.relative_to(root).as_posix(),
        "evidence_sha256": body.get("evidence_sha256"),
        "fixed_state_count": len(states),
        "contains_granularity_frontier": contains_frontier,
        "contains_exact_next_evidence_identity": bool(body.get("next_evidence_identity")),
    }


def compile_company_state_partition_frontier(
    profile_path: str | Path, *, workspace: str | Path,
) -> dict[str, Any]:
    """Close a state-partition scope using state coverage only, then freeze its successor."""
    root = Path(workspace).expanduser().resolve()
    source = Path(profile_path).expanduser()
    if not source.is_absolute():
        source = root / source
    source = source.resolve()
    profile = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(profile, Mapping) or profile.get("schema") != COMPANY_STATE_FLOW_PROFILE_SCHEMA:
        raise ValueError(f"company-state profile schema must be {COMPANY_STATE_FLOW_PROFILE_SCHEMA}")
    source_run_path = root / "data" / "latest_source_run.json"
    source_run = json.loads(source_run_path.read_text(encoding="utf-8"))
    raw_as_of = source_run["as_of"] if profile.get("as_of") == "latest_source_run" else profile["as_of"]
    as_of = canonical_timestamp(raw_as_of, "company-state partition source as_of")
    benchmark_id = require_text(profile.get("benchmark_id"), "company-state benchmark_id")
    epochs = _quarter_ends(str(profile["start_date"]), str(profile["end_date"]))
    observations_path = root / "data" / "observations.csv"
    panels, universe = _state_panel(
        _load_state_observations(observations_path, epochs, source_as_of=as_of),
        epochs, source_as_of=as_of,
        min_years=int(profile.get("min_years", 3)),
        min_cross_section=int(profile.get("min_cross_section", 20)),
        benchmark_id=benchmark_id,
    )
    if len(panels) < 2:
        raise ValueError("company-state partition closure requires at least two panels")
    panel_evidence_sha256 = stable_sha256([
        {
            "epoch": panel["epoch"],
            "companies": [{
                "entity_id": row["entity_id"],
                "owner_earnings_yield": row["owner_earnings_yield"],
                "durable_earnings_score": row["durable_earnings_score"],
                "evidence_sha256": row["evidence_sha256"],
            } for row in panel["companies"]],
        } for panel in panels
    ])

    grammar, interpretation = _grammar()
    enumeration = enumerate_typed_programs(grammar, max_depth=1, max_programs=32)
    programs = enumeration.programs_of_type("CompanyStatePartition")
    rows, snapshots, levels_by_program = {}, {}, {}
    for program in programs:
        value_levels, durability_levels = interpret_program(
            program, grammar=grammar, interpretation=interpretation,
        ).value
        row, snapshot = _candidate(panels, value_levels, durability_levels)
        row["program_id"] = program.program_id
        row["ast"] = program.to_dict()
        rows[program.program_id] = row
        snapshots[program.program_id] = snapshot
        levels_by_program[program.program_id] = (value_levels, durability_levels)

    evaluations = tuple(CandidateEvaluation(
        program_id=program_id,
        objective_values=tuple(float(row["objectives"][name]) for name in OBJECTIVES),
        behavior_signature=(str(row["partition_id"]),),
        evidence_refs=(f"pre-outcome-panels:{panel_evidence_sha256}",),
    ) for program_id, row in rows.items())
    edges = tuple(
        (left, right)
        for index, left in enumerate(sorted(rows))
        for right in sorted(rows)[index + 1:]
        if _neighbor(levels_by_program[left], levels_by_program[right])
    )
    neighborhood = Neighborhood(
        neighborhood_id=f"company-state-resolution-edit:{panel_evidence_sha256}", edges=edges,
    )
    scope = FrontierScope(
        grammar_id=grammar.grammar_id,
        grammar_version=grammar.version,
        grammar_digest=grammar.grammar_digest,
        target_type="CompanyStatePartition",
        max_depth=enumeration.max_depth,
        max_programs=enumeration.max_programs,
        evaluation_model_id="pre-outcome-state-support-v1",
        landscape_mode="fixed",
        evidence_epoch=panel_evidence_sha256,
        objective_names=OBJECTIVES,
        neighborhood_id=neighborhood.neighborhood_id,
    )
    certificate = compile_jaggedthoughts_frontier(
        scope=scope,
        enumeration=enumeration,
        evaluations=evaluations,
        neighborhood=neighborhood,
        representation_audit=RepresentationAudit(
            audit_id=f"company-state-axis-library:{panel_evidence_sha256}",
            status="residual",
            residuals=(
                "The grammar covers valuation and durable-earnings axes only.",
                "The historical company universe is current-store selected.",
            ),
            evidence_refs=(f"pre-outcome-panels:{panel_evidence_sha256}",),
        ),
    )
    frontier_ids = set(certificate.frontier_program_ids)
    valid = [
        row for program_id, row in rows.items()
        if program_id in frontier_ids and row["support_valid"] and row["metrics"]["state_count"] > 4
    ]
    selected = max(valid, key=lambda row: (
        int(row["metrics"]["state_count"]),
        float(row["objectives"]["transition_selectivity"]),
        float(row["objectives"]["panel_coverage"]),
        -int(row["metrics"]["description_units"]),
        str(row["partition_id"]),
    )) if valid else None

    activation: dict[str, Any] = {
        "status": "future_research_activation" if selected else "killed_no_supported_refinement",
        "signal_authority": False,
        "model_fit_authority": False,
        "capital_authority": False,
    }
    if selected is not None:
        selected_program_id = str(selected["program_id"])
        snapshot = snapshots[selected_program_id]
        entity_ids = [str(row["entity_id"]) for row in snapshot["assignments"]]
        target_epoch = _next_quarter(str(snapshot["epoch"]))
        partition_identity = {
            "partition_id": selected["partition_id"],
            "value_levels": selected["value_levels"],
            "durability_levels": selected["durability_levels"],
            "definition": selected["definition"],
            "state_ids": selected["state_ids"],
            "grammar_digest": grammar.grammar_digest,
        }
        next_identity: dict[str, Any] = {
            "schema": NEXT_TRANSITION_EVIDENCE_SCHEMA,
            "partition_sha256": stable_sha256(partition_identity),
            "source_epoch": snapshot["epoch"],
            "target_epoch": target_epoch,
            "settlement_not_before": f"{target_epoch}T23:59:59Z",
            "benchmark_id": benchmark_id,
            "min_years": int(profile.get("min_years", 3)),
            "source_entity_count": len(entity_ids),
            "source_entity_ids_sha256": stable_sha256(entity_ids),
            "source_assignments_sha256": stable_sha256(snapshot["assignments"]),
            "membership_rule": "freeze source cohort; censor missing target observations",
            "target_threshold_population": "target-eligible members of the frozen source cohort",
            "minimum_target_entity_count": max(
                int(profile.get("min_cross_section", 20)), math.ceil(0.8 * len(entity_ids)),
            ),
            "availability_rule": "use only observations available by the target source-run as_of",
            "required_output": "target state assignments and transition counts; no return field",
            "signal_authority": False,
            "capital_authority": False,
        }
        next_identity["evidence_id"] = (
            f"company-state-transition:{snapshot['epoch']}:{target_epoch}:"
            f"{stable_sha256(next_identity)[:16]}"
        )
        activation.update({
            "partition_id": selected["partition_id"],
            "partition_sha256": stable_sha256(partition_identity),
            "source_snapshot": snapshot,
            "next_evidence_identity": next_identity,
        })
    activation["activation_sha256"] = stable_sha256(activation)

    body: dict[str, Any] = {
        "schema": COMPANY_STATE_PARTITION_FRONTIER_SCHEMA,
        "frontier_id": f"{profile['experiment_id']}-partition-frontier",
        "as_of": as_of,
        "authority": "research_activation_only",
        "existing_evidence_audit": _existing_audit(
            root, require_text(profile.get("experiment_id"), "company-state experiment_id"),
        ),
        "input_identity": {
            "profile_sha256": stable_sha256({**profile, "as_of": as_of}),
            "source_run_sha256": source_run.get("run_sha256") or _file_sha256(source_run_path),
            "observations_sha256": _file_sha256(observations_path),
            "panel_evidence_sha256": panel_evidence_sha256,
            "universe": universe,
        },
        "grammar": grammar.to_dict(),
        "enumeration": {
            "enumeration_digest": enumeration.enumeration_digest,
            "candidate_count": len(programs),
            "exhausted_within_scope": enumeration.exhausted_within_scope,
            "residuals": [row.to_dict() for row in enumeration.residuals],
        },
        "closure": {
            "certificate_sha256": certificate.certificate_sha256,
            "frontier_program_ids": list(certificate.frontier_program_ids),
            "frontier_partition_ids": sorted(
                rows[program_id]["partition_id"] for program_id in certificate.frontier_program_ids
            ),
            "local_peak_partition_ids": sorted(
                rows[program_id]["partition_id"] for program_id in certificate.local_peak_program_ids
            ),
            "scope_closed": certificate.scope_closed,
            "decision_closed": certificate.decision_closed,
            "representation_residuals": list(certificate.representation_audit.residuals),
        },
        "candidate_partitions": sorted(rows.values(), key=lambda row: str(row["partition_id"])),
        "activation": activation,
        "use_boundary": (
            "This artifact chooses a prospective state-evidence identity from coverage, support, "
            "compression, and business legibility. It does not fit returns, emit a signal, or alter capital."
        ),
    }
    return {**body, "partition_frontier_sha256": stable_sha256(body)}


def main() -> int:
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("profile")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    result = compile_company_state_partition_frontier(args.profile, workspace=args.workspace)
    payload = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        destination = Path(args.output).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(payload, encoding="utf-8")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "COMPANY_STATE_PARTITION_FRONTIER_SCHEMA",
    "NEXT_TRANSITION_EVIDENCE_SCHEMA",
    "compile_company_state_partition_frontier",
]
