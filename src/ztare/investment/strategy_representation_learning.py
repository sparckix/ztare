"""Turn strategy-security counterexamples into future-only grammar challenges."""

from __future__ import annotations

from itertools import combinations
from typing import Any, Mapping

from ztare.common.cegis_membrane import evidence_promotion_receipt
from ztare.common.equivariance import stable_sha256
from ztare.strategy import (
    CandidateEvaluation,
    ClaimDisposition,
    CompiledJaggedThoughtsProfile,
    EnumerationResult,
    FrontierScope,
    Neighborhood,
    OperatorGrammar,
    Program,
    ProgramInterpretation,
    RepresentationAudit,
    StrategicClaim,
    TypedOperator,
    TypedTerminal,
    TypedValue,
    build_typed_program,
    challenge_representation,
    compile_enumeration_result,
    compile_evidence_manifest,
    compile_jaggedthoughts_frontier,
    interpret_program,
)

from .contracts import canonical_timestamp, require_text, timestamp_key
from .historical_strategy_control_design import (
    HISTORICAL_STRATEGY_MODERATOR_DIMENSIONS,
    enumerate_historical_strategy_moderator_programs,
)
from .historical_strategy_event_replay import HISTORICAL_STRATEGY_EVENT_REPLAY_SCHEMA
from .strategy_walk_forward import STRATEGY_SECURITY_WALK_FORWARD_SCHEMA


STRATEGY_SECURITY_GRAMMAR_CONJECTURE_SCHEMA = (
    "jaggedthoughts-strategy-security-grammar-conjecture-v1"
)
STRATEGY_SECURITY_REPRESENTATION_LEARNING_SCHEMA = (
    "jaggedthoughts-strategy-security-representation-learning-v1"
)
_MIN_PROSPECTIVE_BLOCKS = 8
_TARGET_TYPE = "historical_strategy_projection"
_REPRESENTATION_OBJECTIVES = (
    "exact_path_projection_rate",
    "parsimony",
)
_PATH_INTERPRETER_VERSION = "source-bound-connected-path-interpreter-v1"
_STRICT_IMPROVEMENT_MARGIN = 1e-12


def _path_grammar_delta() -> tuple[
    dict[str, Any], OperatorGrammar, EnumerationResult,
    OperatorGrammar, EnumerationResult,
]:
    baseline, baseline_programs, _ = enumerate_historical_strategy_moderator_programs()
    baseline_enumeration = compile_enumeration_result(
        baseline,
        programs=baseline_programs,
        max_depth=len(HISTORICAL_STRATEGY_MODERATOR_DIMENSIONS),
        max_programs=len(baseline_programs),
    )
    terminals = tuple(
        TypedTerminal(
            f"source_bound_strategy_move_{position}",
            "historical_strategy_move",
            claim_ids=("source_bound_move", "single_issuer_identity"),
            description=f"Ordered source-bound management-move slot {position}.",
        )
        for position in range(1, 4)
    )
    operators = (
        TypedOperator(
            "compose_strategy_moves",
            ("historical_strategy_move", "historical_strategy_move"),
            "historical_strategy_move_path",
            claim_ids=("same_issuer", "strict_event_order", "connected_interval"),
            description="Compose two ordered moves from the same issuer into one path.",
        ),
        TypedOperator(
            "append_strategy_move",
            ("historical_strategy_move_path", "historical_strategy_move"),
            "historical_strategy_move_path",
            claim_ids=("same_issuer", "strict_event_order", "connected_interval"),
            description="Append one later move to an existing connected path.",
        ),
        TypedOperator(
            "project_strategy_move_path",
            ("historical_strategy_move_path",),
            "historical_strategy_projection",
            claim_ids=("path_signature_declared",),
            description="Project a connected move path onto the strategy forecast surface.",
        ),
    )
    challenger = OperatorGrammar(
        grammar_id=baseline.grammar_id,
        version="2-path-challenger",
        terminals=baseline.terminals + terminals,
        operators=baseline.operators + operators,
    )
    base = build_typed_program(challenger, terminal_id="all_typed_events")
    challenger_programs = []
    for depth in range(len(HISTORICAL_STRATEGY_MODERATOR_DIMENSIONS) + 1):
        for fields in combinations(HISTORICAL_STRATEGY_MODERATOR_DIMENSIONS, depth):
            program = base
            for field in fields:
                program = build_typed_program(
                    challenger,
                    operator_id=f"condition_on_{field}",
                    children=(program,),
                )
            challenger_programs.append(program)
    move_1, move_2, move_3 = (
        build_typed_program(challenger, terminal_id=f"source_bound_strategy_move_{position}")
        for position in range(1, 4)
    )
    path_2 = build_typed_program(
        challenger, operator_id="compose_strategy_moves", children=(move_1, move_2),
    )
    projection_2 = build_typed_program(
        challenger, operator_id="project_strategy_move_path", children=(path_2,),
    )
    path_3 = build_typed_program(
        challenger, operator_id="append_strategy_move", children=(path_2, move_3),
    )
    projection_3 = build_typed_program(
        challenger, operator_id="project_strategy_move_path", children=(path_3,),
    )
    challenger_programs.extend((projection_2, projection_3))
    challenger_enumeration = compile_enumeration_result(
        challenger,
        programs=challenger_programs,
        max_depth=len(HISTORICAL_STRATEGY_MODERATOR_DIMENSIONS),
        max_programs=len(challenger_programs),
    )
    definitions = {
        "added_terminals": [row.to_dict() for row in terminals],
        "removed_terminals": [],
        "added_operators": [row.to_dict() for row in operators],
        "removed_operators": [],
    }
    return ({
        "baseline_grammar": baseline.to_dict(),
        "challenger_grammar": challenger.to_dict(),
        "full_typed_delta": definitions,
        "full_typed_delta_sha256": stable_sha256(definitions),
        "baseline_enumeration": baseline_enumeration.to_dict(),
        "challenger_enumeration": challenger_enumeration.to_dict(),
        "canonical_incumbent_program_count": len(baseline_programs),
        "canonical_path_program_count": 2,
    }, baseline, baseline_enumeration, challenger, challenger_enumeration)


