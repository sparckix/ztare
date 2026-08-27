"""Compile relational affordances into exact-scope sparse recall proposals.

The source memory owns a palette/D4-quotiented pose-to-motion relation and a
goal-role identity. The target proposal owns a current scene, its first
decision seam, and one exact recall scope. Keeping these identities separate
lets the memory survive target presentation changes while every consumption
remains bound to the observation that generated the decision.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

from ztare.common.wake_sleep_credit_router import (
    MemoryAcquisitionProvenance,
    MemoryCandidate,
    MemoryScope,
    RecallReceipt,
    WakeSleepCreditState,
    select_sparse_memories,
)
from ztare.worldmodel.relational_affordance import (
    AffordanceFrontier,
    GoalPrototype,
    PoseMotionRelation,
    RelationalScene,
    canonical_frontier_key,
    compile_relational_affordance_frontier,
    discover_pose_motion_relations,
    extract_relational_scene,
    extract_settled_residual_scene,
    learn_goal_prototype,
    scan_oriented_tokens,
)


Point = tuple[int, int]
Direction = str
_DIRECTION_BY_UNIT = {
    (-1, 0): "up",
    (1, 0): "down",
    (0, -1): "left",
    (0, 1): "right",
}
_UNIT_BY_DIRECTION = {
    direction: vector for vector, direction in _DIRECTION_BY_UNIT.items()
}


def _sha(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _direction(source: Point, target: Point, *, stride: int) -> Direction:
    dy = target[0] - source[0]
    dx = target[1] - source[1]
    if stride <= 0 or dy % stride or dx % stride:
        raise ValueError("decision edge does not respect scene stride")
    unit = (dy // stride, dx // stride)
    if unit not in _DIRECTION_BY_UNIT:
        raise ValueError("decision edge is not one cardinal scene step")
    return _DIRECTION_BY_UNIT[unit]


def _canonical_refs(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(sorted({
        str(value).strip() for value in values if str(value).strip()
    }))


@dataclass(frozen=True)
class DecisionBranch:
    direction: Direction
    action: int
    contact_kind: str
    risk_rank: int
    total_action_count: int
    remaining_action_count: int

    def to_receipt(self) -> dict[str, Any]:
        return {
            "direction": self.direction,
            "action": self.action,
            "contact_kind": self.contact_kind,
            "risk_rank": self.risk_rank,
            "total_action_count": self.total_action_count,
            "remaining_action_count": self.remaining_action_count,
        }


@dataclass(frozen=True)
class RelationalDecisionSeam:
    approach_directions: tuple[Direction, ...]
    approach_actions: tuple[int, ...]
    branches: tuple[DecisionBranch, ...]
    selected_direction: Direction
    selected_action: int
    selected_contact_kind: str
    frontier_sha256: str
    budget: int

    @property
    def approach_action_count(self) -> int:
        return len(self.approach_actions)

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": "ztare-relational-decision-seam-v1",
            "approach_directions": list(self.approach_directions),
            "approach_actions": list(self.approach_actions),
            "approach_action_count": self.approach_action_count,
            "branches": [branch.to_receipt() for branch in self.branches],
            "selected_direction": self.selected_direction,
            "selected_action": self.selected_action,
            "selected_contact_kind": self.selected_contact_kind,
            "frontier_sha256": self.frontier_sha256,
            "budget": self.budget,
        }
        return {**payload, "sha256": _sha(payload)}


def discover_relational_decision_seam(
    scene: RelationalScene,
    *,
    budget: int,
) -> tuple[RelationalDecisionSeam, AffordanceFrontier]:
    """Find the first divergence shared by all budget-feasible goal routes."""

    root = compile_relational_affordance_frontier(
        scene,
        prefix=(scene.start,),
        budget=int(budget),
    )
    routes = tuple(
        row.route for row in root.candidates if row.budget_feasible
    )
    if len(routes) < 2:
        raise ValueError("scene has no competing budget-feasible routes")
    common = []
    for index in range(min(len(route) for route in routes)):
        point = routes[0][index]
        if any(route[index] != point for route in routes[1:]):
            break
        common.append(point)
    prefix = tuple(common)
    if not prefix or any(len(route) <= len(prefix) for route in routes):
        raise ValueError("goal routes expose no proper decision seam")
    frontier = compile_relational_affordance_frontier(
        scene,
        prefix=prefix,
        budget=int(budget),
    )
    action_by_direction = dict(scene.action_by_direction)
    approach_directions = tuple(
        _direction(source, target, stride=scene.stride)
        for source, target in zip(prefix, prefix[1:])
    )
    approach_actions = tuple(
        int(action_by_direction[direction])
        for direction in approach_directions
    )
    best_by_direction = {}
    for candidate in frontier.candidates:
        direction = _direction(
            prefix[-1],
            candidate.route[len(prefix)],
            stride=scene.stride,
        )
        branch = DecisionBranch(
            direction=direction,
            action=int(action_by_direction[direction]),
            contact_kind=candidate.contact_kind,
            risk_rank=candidate.risk_rank,
            total_action_count=candidate.action_count,
            remaining_action_count=(
                candidate.action_count - (len(prefix) - 1)
            ),
        )
        incumbent = best_by_direction.get(direction)
        if incumbent is None or (
            branch.risk_rank,
            branch.total_action_count,
            branch.contact_kind,
        ) < (
            incumbent.risk_rank,
            incumbent.total_action_count,
            incumbent.contact_kind,
        ):
            best_by_direction[direction] = branch
    if len(best_by_direction) < 2:
        raise ValueError("decision seam does not expose competing branches")
    selected_direction = frontier.selected_direction
    selected_action = frontier.selected_action
    if selected_direction is None or selected_action is None:
        raise ValueError("decision seam has no selected intervention")
    seam = RelationalDecisionSeam(
        approach_directions=approach_directions,
        approach_actions=approach_actions,
        branches=tuple(sorted(
            best_by_direction.values(),
            key=lambda row: row.direction,
        )),
        selected_direction=selected_direction,
        selected_action=int(selected_action),
        selected_contact_kind=frontier.selected.contact_kind,
        frontier_sha256=canonical_frontier_key(frontier),
        budget=int(budget),
    )
    return seam, frontier


@dataclass(frozen=True)
class RelationalAffordanceMemoryRevision:
    relation: PoseMotionRelation
    goal_kind: str
    goal_size: int
    source_support_refs: tuple[str, ...]
    boundary_support_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_support_refs",
            _canonical_refs(self.source_support_refs),
        )
        object.__setattr__(
            self,
            "boundary_support_refs",
            _canonical_refs(self.boundary_support_refs),
        )
        if not self.relation.passed:
            raise ValueError("memory revision requires a supported relation")
        if not self.source_support_refs:
            raise ValueError("memory revision requires source support")
        if set(self.boundary_support_refs) - set(self.source_support_refs):
            raise ValueError("boundary support must belong to source support")

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": "ztare-relational-affordance-memory-revision-v1",
            "relation": self.relation.semantic_receipt(),
            "goal_role": {
                "kind": self.goal_kind,
                "size": self.goal_size,
            },
            "source_support_refs": list(self.source_support_refs),
            "boundary_support_refs": list(self.boundary_support_refs),
        }
        return {**payload, "sha256": _sha(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


def _goal_from_memory(
    memory: RelationalAffordanceMemoryRevision,
) -> GoalPrototype:
    # The portable boundary-goal identity is structural.  Its literal source
    # palette value is evidence, not target-consumption authority.
    return GoalPrototype(
        kind=memory.goal_kind,
        size=memory.goal_size,
        uniform_value=-1,
    )


def _target_entities(
    grid: Sequence[Sequence[int]],
    memory: RelationalAffordanceMemoryRevision,
) -> tuple[tuple[Point, Direction], ...]:
    relation = memory.relation
    tokens = tuple(
        token for token in scan_oriented_tokens(
            grid,
            expected_size=relation.token_size,
        )
        if token.structural_key == relation.structural_key
    )
    controlled_palette = (
        relation.controlled_body_value,
        relation.controlled_marker_value,
    )
    return tuple(sorted(
        (token.origin, token.bearing)
        for token in tokens
        if token.palette != controlled_palette
    ))


@dataclass(frozen=True)
class ActiveRelationalWorkingRevision:
    """One observation-bound action while target transport remains active."""

    memory_revision: RelationalAffordanceMemoryRevision
    scope: MemoryScope
    observation_sha256: str
    predecessor_revision_sha256: str
    remaining_budget: int
    frontier_sha256: str
    selected_direction: Direction
    selected_action: int
    selected_route: tuple[Point, ...]
    selected_contact_kind: str
    target_entities: tuple[tuple[Point, Direction], ...]
    projected_target_successors: tuple[
        tuple[Point, Direction, Point], ...
    ]
    tests_target_transport: bool

    def __post_init__(self) -> None:
        if self.scope.context_sha256 != self.observation_sha256:
            raise ValueError("working revision scope does not bind observation")
        if self.remaining_budget <= 0:
            raise ValueError("working revision requires positive remaining budget")
        if not self.target_entities:
            raise ValueError("active working revision requires a target entity")
        if len(self.selected_route) < 2:
            raise ValueError("active working revision requires one next edge")

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": "ztare-active-relational-working-revision-v1",
            "source_memory_sha256": self.memory_revision.sha256,
            "scope": self.scope.to_receipt(),
            "scope_sha256": self.scope.sha256,
            "observation_sha256": self.observation_sha256,
            "predecessor_revision_sha256": self.predecessor_revision_sha256,
            "remaining_budget": self.remaining_budget,
            "frontier_sha256": self.frontier_sha256,
            "current_action": {
                "direction": self.selected_direction,
                "action": self.selected_action,
                "contact_kind": self.selected_contact_kind,
            },
            "selected_route_action_count": len(self.selected_route) - 1,
            "target_entities": [
                {"origin": list(origin), "bearing": bearing}
                for origin, bearing in self.target_entities
            ],
            "projected_target_successors": [
                {
                    "source": list(source),
                    "bearing": bearing,
                    "projected_successor": list(successor),
                }
                for source, bearing, successor
                in self.projected_target_successors
            ],
            "tests_target_transport": self.tests_target_transport,
            "authority": (
                "exact current observation and remaining budget only; "
                "one action; score the successor before reuse"
            ),
        }
        return {**payload, "sha256": _sha(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])

    def digest_payload(self) -> dict[str, Any]:
        receipt = self.to_receipt()
        return {
            "schema": "ztare-relational-working-action-v1",
            "revision_schema": receipt["schema"],
            "working_revision_sha256": receipt["sha256"],
            "source_memory_sha256": self.memory_revision.sha256,
            "observation_sha256": self.observation_sha256,
            "scope_sha256": self.scope.sha256,
            "remaining_budget": self.remaining_budget,
            "current_action": dict(receipt["current_action"]),
            "tests_target_transport": self.tests_target_transport,
            "guard": receipt["authority"],
            "refusal": "no future action suffix is authorized",
        }


@dataclass(frozen=True)
class TargetTransportSettlement:
    """Prediction error for one transition under active target authority."""

    active_revision_sha256: str
    source_memory_sha256: str
    source_observation_sha256: str
    successor_observation_sha256: str
    selected_action: int
    tested_target_transport: bool
    projected_target_successors: tuple[
        tuple[Point, Direction, Point], ...
    ]
    observed_target_entities: tuple[tuple[Point, Direction], ...]
    status: str
    reason: str

    def __post_init__(self) -> None:
        allowed = {
            "not_tested",
            "target_transport_supported",
            "target_transport_refuted",
        }
        if self.status not in allowed:
            raise ValueError(f"unknown target settlement status: {self.status}")
        if self.tested_target_transport != (self.status != "not_tested"):
            raise ValueError("settlement test identity conflicts with status")

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": "ztare-target-transport-settlement-v1",
            "active_revision_sha256": self.active_revision_sha256,
            "source_memory_sha256": self.source_memory_sha256,
            "source_observation_sha256": self.source_observation_sha256,
            "successor_observation_sha256": self.successor_observation_sha256,
            "selected_action": self.selected_action,
            "tested_target_transport": self.tested_target_transport,
            "projected_target_successors": [
                {
                    "source": list(source),
                    "bearing": bearing,
                    "projected_successor": list(successor),
                }
                for source, bearing, successor
                in self.projected_target_successors
            ],
            "observed_target_entities": [
                {"origin": list(origin), "bearing": bearing}
                for origin, bearing in self.observed_target_entities
            ],
            "status": self.status,
            "reason": self.reason,
        }
        return {**payload, "sha256": _sha(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])


@dataclass(frozen=True)
class SettledResidualWorkingRevision:
    """One observation-bound navigation action after target refutation."""

    memory_revision: RelationalAffordanceMemoryRevision
    scope: MemoryScope
    observation_sha256: str
    predecessor_revision_sha256: str
    settlement_sha256: str
    remaining_budget: int
    frontier_sha256: str
    selected_direction: Direction
    selected_action: int
    selected_route: tuple[Point, ...]

    def __post_init__(self) -> None:
        if self.scope.context_sha256 != self.observation_sha256:
            raise ValueError("residual revision scope does not bind observation")
        if self.remaining_budget <= 0:
            raise ValueError("residual revision requires positive remaining budget")
        if len(self.selected_route) < 2:
            raise ValueError("residual revision requires one next edge")
        if not self.settlement_sha256:
            raise ValueError("residual revision requires target settlement")

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": "ztare-settled-residual-working-revision-v1",
            "source_memory_sha256": self.memory_revision.sha256,
            "scope": self.scope.to_receipt(),
            "scope_sha256": self.scope.sha256,
            "observation_sha256": self.observation_sha256,
            "predecessor_revision_sha256": self.predecessor_revision_sha256,
            "settlement_sha256": self.settlement_sha256,
            "remaining_budget": self.remaining_budget,
            "frontier_sha256": self.frontier_sha256,
            "current_action": {
                "direction": self.selected_direction,
                "action": self.selected_action,
                "contact_kind": "none",
            },
            "selected_route_action_count": len(self.selected_route) - 1,
            "authority": (
                "target transport is discharged; exact current observation "
                "and remaining budget authorize one residual action"
            ),
        }
        return {**payload, "sha256": _sha(payload)}

    @property
    def sha256(self) -> str:
        return str(self.to_receipt()["sha256"])

    def digest_payload(self) -> dict[str, Any]:
        receipt = self.to_receipt()
        return {
            "schema": "ztare-relational-working-action-v1",
            "revision_schema": receipt["schema"],
            "working_revision_sha256": receipt["sha256"],
            "source_memory_sha256": self.memory_revision.sha256,
            "observation_sha256": self.observation_sha256,
            "scope_sha256": self.scope.sha256,
            "remaining_budget": self.remaining_budget,
            "current_action": dict(receipt["current_action"]),
            "settlement_sha256": self.settlement_sha256,
            "guard": receipt["authority"],
            "refusal": "discharged target motion cannot regain authority",
        }


RelationalWorkingRevision = (
    ActiveRelationalWorkingRevision | SettledResidualWorkingRevision
)


@dataclass(frozen=True)
class RelationalWorkingAdvance:
    predecessor_revision_sha256: str
    settlement: TargetTransportSettlement | None
    revision: RelationalWorkingRevision

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": "ztare-relational-working-advance-v1",
            "predecessor_revision_sha256": self.predecessor_revision_sha256,
            "settlement": (
                self.settlement.to_receipt()
                if self.settlement is not None else None
            ),
            "revision": self.revision.to_receipt(),
        }
        return {**payload, "sha256": _sha(payload)}


def compile_active_relational_working_revision(
    memory_revision: RelationalAffordanceMemoryRevision,
    *,
    target_grid: Sequence[Sequence[int]],
    observation_sha256: str,
    scope: MemoryScope,
    remaining_budget: int,
    predecessor_revision_sha256: str = "",
) -> ActiveRelationalWorkingRevision:
    """Recompute one active action from the exact current observation."""

    if scope.context_sha256 != str(observation_sha256):
        raise ValueError("working revision scope does not bind observation")
    scene = extract_relational_scene(
        target_grid,
        relation=memory_revision.relation,
        goal=_goal_from_memory(memory_revision),
    )
    frontier = compile_relational_affordance_frontier(
        scene,
        prefix=(scene.start,),
        budget=int(remaining_budget),
    )
    direction = frontier.selected_direction
    action = frontier.selected_action
    if direction is None or action is None:
        raise ValueError("current relational frontier has no next action")
    projections = tuple(
        (
            origin,
            bearing,
            (
                origin[0] + _UNIT_BY_DIRECTION[bearing][0] * scene.stride,
                origin[1] + _UNIT_BY_DIRECTION[bearing][1] * scene.stride,
            ),
        )
        for origin, bearing in scene.oriented_entities
    )
    next_point = frontier.selected.route[1]
    return ActiveRelationalWorkingRevision(
        memory_revision=memory_revision,
        scope=scope,
        observation_sha256=str(observation_sha256),
        predecessor_revision_sha256=str(predecessor_revision_sha256),
        remaining_budget=int(remaining_budget),
        frontier_sha256=canonical_frontier_key(frontier),
        selected_direction=direction,
        selected_action=int(action),
        selected_route=frontier.selected.route,
        selected_contact_kind=frontier.selected.contact_kind,
        target_entities=scene.oriented_entities,
        projected_target_successors=projections,
        tests_target_transport=next_point in {
            origin for origin, _bearing in scene.oriented_entities
        },
    )


def _compile_settled_residual_working_revision(
    memory_revision: RelationalAffordanceMemoryRevision,
    *,
    target_grid: Sequence[Sequence[int]],
    observation_sha256: str,
    scope: MemoryScope,
    remaining_budget: int,
    predecessor_revision_sha256: str,
    settlement_sha256: str,
) -> SettledResidualWorkingRevision:
    scene = extract_settled_residual_scene(
        target_grid,
        relation=memory_revision.relation,
        goal=_goal_from_memory(memory_revision),
    )
    frontier = compile_relational_affordance_frontier(
        scene,
        prefix=(scene.start,),
        budget=int(remaining_budget),
    )
    direction = frontier.selected_direction
    action = frontier.selected_action
    if direction is None or action is None:
        raise ValueError("current residual frontier has no next action")
    return SettledResidualWorkingRevision(
        memory_revision=memory_revision,
        scope=scope,
        observation_sha256=str(observation_sha256),
        predecessor_revision_sha256=str(predecessor_revision_sha256),
        settlement_sha256=str(settlement_sha256),
        remaining_budget=int(remaining_budget),
        frontier_sha256=canonical_frontier_key(frontier),
        selected_direction=direction,
        selected_action=int(action),
        selected_route=frontier.selected.route,
    )


def advance_relational_working_revision(
    revision: RelationalWorkingRevision,
    *,
    successor_grid: Sequence[Sequence[int]],
    successor_observation_sha256: str,
    successor_scope: MemoryScope,
    remaining_budget: int,
    settlement: TargetTransportSettlement | None = None,
) -> RelationalWorkingAdvance:
    """Score one successor and compile exactly one next-state action."""

    if successor_scope.context_sha256 != str(successor_observation_sha256):
        raise ValueError("successor scope does not bind successor observation")
    if isinstance(revision, SettledResidualWorkingRevision):
        if settlement is not None and settlement.sha256 != revision.settlement_sha256:
            raise ValueError("residual settlement identity drifted")
        next_revision = _compile_settled_residual_working_revision(
            revision.memory_revision,
            target_grid=successor_grid,
            observation_sha256=successor_observation_sha256,
            scope=successor_scope,
            remaining_budget=remaining_budget,
            predecessor_revision_sha256=revision.sha256,
            settlement_sha256=revision.settlement_sha256,
        )
        return RelationalWorkingAdvance(
            predecessor_revision_sha256=revision.sha256,
            settlement=None,
            revision=next_revision,
        )

    observed = _target_entities(successor_grid, revision.memory_revision)
    expected = {
        (successor, bearing)
        for _source, bearing, successor
        in revision.projected_target_successors
    }
    actual = set(observed)
    if not revision.tests_target_transport:
        status = "not_tested"
        reason = "selected action did not enter a target-occupied node"
    elif actual == expected:
        status = "target_transport_supported"
        reason = "observed target successors equal relation projections"
    elif not actual:
        status = "target_transport_refuted"
        reason = "target absent after direct contact"
    else:
        status = "target_transport_refuted"
        reason = "observed target successors differ from relation projections"
    transition_settlement = TargetTransportSettlement(
        active_revision_sha256=revision.sha256,
        source_memory_sha256=revision.memory_revision.sha256,
        source_observation_sha256=revision.observation_sha256,
        successor_observation_sha256=str(successor_observation_sha256),
        selected_action=revision.selected_action,
        tested_target_transport=revision.tests_target_transport,
        projected_target_successors=revision.projected_target_successors,
        observed_target_entities=observed,
        status=status,
        reason=reason,
    )
    if status == "target_transport_refuted" and not observed:
        next_revision: RelationalWorkingRevision = (
            _compile_settled_residual_working_revision(
                revision.memory_revision,
                target_grid=successor_grid,
                observation_sha256=successor_observation_sha256,
                scope=successor_scope,
                remaining_budget=remaining_budget,
                predecessor_revision_sha256=revision.sha256,
                settlement_sha256=transition_settlement.sha256,
            )
        )
    elif status in {"not_tested", "target_transport_supported"}:
        next_revision = compile_active_relational_working_revision(
            revision.memory_revision,
            target_grid=successor_grid,
            observation_sha256=successor_observation_sha256,
            scope=successor_scope,
            remaining_budget=remaining_budget,
            predecessor_revision_sha256=revision.sha256,
        )
    else:
        raise ValueError(
            "refuted target transport with a surviving target requires a new "
            "target model before action authority can continue"
        )
    return RelationalWorkingAdvance(
        predecessor_revision_sha256=revision.sha256,
        settlement=transition_settlement,
        revision=next_revision,
    )


@dataclass(frozen=True)
class RelationalAffordanceRecallProposal:
    memory_revision: RelationalAffordanceMemoryRevision
    scope: MemoryScope
    target_observation_sha256: str
    target_entity_bearings: tuple[Direction, ...]
    decision_seam: RelationalDecisionSeam
    predicted_decision_delta: float
    retrieval_cost: float
    primitive_action_cost: float
    acquisition_provenance: MemoryAcquisitionProvenance | None = None

    def __post_init__(self) -> None:
        if self.scope.context_sha256 != self.target_observation_sha256:
            raise ValueError("proposal scope does not bind target observation")
        if not self.target_entity_bearings:
            raise ValueError("proposal requires a transported target entity")

    def digest_payload(self) -> dict[str, Any]:
        return {
            "schema": "ztare-autonomous-relational-affordance-recall-v1",
            "memory_revision": self.memory_revision.to_receipt(),
            "scope": self.scope.to_receipt(),
            "scope_sha256": self.scope.sha256,
            "target_compatibility": {
                "observation_sha256": self.target_observation_sha256,
                "frontier_sha256": self.decision_seam.frontier_sha256,
                "matching_entity_count": len(self.target_entity_bearings),
                "transported_entity_bearings": list(
                    self.target_entity_bearings
                ),
                "status": "source_supported_target_proposal",
            },
            "decision_seam": self.decision_seam.to_receipt(),
            "active_uncertainties": [
                "target entity dynamics and contact outcome remain unsettled"
            ],
            "guard": (
                "consume only under the exact scope and frontier identity; "
                "recompute after any observed transition"
            ),
            "refusal": (
                "source memory supplies no target contact outcome or future "
                "action suffix; current-scene planning owns the approach and "
                "branch intervention"
            ),
        }

    @property
    def sha256(self) -> str:
        return _sha(self.digest_payload())

    def to_memory_candidate(self) -> MemoryCandidate:
        relation = self.memory_revision.relation
        return MemoryCandidate(
            provider_id="relational_affordance_recall_compiler_v1",
            memory_revision_sha256=self.memory_revision.sha256,
            scope=self.scope,
            predicted_decision_delta=self.predicted_decision_delta,
            retrieval_cost=self.retrieval_cost,
            primitive_action_cost=self.primitive_action_cost,
            prompt_token_cost=0,
            authority_score=float(relation.support_count),
            actionability_score=1.0,
            recency_score=1.0,
            guard_features=(
                f"frontier:{self.decision_seam.frontier_sha256}",
                f"budget:{self.decision_seam.budget}",
                f"entity_count:{len(self.target_entity_bearings)}",
                "exact_scope",
                "route_divergence",
            ),
            semantic_features=(
                "oriented_token",
                "marker_bearing",
                "motion_cone",
                "relative_contact",
                "viability_route",
                "decision_seam",
            ),
            support_refs=self.memory_revision.source_support_refs,
            boundary_support_refs=(
                self.memory_revision.boundary_support_refs
            ),
            content_ref=f"relational_affordance_proposal:{self.sha256}",
            acquisition_provenance=self.acquisition_provenance,
        )

    def to_receipt(self) -> dict[str, Any]:
        candidate = self.to_memory_candidate()
        payload = {
            "schema": "ztare-relational-affordance-recall-proposal-v1",
            "proposal_sha256": self.sha256,
            "digest": self.digest_payload(),
            "candidate": candidate.to_receipt(),
        }
        return {**payload, "sha256": _sha(payload)}


def compile_relational_affordance_recall(
    source_rows: Sequence[Any],
    *,
    boundary_source_grid: Sequence[Sequence[int]],
    boundary_action: int,
    target_grid: Sequence[Sequence[int]],
    target_observation_sha256: str,
    scope: MemoryScope,
    budget: int,
    source_support_refs: Sequence[str],
    boundary_support_refs: Sequence[str],
    predicted_decision_delta: float,
    retrieval_cost: float,
    primitive_action_cost: float,
    acquisition_provenance: MemoryAcquisitionProvenance | None = None,
) -> RelationalAffordanceRecallProposal:
    """Compile raw evidence and a current grid into one recall proposal."""

    relations = discover_pose_motion_relations(source_rows)
    if len(relations) != 1:
        raise ValueError("source must induce exactly one pose-motion relation")
    relation = relations[0]
    goal = learn_goal_prototype(
        boundary_source_grid,
        boundary_action=int(boundary_action),
        relation=relation,
    )
    scene = extract_relational_scene(
        target_grid,
        relation=relation,
        goal=goal,
    )
    seam, _frontier = discover_relational_decision_seam(
        scene,
        budget=int(budget),
    )
    memory_revision = RelationalAffordanceMemoryRevision(
        relation=relation,
        goal_kind=goal.kind,
        goal_size=goal.size,
        source_support_refs=tuple(source_support_refs),
        boundary_support_refs=tuple(boundary_support_refs),
    )
    return RelationalAffordanceRecallProposal(
        memory_revision=memory_revision,
        scope=scope,
        target_observation_sha256=str(target_observation_sha256),
        target_entity_bearings=tuple(
            bearing for _origin, bearing in scene.oriented_entities
        ),
        decision_seam=seam,
        predicted_decision_delta=float(predicted_decision_delta),
        retrieval_cost=float(retrieval_cost),
        primitive_action_cost=float(primitive_action_cost),
        acquisition_provenance=acquisition_provenance,
    )


@dataclass(frozen=True)
class SelectedRelationalAffordanceRecall:
    proposal: RelationalAffordanceRecallProposal
    recall: RecallReceipt
    digest: Mapping[str, Any] | None

    @property
    def selected(self) -> bool:
        return self.digest is not None

    def to_receipt(self) -> dict[str, Any]:
        payload = {
            "schema": "ztare-selected-relational-affordance-recall-v1",
            "selected": self.selected,
            "proposal_sha256": self.proposal.sha256,
            "recall": self.recall.to_receipt(),
            "digest": dict(self.digest) if self.digest is not None else None,
        }
        return {**payload, "sha256": _sha(payload)}


def select_relational_affordance_recall(
    proposal: RelationalAffordanceRecallProposal,
    state: WakeSleepCreditState,
    *,
    consumption_scope: MemoryScope,
    max_prompt_tokens: int | None = None,
) -> SelectedRelationalAffordanceRecall:
    """Route one proposal through the shared calibrated sparse selector."""

    candidate = proposal.to_memory_candidate()
    recall = select_sparse_memories(
        state,
        (candidate,),
        scope=consumption_scope,
        max_items=1,
        max_prompt_tokens=max_prompt_tokens,
    )
    selected = any(
        row.memory_revision_sha256 == candidate.memory_revision_sha256
        for row in recall.selections
    )
    digest = None
    if selected:
        digest = {
            **proposal.digest_payload(),
            "selection": {
                "recall_sha256": recall.sha256,
                "memory_key": candidate.key,
                "direct_injection_limit": 1,
            },
        }
    return SelectedRelationalAffordanceRecall(
        proposal=proposal,
        recall=recall,
        digest=digest,
    )


__all__ = [
    "ActiveRelationalWorkingRevision",
    "DecisionBranch",
    "RelationalAffordanceMemoryRevision",
    "RelationalAffordanceRecallProposal",
    "RelationalDecisionSeam",
    "RelationalWorkingAdvance",
    "RelationalWorkingRevision",
    "SelectedRelationalAffordanceRecall",
    "SettledResidualWorkingRevision",
    "TargetTransportSettlement",
    "advance_relational_working_revision",
    "compile_active_relational_working_revision",
    "compile_relational_affordance_recall",
    "discover_relational_decision_seam",
    "select_relational_affordance_recall",
]