def _verified_tournament(raw: Mapping[str, Any]) -> dict[str, Any]:
    tournament = dict(raw)
    if tournament.get("schema") != STRATEGY_SECURITY_WALK_FORWARD_SCHEMA:
        raise ValueError(
            f"strategy representation learning requires {STRATEGY_SECURITY_WALK_FORWARD_SCHEMA}"
        )
    claimed = require_text(tournament.get("tournament_sha256"), "tournament_sha256")
    payload = {key: value for key, value in tournament.items() if key != "tournament_sha256"}
    if claimed != stable_sha256(payload):
        raise ValueError("strategy-security tournament digest does not match its payload")
    if tournament.get("capital_authority") is not False:
        raise ValueError("strategy-security tournaments must deny capital authority")
    return tournament


def _verified_replay(
    raw: Mapping[str, Any], tournament: Mapping[str, Any],
) -> dict[str, Any]:
    replay = dict(raw)
    if replay.get("schema") != HISTORICAL_STRATEGY_EVENT_REPLAY_SCHEMA:
        raise ValueError(
            f"strategy representation learning requires {HISTORICAL_STRATEGY_EVENT_REPLAY_SCHEMA}"
        )
    claimed = require_text(replay.get("replay_sha256"), "replay_sha256")
    if claimed != stable_sha256({key: value for key, value in replay.items() if key != "replay_sha256"}):
        raise ValueError("historical strategy replay digest does not match its payload")
    if tournament.get("replay_sha256") != claimed:
        raise ValueError("strategy tournament and replay identities differ")
    return replay


def _moderator_fields(program: Program) -> tuple[str, ...] | None:
    if program.terminal_id == "all_typed_events":
        return ()
    if program.operator_id and program.operator_id.startswith("condition_on_"):
        child = _moderator_fields(program.children[0])
        if child is not None:
            return tuple(sorted({*child, program.operator_id.removeprefix("condition_on_")}))
    return None


def _path_length(program: Program) -> int | None:
    if program.terminal_id and program.terminal_id.startswith("source_bound_strategy_move_"):
        return 1
    if program.operator_id in {"compose_strategy_moves", "append_strategy_move"}:
        lengths = tuple(_path_length(child) for child in program.children)
        return sum(length for length in lengths if length is not None) \
            if all(length is not None for length in lengths) else None
    if program.operator_id == "project_strategy_move_path":
        return _path_length(program.children[0])
    return None


def _node_count(program: Program) -> int:
    return 1 + sum(_node_count(child) for child in program.children)


def _event_atom(episode: Mapping[str, Any]) -> dict[str, Any]:
    phenotype = episode.get("transaction_phenotype")
    phenotype = phenotype if isinstance(phenotype, Mapping) else {}
    return {
        "episode_sha256": require_text(episode.get("episode_sha256"), "episode_sha256"),
        "entity_id": require_text(episode.get("entity_id"), "entity_id"),
        "occurred_at": canonical_timestamp(str(episode.get("occurred_at") or ""), "occurred_at"),
        "phenotype": [
            str(episode.get("implementation_mode") or "indeterminate"),
            *[
                str(phenotype.get(field) or "indeterminate")
                for field in HISTORICAL_STRATEGY_MODERATOR_DIMENSIONS
                if field != "implementation_mode"
            ],
        ],
    }


def _validate_path(
    members: tuple[Mapping[str, Any], ...], *, horizon_days: int,
) -> tuple[dict[str, Any], ...]:
    atoms = tuple(dict(member) for member in members)
    if len(atoms) not in {2, 3}:
        raise ValueError("connected strategy paths require two or three moves")
    if len({str(row["entity_id"]) for row in atoms}) != 1:
        raise ValueError("connected strategy paths cannot cross issuers")
    if len({str(row["episode_sha256"]) for row in atoms}) != len(atoms):
        raise ValueError("connected strategy paths cannot reuse one move")
    times = [timestamp_key(str(row["occurred_at"])) for row in atoms]
    if any(right <= left for left, right in zip(times, times[1:])):
        raise ValueError("connected strategy paths require strict event order")
    if any((right - left).days > horizon_days for left, right in zip(times, times[1:])):
        raise ValueError("strategy moves do not share a connected event interval")
    return atoms


def _projection(members: tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    return {
        "entity_id": str(members[0]["entity_id"]),
        "ordered_episode_sha256s": [str(row["episode_sha256"]) for row in members],
        "connected_interval": {
            "start": str(members[0]["occurred_at"]),
            "end": str(members[-1]["occurred_at"]),
        },
        "path_signature": [list(row["phenotype"]) for row in members],
    }


def _interpret_path(
    program: Program, grammar: OperatorGrammar,
    members: tuple[Mapping[str, Any], ...], *, horizon_days: int,
) -> dict[str, Any]:
    terminal_values = {
        f"source_bound_strategy_move_{index}": TypedValue(
            "historical_strategy_move", dict(member),
        )
        for index, member in enumerate(members, start=1)
    }

    def compose(values: tuple[TypedValue, ...]) -> TypedValue:
        path = _validate_path(tuple(value.value for value in values), horizon_days=horizon_days)
        return TypedValue("historical_strategy_move_path", path)

    def append(values: tuple[TypedValue, ...]) -> TypedValue:
        path = _validate_path(tuple(values[0].value) + (values[1].value,), horizon_days=horizon_days)
        return TypedValue("historical_strategy_move_path", path)

    def project(values: tuple[TypedValue, ...]) -> TypedValue:
        return TypedValue("historical_strategy_projection", _projection(tuple(values[0].value)))

    value = interpret_program(
        program,
        grammar=grammar,
        interpretation=ProgramInterpretation(
            _PATH_INTERPRETER_VERSION,
            grammar.grammar_digest,
            terminal_values,
            {
                "compose_strategy_moves": compose,
                "append_strategy_move": append,
                "project_strategy_move_path": project,
            },
        ),
    )
    return dict(value.value)


def _ordered_witness_members(
    replay: Mapping[str, Any], witnesses: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], ...]]:
    episodes = {
        str(row["episode_sha256"]): _event_atom(row)
        for row in replay.get("episodes") or () if isinstance(row, Mapping)
    }
    return [
        tuple(sorted(
            (episodes[episode_sha] for episode_sha in witness["episode_sha256s"]),
            key=lambda row: (row["occurred_at"], row["episode_sha256"]),
        ))
        for witness in witnesses
    ]


def _path_programs(enumeration: EnumerationResult) -> dict[int, Program]:
    result = {}
    for program in enumeration.programs_of_type(_TARGET_TYPE):
        length = _path_length(program)
        if length is not None:
            result[length] = program
    return result


def _probe_receipt(
    *, grammar: OperatorGrammar, enumeration: EnumerationResult,
    replay: Mapping[str, Any], witnesses: list[dict[str, Any]], horizon_days: int,
) -> dict[str, Any]:
    programs = _path_programs(enumeration)
    witness_members = _ordered_witness_members(replay, witnesses)
    positives = []
    for length, program in sorted(programs.items()):
        for members in witness_members:
            for start in range(len(members) - length + 1):
                probe_members = members[start:start + length]
                positives.append({
                    "probe_id": stable_sha256({
                        "kind": "positive", "program_id": program.program_id,
                        "episode_sha256s": [row["episode_sha256"] for row in probe_members],
                    }),
                    "kind": "positive",
                    "program": program,
                    "members": probe_members,
                })
    negatives = []
    for positive in positives:
        members = positive["members"]
        negatives.extend((
            {**positive, "probe_id": f"{positive['probe_id']}:reversed", "kind": "reversed_order", "members": tuple(reversed(members))},
            {**positive, "probe_id": f"{positive['probe_id']}:duplicate", "kind": "duplicate_event", "members": members[:-1] + (members[0],)},
        ))
        other = next((
            row for row in positives
            if len(row["members"]) == len(members)
            and row["members"][0]["entity_id"] != members[0]["entity_id"]
        ), None)
        if other is not None:
            negatives.append({
                **positive,
                "probe_id": f"{positive['probe_id']}:cross-issuer",
                "kind": "cross_issuer_splice",
                "members": members[:-1] + (other["members"][-1],),
            })
    by_entity: dict[str, list[dict[str, Any]]] = {}
    for row in replay.get("episodes") or ():
        if isinstance(row, Mapping):
            atom = _event_atom(row)
            by_entity.setdefault(atom["entity_id"], []).append(atom)
    disconnected = next((
        (left, right)
        for rows in by_entity.values()
        for left in sorted(rows, key=lambda row: row["occurred_at"])
        for right in sorted(rows, key=lambda row: row["occurred_at"])
        if (timestamp_key(right["occurred_at"]) - timestamp_key(left["occurred_at"])).days > horizon_days
    ), None)
    if disconnected is not None and 2 in programs:
        negatives.append({
            "probe_id": stable_sha256({
                "kind": "disconnected", "episode_sha256s": [row["episode_sha256"] for row in disconnected],
            }),
            "kind": "disconnected_same_issuer",
            "program": programs[2],
            "members": disconnected,
        })

    positive_rows, negative_rows, invariant_rows = [], [], []
    outputs_by_program: dict[str, list[str]] = {program.program_id: [] for program in programs.values()}
    for probe in positives:
        expected = _projection(probe["members"])
        try:
            output = _interpret_path(
                probe["program"], grammar, probe["members"], horizon_days=horizon_days,
            )
            exact = output == expected
            output_sha = stable_sha256(output)
            if exact:
                outputs_by_program[probe["program"].program_id].append(output_sha)
        except (KeyError, TypeError, ValueError):
            exact, output_sha = False, None
        positive_rows.append({
            "probe_id": probe["probe_id"], "program_id": probe["program"].program_id,
            "path_length": len(probe["members"]), "exact_projection": exact,
            "output_sha256": output_sha,
        })
        perturbed = tuple({**row, "irrelevant_metadata": "ignored"} for row in probe["members"])
        try:
            invariant = _interpret_path(
                probe["program"], grammar, perturbed, horizon_days=horizon_days,
            ) == expected
        except (KeyError, TypeError, ValueError):
            invariant = False
        invariant_rows.append({"probe_id": probe["probe_id"], "passed": invariant})
    for probe in negatives:
        try:
            _interpret_path(
                probe["program"], grammar, probe["members"], horizon_days=horizon_days,
            )
            rejected = False
        except (KeyError, TypeError, ValueError):
            rejected = True
        negative_rows.append({
            "probe_id": probe["probe_id"], "kind": probe["kind"], "rejected": rejected,
        })
    required_negative_kinds = {
        "reversed_order", "duplicate_event", "cross_issuer_splice", "disconnected_same_issuer",
    }
    observed_negative_kinds = {row["kind"] for row in negative_rows}
    probe_set = [
        {
            "probe_id": probe["probe_id"], "kind": probe["kind"],
            "program_id": probe["program"].program_id,
            "ordered_episode_sha256s": [row["episode_sha256"] for row in probe["members"]],
        }
        for probe in [*positives, *negatives]
    ]
    body = {
        "interpreter_version": _PATH_INTERPRETER_VERSION,
        "interpreter_sha256": stable_sha256({"version": _PATH_INTERPRETER_VERSION}),
        "probe_set_sha256": stable_sha256(probe_set),
        "positive_results": positive_rows,
        "negative_results": negative_rows,
        "metadata_invariance_results": invariant_rows,
        "outputs_by_program": {
            program_id: sorted(set(output_sha256s))
            for program_id, output_sha256s in sorted(outputs_by_program.items())
        },
        "hard_gates": {
            "all_positive_paths_project_exactly": bool(positive_rows) and all(row["exact_projection"] for row in positive_rows),
            "invalid_tuple_specificity_is_one": required_negative_kinds <= observed_negative_kinds and all(row["rejected"] for row in negative_rows),
            "irrelevant_metadata_invariant": bool(invariant_rows) and all(row["passed"] for row in invariant_rows),
            "distinct_positive_paths_remain_distinct": len({row["output_sha256"] for row in positive_rows if row["output_sha256"]}) >= 2,
        },
    }
    return {**body, "probe_receipt_sha256": stable_sha256(body)}


def _representation_profile(
    *, profile_id: str, grammar: OperatorGrammar, enumeration: EnumerationResult,
    probe_receipt: Mapping[str, Any], evidence_epoch: str, evidence_ref: str,
    evaluation_surface_sha256: str,
) -> CompiledJaggedThoughtsProfile:
    positive_by_program: dict[str, list[Mapping[str, Any]]] = {}
    for row in probe_receipt.get("positive_results") or ():
        positive_by_program.setdefault(str(row["program_id"]), []).append(row)
    outputs_by_program = probe_receipt.get("outputs_by_program") or {}
    evaluations = []
    for program in enumeration.programs_of_type(_TARGET_TYPE):
        fields = _moderator_fields(program)
        if fields is not None:
            objectives = (0.0, 1.0 / _node_count(program))
            signature = (f"isolated-projection:{stable_sha256({'fields': fields})}",)
        else:
            rows = positive_by_program.get(program.program_id, [])
            exact_rate = sum(bool(row["exact_projection"]) for row in rows) / max(1, len(rows))
            length = _path_length(program) or 1
            objectives = (exact_rate, length / _node_count(program))
            signature = tuple(outputs_by_program.get(program.program_id) or ()) or (
                f"empty-path-projection:{length}",
            )
        evaluations.append(CandidateEvaluation(
            program.program_id, objectives, signature, (evidence_ref,),
        ))
    claims = tuple(
        StrategicClaim(claim_id, "internal", claim_id.replace("_", " "))
        for claim_id in sorted({
            claim_id for program in enumeration.programs_of_type(_TARGET_TYPE)
            for claim_id in program.claim_ids
        })
    )
    dispositions = tuple(
        ClaimDisposition(claim.claim_id, "supported", evidence_ref) for claim in claims
    )
    neighborhood = Neighborhood("same-epoch-behavior-identity", ())
    scope = FrontierScope(
        grammar.grammar_id, grammar.version, grammar.grammar_digest, _TARGET_TYPE,
        enumeration.max_depth, enumeration.max_programs,
        f"source-bound-path-probes-v1@sha256:{evaluation_surface_sha256}",
        "fixed", evidence_epoch, _REPRESENTATION_OBJECTIVES, neighborhood.neighborhood_id,
    )
    certificate = compile_jaggedthoughts_frontier(
        scope=scope, enumeration=enumeration, claims=claims,
        claim_dispositions=dispositions, evaluations=evaluations,
        neighborhood=neighborhood,
        representation_audit=RepresentationAudit(f"{profile_id}:representation"),
    )
    profile = CompiledJaggedThoughtsProfile(
        profile_id=profile_id,
        title="Strategy-security grammar behavior",
        decision_question="Does the grammar expose a reusable source-bound behavior?",
        owner="historical_strategy_representation_challenger",
        as_of=evidence_epoch,
        grammar=grammar,
        enumeration=enumeration,
        neighborhood=neighborhood,
        claims=claims,
        claim_dispositions=dispositions,
        evidence_manifest=compile_evidence_manifest({}, source_root=None),
        evaluation_kind="table",
        evaluation_model=None,
        evaluations=tuple(evaluations),
        certificate=certificate,
    )
    return profile


def _qualify_same_epoch_behavior(
    *, grammar_delta: Mapping[str, Any], baseline: OperatorGrammar,
    baseline_enumeration: EnumerationResult, challenger: OperatorGrammar,
    challenger_enumeration: EnumerationResult,
    tournament: Mapping[str, Any], replay: Mapping[str, Any],
    witnesses: list[dict[str, Any]], conjecture_id: str,
) -> dict[str, Any]:
    horizon_days = int((tournament.get("execution_contract") or {}).get("horizon_days") or 365)
    probe_receipt = _probe_receipt(
        grammar=challenger, enumeration=challenger_enumeration, replay=replay,
        witnesses=witnesses, horizon_days=horizon_days,
    )
    evaluation_surface_sha256 = stable_sha256({
        "schema": "strategy-security-path-evaluation-surface-v1",
        "probe_set_sha256": probe_receipt["probe_set_sha256"],
        "interpreter_sha256": probe_receipt["interpreter_sha256"],
        "objective_names": _REPRESENTATION_OBJECTIVES,
        "strict_improvement_margin": _STRICT_IMPROVEMENT_MARGIN,
    })
    evidence_epoch = stable_sha256({
        "replay_sha256": replay["replay_sha256"],
        "tournament_sha256": tournament["tournament_sha256"],
        "evaluation_surface_sha256": evaluation_surface_sha256,
    })
    evidence_ref = f"strategy-representation-evidence://{evidence_epoch}"
    baseline_profile = _representation_profile(
        profile_id=f"{conjecture_id}:baseline", grammar=baseline,
        enumeration=baseline_enumeration, probe_receipt=probe_receipt,
        evidence_epoch=evidence_epoch, evidence_ref=evidence_ref,
        evaluation_surface_sha256=evaluation_surface_sha256,
    )
    challenger_profile = _representation_profile(
        profile_id=f"{conjecture_id}:challenger", grammar=challenger,
        enumeration=challenger_enumeration, probe_receipt=probe_receipt,
        evidence_epoch=evidence_epoch, evidence_ref=evidence_ref,
        evaluation_surface_sha256=evaluation_surface_sha256,
    )
    if (
        baseline_profile.certificate.scope.evaluation_model_id
        != challenger_profile.certificate.scope.evaluation_model_id
    ):
        raise ValueError("strategy grammar profiles do not share one evaluation surface")
    challenge = challenge_representation(
        challenge_id=f"{conjecture_id}:same-epoch", baseline=baseline_profile,
        challenger=challenger_profile,
    )
    baseline_exact_rate = max(
        evaluation.objective_values[0] for evaluation in baseline_profile.evaluations
    )
    strict_material = [
        behavior for behavior in challenge.material_frontier_behaviors
        if behavior.objective_values[0]
        > baseline_exact_rate + _STRICT_IMPROVEMENT_MARGIN
    ]
    hard_gates = {
        **dict(probe_receipt["hard_gates"]),
        "all_incumbent_behaviors_retained": (
            len(challenge.shared_behavior_signatures)
            == int(grammar_delta["canonical_incumbent_program_count"])
        ),
        "evaluation_surface_identity_exact": True,
        "strict_objective_improvement": bool(strict_material),
    }
    qualified = all(hard_gates.values())
    body = {
        "status": "qualified" if qualified else "unqualified_executable_behavior_gate_failed",
        "evaluation_model_id": "source-bound-path-probes-v1",
        "evaluation_surface_sha256": evaluation_surface_sha256,
        "objective_names": list(_REPRESENTATION_OBJECTIVES),
        "strict_improvement_margin": _STRICT_IMPROVEMENT_MARGIN,
        "baseline_grammar_digest": grammar_delta["baseline_grammar"]["grammar_digest"],
        "challenger_grammar_digest": grammar_delta["challenger_grammar"]["grammar_digest"],
        "challenge": challenge.to_dict(),
        "qualified_behavior_count": len(strict_material) if qualified else 0,
        "hard_gates": hard_gates,
        "probe_receipt": probe_receipt,
        "repair_targets": [name for name, passed in hard_gates.items() if not passed],
        "future_settlement_use": False,
        "economic_or_return_evidence": False,
    }
    return {**body, "qualification_sha256": stable_sha256(body)}


def compile_strategy_security_representation_learning(
    raw_tournament: Mapping[str, Any], *, replay: Mapping[str, Any] | None = None,
    compiled_at: str | None = None,
) -> dict[str, Any]:
    """Compile supported representation deltas without activating a grammar."""

    tournament = _verified_tournament(raw_tournament)
    at = canonical_timestamp(
        compiled_at or str(tournament.get("evidence_as_of") or ""), "compiled_at"
    )
    gaps = [
        dict(row) for row in tournament.get("coverage_gaps") or ()
        if isinstance(row, Mapping)
    ]
    overlap_witnesses = [
        row for row in gaps
        if row.get("reason") == "overlapping_strategy_events_require_bundle_representation"
        and len(row.get("episode_sha256s") or ()) >= 2
    ]
    acquisition_gaps = [
        {
            "reason": str(row.get("reason") or "unknown"),
            "entity_id": str(row.get("entity_id") or ""),
            "episode_sha256s": sorted({
                str(value) for value in (
                    row.get("episode_sha256s") or [row.get("episode_sha256")]
                ) if value
            }),
        }
        for row in gaps
        if row.get("reason") != "overlapping_strategy_events_require_bundle_representation"
    ]
    conjectures: list[dict[str, Any]] = []
    if overlap_witnesses:
        (
            grammar_delta,
            baseline_grammar,
            baseline_enumeration,
            challenger_grammar,
            challenger_enumeration,
        ) = _path_grammar_delta()
        verified_replay = _verified_replay(replay, tournament) if replay is not None else None
        episode_order = {
            str(row["episode_sha256"]): (
                str(row.get("occurred_at") or ""), str(row["episode_sha256"]),
            )
            for row in (verified_replay or {}).get("episodes") or ()
            if isinstance(row, Mapping)
        }
        witness_rows = [
            {
                "entity_id": str(row.get("entity_id") or ""),
                "episode_sha256s": sorted(
                    map(str, row.get("episode_sha256s") or ()),
                    key=lambda episode_sha: episode_order.get(
                        episode_sha, ("", episode_sha),
                    ),
                ),
                "entry_start": str(row.get("entry_start") or ""),
                "exit_end": str(row.get("exit_end") or ""),
            }
            for row in overlap_witnesses
        ]
        witness_rows.sort(key=lambda row: (
            row["entry_start"], row["entity_id"], row["episode_sha256s"],
        ))
        consumed_episode_sha256s = sorted({
            episode_sha
            for row in witness_rows for episode_sha in row["episode_sha256s"]
        })
        identity = {
            "selection_tournament_sha256": tournament["tournament_sha256"],
            "revision_kind": "compose_connected_strategy_move_path",
            "baseline_grammar_digest": grammar_delta["baseline_grammar"]["grammar_digest"],
            "challenger_grammar_digest": grammar_delta["challenger_grammar"]["grammar_digest"],
            "full_typed_delta_sha256": grammar_delta["full_typed_delta_sha256"],
            "witnesses": witness_rows,
        }
        conjecture_id = (
            "strategy-security-grammar:connected-move-path:"
            f"{stable_sha256(identity)[:16]}"
        )
        qualification = (
            _qualify_same_epoch_behavior(
                grammar_delta=grammar_delta,
                baseline=baseline_grammar,
                baseline_enumeration=baseline_enumeration,
                challenger=challenger_grammar,
                challenger_enumeration=challenger_enumeration,
                tournament=tournament,
                replay=verified_replay,
                witnesses=witness_rows,
                conjecture_id=conjecture_id,
            )
            if replay is not None else {
                "status": "pending_replay_identity",
                "required_primitive": "ztare.strategy.challenge_representation",
                "future_settlement_use": False,
                "economic_or_return_evidence": False,
            }
        )
        behavior_qualified = qualification["status"] == "qualified"
        evaluation = {
            "mode": "paired_future_only_shadow",
            "activation_status": (
                "eligible_to_freeze" if behavior_qualified
                else "blocked_by_same_epoch_behavior_qualification"
            ),
            "not_before": at,
            "selection_tournament_sha256": tournament["tournament_sha256"],
            "selection_episode_sha256s": sorted({
                str(row.get("episode_sha256") or "")
                for row in tournament.get("security_outcomes") or ()
                if isinstance(row, Mapping) and row.get("episode_sha256")
            } | {
                episode_sha
                for row in witness_rows for episode_sha in row["episode_sha256s"]
            }),
            "eligible_path_rule": (
                "every constituent filing event must be later than not_before, absent from the "
                "selection episodes, bound to one historical security identity, and settled "
                "under the frozen daily factor-control execution contract"
            ),
            "comparison": [
                "untyped global-median control",
                "frozen isolated-event transaction-phenotype grammar",
                "one versioned connected-move-path grammar",
            ],
            "shared_execution_contract_sha256": stable_sha256(
                tournament.get("execution_contract") or {}
            ),
            "minimum_independent_blocks": max(
                _MIN_PROSPECTIVE_BLOCKS,
                int(tournament.get("minimum_independent_blocks") or 0),
            ),
            "power_analysis_required": True,
            "complete_model_episode_matrix_required": True,
            "multiplicity_family": "connected_strategy_move_path_v1",
            "success_condition": (
                "the path grammar lowers paired forecast error and raises after-cost paper-book "
                "active return versus both controls without weakening identity, factor, overlap, "
                "or multiplicity gates"
            ),
            "counterexample_rule": (
                "retain every future path for which composition adds no predictive or paper-economic "
                "value, changes only coverage, or fails a source or identity contract"
            ),
            "historical_retrofit_allowed": False,
            "automatic_grammar_activation": False,
        }
        body = {
            "schema": STRATEGY_SECURITY_GRAMMAR_CONJECTURE_SCHEMA,
            "conjecture_id": conjecture_id,
            "compiled_at": at,
            "status": (
                "same_epoch_behavior_qualified_awaiting_future_shadow"
                if behavior_qualified else
                "delta_compiled_behavior_unqualified"
                if replay is not None else
                "delta_compiled_awaiting_same_epoch_behavior_qualification"
            ),
            "trial_state": (
                "same_epoch_behavior_qualified" if behavior_qualified
                else "same_epoch_behavior_unqualified"
                if replay is not None else "delta_compiled"
            ),
            "trial_family_id": "strategy_security_representation",
            "revision_kind": "compose_connected_strategy_move_path",
            "conjecture": (
                "A connected sequence of management moves may carry decision-relevant information "
                "that isolated transaction phenotypes discard."
            ),
            "support_semantics": (
                "overlap witnesses justify testing a path representation; they provide no return edge"
            ),
            "support_path_count": len(witness_rows),
            "support_episode_count": sum(
                len(row["episode_sha256s"]) for row in witness_rows
            ),
            "support_entity_count": len({row["entity_id"] for row in witness_rows}),
            "counterexamples": witness_rows,
            "consumed_counterexample_receipts": [
                evidence_promotion_receipt(
                    from_ref=f"strategy-security-episode://{episode_sha}",
                    reason="used_to_author_connected_move_path_delta",
                )
                for episode_sha in consumed_episode_sha256s
            ],
            "grammar_delta": grammar_delta,
            "same_epoch_behavior_qualification": qualification,
            "governing_identity": {
                "job": "represent one connected same-issuer management-move path",
                "owner": "historical_strategy_representation_challenger",
                "lifecycle": [
                    "counterexample_supported", "future_shadow_evaluation", "rejected_or_reviewable",
                ],
                "authority": "research_challenger_only",
                "equality": (
                    "same issuer, ordered constituent episode hashes, and same connected event interval"
                ),
            },
            "future_evaluation_contract": evaluation,
            "promotion_boundary": (
                "a successful trial may change only the default grammar for future shadow forecasts; "
                "inconclusive evidence remains collecting and the incumbent grammar stays frozen"
            ),
            "auto_modifies_grammar": False,
            "security_ranking_use": False,
            "security_alpha_claim": False,
            "paper_policy_authority": False,
            "capital_authority": False,
        }
        trial_identity = {
            "baseline_grammar_digest": grammar_delta["baseline_grammar"]["grammar_digest"],
            "challenger_grammar_digest": grammar_delta["challenger_grammar"]["grammar_digest"],
            "full_typed_delta_sha256": grammar_delta["full_typed_delta_sha256"],
            "consumed_counterexample_sha256s": consumed_episode_sha256s,
            "ordered_path_witnesses": [
                {
                    "entity_id": row["entity_id"],
                    "episode_sha256s": row["episode_sha256s"],
                    "entry_start": row["entry_start"],
                    "exit_end": row["exit_end"],
                }
                for row in witness_rows
            ],
            "evaluation_surface_sha256": qualification.get(
                "evaluation_surface_sha256"
            ),
            "selection_cutoff": at,
            "target_observable_contract_sha256": stable_sha256({
                "target_metric_id": (
                    tournament.get("execution_contract") or {}
                ).get("return_target")
            }),
            "execution_contract_sha256": stable_sha256(
                tournament.get("execution_contract") or {}
            ),
            "trial_family_id": body["trial_family_id"],
        }
        body["trial_id"] = stable_sha256(trial_identity)
        body["trial_identity"] = trial_identity
        conjectures.append({**body, "conjecture_sha256": stable_sha256(body)})

    failed_joint_gate = (
        tournament.get("status") == "typed_policy_did_not_clear_both_controls"
    )
    body = {
        "schema": STRATEGY_SECURITY_REPRESENTATION_LEARNING_SCHEMA,
        "compiled_at": at,
        "selection_tournament_sha256": tournament["tournament_sha256"],
        "current_representation_status": (
            "rejected_for_security_selection_under_current_evidence"
            if failed_joint_gate else "unassessed_for_security_selection"
        ),
        "representation_residual": (
            "isolated events cannot encode connected same-issuer move paths"
            if overlap_witnesses else None
        ),
        "generic_underperformance_selects_grammar_delta": False,
        "conjecture_count": len(conjectures),
        "conjectures": conjectures,
        "acquisition_gap_count": len(acquisition_gaps),
        "acquisition_gaps": acquisition_gaps,
        "routing_rule": (
            "identity and factor-history failures route to acquisition; overlap can support a "
            "composition challenger; aggregate underperformance alone cannot invent an axis"
        ),
        "next_activation": (
            "Keep the current phenotype out of security ranking and repair the failed executable "
            "path-behavior gate before opening a shadow trial."
            if conjectures and conjectures[0]["trial_state"] == "same_epoch_behavior_unqualified"
            else "Keep the current phenotype out of security ranking and freeze only a qualified "
            "path grammar into later paired shadow blocks."
            if conjectures else
            "Keep the current phenotype out of security ranking and acquire a typed counterexample "
            "before proposing another grammar."
        ),
        "auto_modifies_grammar": False,
        "security_ranking_use": False,
        "security_alpha_claim": False,
        "paper_policy_authority": False,
        "capital_authority": False,
    }
    return {**body, "learning_sha256": stable_sha256(body)}


__all__ = [
    "STRATEGY_SECURITY_GRAMMAR_CONJECTURE_SCHEMA",
    "STRATEGY_SECURITY_REPRESENTATION_LEARNING_SCHEMA",
    "compile_strategy_security_representation_learning",
]
