"""Palette-quotiented oriented-token relations and viability frontiers.

The object owned here is a relation:

    edge-marker bearing -> witnessed motion bearing

Its identity quotients palette names and D4 presentation while retaining the
cardinal bearing as a covariant state coordinate.  A source-controlled token
can therefore teach a motion cone that is proposed for a structurally matching
target token with a different palette. Target dynamics retain authority over
whether that proposal survives.

The route compiler consumes only a finite scene graph plus that proposed cone.
It distinguishes relative contact classes and prefers a budget-feasible route
that avoids closing head-on exposure when a non-closing alternative exists.
It never assigns a target-specific semantic role or a contact outcome.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import itertools
import json
from typing import Any, Iterable, Mapping, Sequence

from ztare.worldmodel.object_roles import _components
from ztare.worldmodel.transition_identity import authoritative_boundary


Grid = tuple[tuple[int, ...], ...]
Point = tuple[int, int]
Direction = str

_DIRECTION_VECTORS: dict[Direction, Point] = {
    "up": (-1, 0),
    "down": (1, 0),
    "left": (0, -1),
    "right": (0, 1),
}
_VECTOR_DIRECTIONS = {value: key for key, value in _DIRECTION_VECTORS.items()}
_CONTACT_RISK = {
    "none": 0,
    "rear": 1,
    "transverse": 1,
    "head_on": 2,
}


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _direction(dy: int, dx: int) -> Direction | None:
    if dy == 0 and dx == 0:
        return None
    if dy != 0 and dx != 0:
        return None
    unit = (
        (0 if dy == 0 else (1 if dy > 0 else -1)),
        (0 if dx == 0 else (1 if dx > 0 else -1)),
    )
    return _VECTOR_DIRECTIONS.get(unit)


def _role_shape_variants(role_shape: Sequence[tuple[int, int, str]]):
    variants = set()
    for swap in (False, True):
        for sy in (-1, 1):
            for sx in (-1, 1):
                transformed = []
                for y, x, role in role_shape:
                    ty, tx = (x, y) if swap else (y, x)
                    transformed.append((sy * ty, sx * tx, str(role)))
                min_y = min(y for y, _x, _role in transformed)
                min_x = min(x for _y, x, _role in transformed)
                variants.add(tuple(sorted(
                    (y - min_y, x - min_x, role)
                    for y, x, role in transformed
                )))
    return tuple(sorted(variants))


@dataclass(frozen=True)
class OrientedToken:
    origin: Point
    size: int
    body_value: int
    marker_value: int
    bearing: Direction
    structural_key: tuple[tuple[int, int, str], ...]

    @property
    def palette(self) -> tuple[int, int]:
        return (self.body_value, self.marker_value)

    def semantic_receipt(self) -> dict[str, Any]:
        return {
            "kind": "palette_quotiented_oriented_token_v1",
            "origin": list(self.origin),
            "size": self.size,
            "bearing": self.bearing,
            "structural_key": [list(row) for row in self.structural_key],
        }

    def evidence_receipt(self) -> dict[str, Any]:
        return {
            **self.semantic_receipt(),
            "body_value": self.body_value,
            "marker_value": self.marker_value,
        }


def scan_oriented_tokens(
    grid: Sequence[Sequence[int]],
    *,
    expected_size: int | None = None,
) -> tuple[OrientedToken, ...]:
    """Find square body+edge-marker components without fixing palette names."""

    colors = sorted({int(value) for row in grid for value in row})
    found: dict[tuple, OrientedToken] = {}
    for first, second in itertools.combinations(colors, 2):
        for component in _components(grid, {first, second}):
            if not component:
                continue
            y0 = min(y for y, _x in component)
            x0 = min(x for _y, x in component)
            height = 1 + max(y for y, _x in component) - y0
            width = 1 + max(x for _y, x in component) - x0
            if height != width or height < 3 or height % 2 == 0:
                continue
            if expected_size is not None and height != expected_size:
                continue
            if len(component) != height * width:
                continue
            counts = Counter(int(grid[y][x]) for y, x in component)
            if sorted(counts.values()) != [1, height * width - 1]:
                continue
            marker = next(value for value, count in counts.items() if count == 1)
            body = next(
                value for value, count in counts.items()
                if count == height * width - 1
            )
            marker_y, marker_x = next(
                (y - y0, x - x0)
                for y, x in component
                if int(grid[y][x]) == marker
            )
            middle = height // 2
            bearing = {
                (0, middle): "up",
                (height - 1, middle): "down",
                (middle, 0): "left",
                (middle, width - 1): "right",
            }.get((marker_y, marker_x))
            if bearing is None:
                continue
            role_shape = tuple(sorted(
                (
                    y - y0,
                    x - x0,
                    "marker" if int(grid[y][x]) == marker else "body",
                )
                for y, x in component
            ))
            structural_key = _role_shape_variants(role_shape)[0]
            token = OrientedToken(
                origin=(y0, x0),
                size=height,
                body_value=body,
                marker_value=marker,
                bearing=bearing,
                structural_key=structural_key,
            )
            found[(token.origin, token.palette, token.structural_key)] = token
    return tuple(sorted(
        found.values(),
        key=lambda row: (row.origin, row.palette, row.bearing),
    ))


def _uniform_region(
    grid: Sequence[Sequence[int]],
    y0: int,
    x0: int,
    height: int,
    width: int,
) -> int | None:
    if y0 < 0 or x0 < 0:
        return None
    if y0 + height > len(grid) or x0 + width > len(grid[0]):
        return None
    values = {
        int(grid[y][x])
        for y in range(y0, y0 + height)
        for x in range(x0, x0 + width)
    }
    return next(iter(values)) if len(values) == 1 else None


def _between_region(
    source: Point,
    target: Point,
    *,
    size: int,
) -> tuple[int, int, int, int] | None:
    sy, sx = source
    ty, tx = target
    if sy == ty and sx != tx:
        left = min(sx, tx)
        gap = abs(tx - sx) - size
        return (sy, left + size, size, gap) if gap > 0 else None
    if sx == tx and sy != ty:
        top = min(sy, ty)
        gap = abs(ty - sy) - size
        return (top + size, sx, gap, size) if gap > 0 else None
    return None


@dataclass(frozen=True)
class PoseMotionRelation:
    structural_key: tuple[tuple[int, int, str], ...]
    controlled_body_value: int
    controlled_marker_value: int
    token_size: int
    stride: int
    node_baseline_value: int
    connector_value: int
    action_by_direction: tuple[tuple[Direction, int], ...]
    support_count: int
    mismatch_count: int

    @property
    def passed(self) -> bool:
        return self.support_count > 0 and self.mismatch_count == 0

    def action_for(self, direction: Direction) -> int:
        table = dict(self.action_by_direction)
        if direction not in table:
            raise KeyError(f"direction has no witnessed action: {direction}")
        return int(table[direction])

    def semantic_receipt(self) -> dict[str, Any]:
        return {
            "kind": "palette_quotiented_pose_motion_relation_v1",
            "structural_key": [list(row) for row in self.structural_key],
            "token_size": self.token_size,
            "stride": self.stride,
            "action_by_direction": [list(row) for row in self.action_by_direction],
            "support_count": self.support_count,
            "mismatch_count": self.mismatch_count,
            "passed": self.passed,
        }

    def evidence_receipt(self) -> dict[str, Any]:
        return {
            **self.semantic_receipt(),
            "controlled_body_value": self.controlled_body_value,
            "controlled_marker_value": self.controlled_marker_value,
            "node_baseline_value": self.node_baseline_value,
            "connector_value": self.connector_value,
        }


def learn_pose_motion_relation(
    rows: Iterable[Any],
    *,
    controlled_body_value: int,
    controlled_marker_value: int,
    expected_size: int | None = None,
) -> PoseMotionRelation:
    """Learn marker-bearing covariance from within-lifecycle motion rows."""

    supports = 0
    mismatches = 0
    structural_keys: Counter = Counter()
    strides: Counter = Counter()
    baselines: Counter = Counter()
    connectors: Counter = Counter()
    action_directions: dict[int, Counter] = {}
    for row in rows:
        if authoritative_boundary(getattr(row, "identity", None)):
            continue
        before = [
            token for token in scan_oriented_tokens(
                row.s,
                expected_size=expected_size,
            )
            if token.palette
            == (int(controlled_body_value), int(controlled_marker_value))
        ]
        after = [
            token for token in scan_oriented_tokens(
                row.s_next,
                expected_size=expected_size,
            )
            if token.palette
            == (int(controlled_body_value), int(controlled_marker_value))
        ]
        if len(before) != 1 or len(after) != 1:
            continue
        source, target = before[0], after[0]
        dy = target.origin[0] - source.origin[0]
        dx = target.origin[1] - source.origin[1]
        direction = _direction(dy, dx)
        if direction is None:
            continue
        supports += 1
        structural_keys[target.structural_key] += 1
        strides[max(abs(dy), abs(dx))] += 1
        if target.bearing != direction:
            mismatches += 1
        action_directions.setdefault(int(row.a), Counter())[direction] += 1
        baseline = _uniform_region(
            row.s_next,
            source.origin[0],
            source.origin[1],
            source.size,
            source.size,
        )
        if baseline is not None:
            baselines[baseline] += 1
        region = _between_region(
            source.origin,
            target.origin,
            size=source.size,
        )
        if region is not None:
            connector = _uniform_region(row.s, *region)
            if connector is not None:
                connectors[connector] += 1
    if not supports or not structural_keys or not strides:
        raise ValueError("no supported oriented-token motion relation")
    if not baselines or not connectors:
        raise ValueError("motion evidence did not expose lattice values")
    action_by_direction: dict[Direction, int] = {}
    for action, counts in action_directions.items():
        direction, _count = counts.most_common(1)[0]
        if len(counts) != 1:
            mismatches += sum(counts.values()) - counts[direction]
        if direction in action_by_direction and action_by_direction[direction] != action:
            mismatches += 1
        action_by_direction[direction] = action
    return PoseMotionRelation(
        structural_key=structural_keys.most_common(1)[0][0],
        controlled_body_value=int(controlled_body_value),
        controlled_marker_value=int(controlled_marker_value),
        token_size=expected_size or (
            1 + max(row[0] for row in structural_keys.most_common(1)[0][0])
        ),
        stride=int(strides.most_common(1)[0][0]),
        node_baseline_value=int(baselines.most_common(1)[0][0]),
        connector_value=int(connectors.most_common(1)[0][0]),
        action_by_direction=tuple(sorted(
            (direction, action)
            for direction, action in action_by_direction.items()
        )),
        support_count=supports,
        mismatch_count=mismatches,
    )


def discover_pose_motion_relations(
    rows: Iterable[Any],
) -> tuple[PoseMotionRelation, ...]:
    """Discover moving oriented-token palettes before learning their law."""

    rows = tuple(rows)
    candidate_sizes: dict[tuple[int, int], Counter] = {}
    for row in rows:
        if authoritative_boundary(getattr(row, "identity", None)):
            continue
        before = scan_oriented_tokens(row.s)
        after = scan_oriented_tokens(row.s_next)
        before_by_palette: dict[tuple[int, int], list[OrientedToken]] = {}
        after_by_palette: dict[tuple[int, int], list[OrientedToken]] = {}
        for token in before:
            before_by_palette.setdefault(token.palette, []).append(token)
        for token in after:
            after_by_palette.setdefault(token.palette, []).append(token)
        for palette in before_by_palette.keys() & after_by_palette.keys():
            source = before_by_palette[palette]
            target = after_by_palette[palette]
            if len(source) != 1 or len(target) != 1:
                continue
            if source[0].origin == target[0].origin:
                continue
            if source[0].structural_key != target[0].structural_key:
                continue
            candidate_sizes.setdefault(palette, Counter())[source[0].size] += 1
    relations = []
    for (body, marker), sizes in sorted(candidate_sizes.items()):
        relation = learn_pose_motion_relation(
            rows,
            controlled_body_value=body,
            controlled_marker_value=marker,
            expected_size=sizes.most_common(1)[0][0],
        )
        if relation.passed:
            relations.append(relation)
    return tuple(relations)


@dataclass(frozen=True)
class GoalPrototype:
    kind: str
    size: int
    uniform_value: int
    support: int = 1

    def to_receipt(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "size": self.size,
            "uniform_value": self.uniform_value,
            "support": self.support,
        }


def learn_goal_prototype(
    source_grid: Sequence[Sequence[int]],
    *,
    boundary_action: int,
    relation: PoseMotionRelation,
) -> GoalPrototype:
    controlled = [
        token for token in scan_oriented_tokens(
            source_grid,
            expected_size=relation.token_size,
        )
        if token.palette == (
            relation.controlled_body_value,
            relation.controlled_marker_value,
        )
    ]
    if len(controlled) != 1:
        raise ValueError("goal source does not contain one controlled token")
    inverse = {action: direction for direction, action in relation.action_by_direction}
    if int(boundary_action) not in inverse:
        raise ValueError("goal boundary action has no witnessed direction")
    vector = _DIRECTION_VECTORS[inverse[int(boundary_action)]]
    target = (
        controlled[0].origin[0] + vector[0] * relation.stride,
        controlled[0].origin[1] + vector[1] * relation.stride,
    )
    value = _uniform_region(
        source_grid,
        target[0],
        target[1],
        relation.token_size,
        relation.token_size,
    )
    if value is None:
        raise ValueError("goal destination is not a uniform token-sized region")
    return GoalPrototype(
        kind="boundary_predecessor_uniform_goal_v1",
        size=relation.token_size,
        uniform_value=int(value),
    )


@dataclass(frozen=True)
class RelationalScene:
    nodes: tuple[Point, ...]
    edges: tuple[tuple[Point, Point], ...]
    start: Point
    goals: tuple[Point, ...]
    oriented_entities: tuple[tuple[Point, Direction], ...]
    stride: int
    action_by_direction: tuple[tuple[Direction, int], ...]

    def adjacency(self) -> dict[Point, tuple[Point, ...]]:
        table: dict[Point, set[Point]] = {node: set() for node in self.nodes}
        for source, target in self.edges:
            table[source].add(target)
            table[target].add(source)
        return {key: tuple(sorted(value)) for key, value in table.items()}


def _extract_relational_scene(
    grid: Sequence[Sequence[int]],
    *,
    relation: PoseMotionRelation,
    goal: GoalPrototype,
    lifecycle: str,
) -> RelationalScene:
    if not relation.passed:
        raise ValueError("pose-motion relation is not supported")
    tokens = tuple(
        token for token in scan_oriented_tokens(
            grid,
            expected_size=relation.token_size,
        )
        if token.structural_key == relation.structural_key
    )
    controlled = tuple(
        token for token in tokens
        if token.palette == (
            relation.controlled_body_value,
            relation.controlled_marker_value,
        )
    )
    if len(controlled) != 1:
        raise ValueError("target does not contain one controlled token")
    start = controlled[0].origin
    if any(
        coordinate % relation.stride != start[index] % relation.stride
        for token in tokens
        for index, coordinate in enumerate(token.origin)
    ):
        raise ValueError("oriented token lies outside the controlled lattice")

    token_by_origin = {token.origin: token for token in tokens}
    nodes = set()
    goals = set()
    uniform_by_origin = {}
    y_phase = start[0] % relation.stride
    x_phase = start[1] % relation.stride
    for y in range(y_phase, len(grid) - relation.token_size + 1, relation.stride):
        for x in range(x_phase, len(grid[0]) - relation.token_size + 1, relation.stride):
            origin = (y, x)
            uniform = _uniform_region(
                grid,
                y,
                x,
                relation.token_size,
                relation.token_size,
            )
            uniform_by_origin[origin] = uniform
            if origin in token_by_origin or uniform == relation.node_baseline_value:
                nodes.add(origin)
    if start not in nodes:
        raise ValueError("scene start identity is ambiguous")

    if goal.kind == "boundary_predecessor_uniform_goal_v1":
        # Goal color is presentation evidence. Its portable identity is the
        # unique uniform, nonstructural lattice region attached to the learned
        # route graph by the learned connector relation.
        excluded_values = {
            relation.node_baseline_value,
            relation.connector_value,
            *(
                value
                for token in tokens
                for value in token.palette
            ),
        }
        for origin, uniform in uniform_by_origin.items():
            if (
                uniform is None
                or uniform in excluded_values
                or origin in token_by_origin
            ):
                continue
            attached = False
            for vector in _DIRECTION_VECTORS.values():
                neighbor = (
                    origin[0] + vector[0] * relation.stride,
                    origin[1] + vector[1] * relation.stride,
                )
                if neighbor not in nodes:
                    continue
                region = _between_region(
                    origin,
                    neighbor,
                    size=relation.token_size,
                )
                if region is not None and _uniform_region(
                    grid,
                    *region,
                ) == relation.connector_value:
                    attached = True
                    break
            if attached:
                goals.add(origin)
    else:
        goals = {
            origin
            for origin, uniform in uniform_by_origin.items()
            if uniform == goal.uniform_value
        }
    if len(goals) != 1:
        raise ValueError("scene goal identity is ambiguous")
    nodes.update(goals)

    edges = set()
    for source in nodes:
        for vector in _DIRECTION_VECTORS.values():
            target = (
                source[0] + vector[0] * relation.stride,
                source[1] + vector[1] * relation.stride,
            )
            if target not in nodes or source >= target:
                continue
            region = _between_region(
                source,
                target,
                size=relation.token_size,
            )
            if region is not None and _uniform_region(
                grid,
                *region,
            ) == relation.connector_value:
                edges.add((source, target))
    entities = tuple(sorted(
        (token.origin, token.bearing)
        for token in tokens
        if token not in controlled
    ))
    if lifecycle == "active_relation" and not entities:
        raise ValueError("scene contains no transported oriented entity")
    if lifecycle == "settled_residual" and entities:
        raise ValueError("settled residual scene still contains target entity")
    if lifecycle not in {"active_relation", "settled_residual"}:
        raise ValueError(f"unknown relational scene lifecycle: {lifecycle}")
    return RelationalScene(
        nodes=tuple(sorted(nodes)),
        edges=tuple(sorted(edges)),
        start=start,
        goals=tuple(sorted(goals)),
        oriented_entities=entities,
        stride=relation.stride,
        action_by_direction=relation.action_by_direction,
    )


def extract_relational_scene(
    grid: Sequence[Sequence[int]],
    *,
    relation: PoseMotionRelation,
    goal: GoalPrototype,
) -> RelationalScene:
    """Extract an active scene whose transported entity remains unresolved."""

    return _extract_relational_scene(
        grid,
        relation=relation,
        goal=goal,
        lifecycle="active_relation",
    )


def extract_settled_residual_scene(
    grid: Sequence[Sequence[int]],
    *,
    relation: PoseMotionRelation,
    goal: GoalPrototype,
) -> RelationalScene:
    """Extract navigation state after target-motion authority was discharged."""

    return _extract_relational_scene(
        grid,
        relation=relation,
        goal=goal,
        lifecycle="settled_residual",
    )


@dataclass(frozen=True)
class RouteAffordance:
    route: tuple[Point, ...]
    action_count: int
    contact_kind: str
    contact_depth: int | None
    entity_origin: Point | None
    entity_bearing: Direction | None
    budget_feasible: bool

    @property
    def risk_rank(self) -> int:
        return _CONTACT_RISK[self.contact_kind]

    def to_receipt(self) -> dict[str, Any]:
        return {
            "route": [list(point) for point in self.route],
            "action_count": self.action_count,
            "contact_kind": self.contact_kind,
            "contact_depth": self.contact_depth,
            "entity_origin": (
                list(self.entity_origin) if self.entity_origin is not None else None
            ),
            "entity_bearing": self.entity_bearing,
            "risk_rank": self.risk_rank,
            "budget_feasible": self.budget_feasible,
        }


def _route_affordance(
    route: tuple[Point, ...],
    scene: RelationalScene,
    *,
    budget: int,
) -> RouteAffordance:
    contacts = []
    for entity, bearing in scene.oriented_entities:
        facing_vector = _DIRECTION_VECTORS[bearing]
        front_neighbor = (
            entity[0] + facing_vector[0] * scene.stride,
            entity[1] + facing_vector[1] * scene.stride,
        )
        # The transported relation predicts a one-step motion cone. Entering
        # its front-adjacent node is therefore already a closing exposure; a
        # planner cannot defer classification until literal overlap and still
        # claim to have preserved the alternative route.
        if front_neighbor in route:
            front_index = route.index(front_neighbor)
            entity_index = route.index(entity) if entity in route else None
            if entity_index is None or front_index < entity_index:
                contacts.append((
                    front_index,
                    -_CONTACT_RISK["head_on"],
                    "head_on",
                    entity,
                    bearing,
                ))
                continue
        if entity not in route:
            continue
        index = route.index(entity)
        if index == 0:
            continue
        predecessor = route[index - 1]
        relative = _direction(
            predecessor[0] - entity[0],
            predecessor[1] - entity[1],
        )
        if relative == bearing:
            kind = "head_on"
        elif relative is not None and _DIRECTION_VECTORS[relative] == tuple(
            -value for value in _DIRECTION_VECTORS[bearing]
        ):
            kind = "rear"
        else:
            kind = "transverse"
        contacts.append((index, -_CONTACT_RISK[kind], kind, entity, bearing))
    if contacts:
        depth, _negative_risk, kind, entity, bearing = min(contacts)
    else:
        depth, kind, entity, bearing = None, "none", None, None
    action_count = len(route) - 1
    return RouteAffordance(
        route=route,
        action_count=action_count,
        contact_kind=kind,
        contact_depth=depth,
        entity_origin=entity,
        entity_bearing=bearing,
        budget_feasible=action_count <= int(budget),
    )


def _simple_routes(
    scene: RelationalScene,
    *,
    budget: int,
) -> tuple[tuple[Point, ...], ...]:
    adjacency = scene.adjacency()
    routes = []

    def visit(path: tuple[Point, ...]) -> None:
        if len(path) - 1 > budget:
            return
        current = path[-1]
        if current in scene.goals:
            routes.append(path)
            return
        for successor in adjacency.get(current, ()):
            if successor not in path:
                visit((*path, successor))

    visit((scene.start,))
    return tuple(sorted(set(routes)))


@dataclass(frozen=True)
class AffordanceFrontier:
    scene: RelationalScene
    prefix: tuple[Point, ...]
    budget: int
    candidates: tuple[RouteAffordance, ...]
    selected_index: int
    decision_rule: str

    @property
    def selected(self) -> RouteAffordance:
        return self.candidates[self.selected_index]

    @property
    def selected_direction(self) -> Direction | None:
        route = self.selected.route
        if len(route) <= len(self.prefix):
            return None
        source = self.prefix[-1]
        target = route[len(self.prefix)]
        return _direction(target[0] - source[0], target[1] - source[1])

    @property
    def selected_action(self) -> int | None:
        direction = self.selected_direction
        if direction is None:
            return None
        return dict(self.scene.action_by_direction).get(direction)

    def to_receipt(self) -> dict[str, Any]:
        return {
            "schema": "ztare-relational-affordance-frontier-v1",
            "prefix": [list(point) for point in self.prefix],
            "budget": self.budget,
            "decision_rule": self.decision_rule,
            "candidate_count": len(self.candidates),
            "candidates": [row.to_receipt() for row in self.candidates],
            "selected_index": self.selected_index,
            "selected_direction": self.selected_direction,
            "selected_action": self.selected_action,
        }


def compile_relational_affordance_frontier(
    scene: RelationalScene,
    *,
    prefix: Sequence[Point],
    budget: int,
) -> AffordanceFrontier:
    prefix = tuple(prefix)
    if not prefix or prefix[0] != scene.start:
        raise ValueError("prefix must start at the scene's controlled node")
    routes = tuple(
        route for route in _simple_routes(scene, budget=int(budget))
        if route[:len(prefix)] == prefix
    )
    candidates = tuple(
        _route_affordance(route, scene, budget=int(budget)) for route in routes
    )
    if not candidates:
        raise ValueError("no budget-feasible route extends the prefix")
    selected = min(
        range(len(candidates)),
        key=lambda index: (
            not candidates[index].budget_feasible,
            candidates[index].risk_rank,
            candidates[index].action_count,
            candidates[index].route,
        ),
    )
    return AffordanceFrontier(
        scene=scene,
        prefix=prefix,
        budget=int(budget),
        candidates=candidates,
        selected_index=selected,
        decision_rule=(
            "budget_feasible_then_nonclosing_contact_then_shortest_v1"
        ),
    )


def _transform_vector(point: Point, transform: tuple[bool, int, int]) -> Point:
    swap, sy, sx = transform
    y, x = (point[1], point[0]) if swap else point
    return (sy * y, sx * x)


def transform_scene(
    scene: RelationalScene,
    transform: tuple[bool, int, int],
) -> RelationalScene:
    anchor = scene.start

    def point(value: Point) -> Point:
        relative = (value[0] - anchor[0], value[1] - anchor[1])
        transformed = _transform_vector(relative, transform)
        return (anchor[0] + transformed[0], anchor[1] + transformed[1])

    def direction(value: Direction) -> Direction:
        transformed = _transform_vector(_DIRECTION_VECTORS[value], transform)
        return _VECTOR_DIRECTIONS[transformed]

    edges = tuple(sorted(
        tuple(sorted((point(source), point(target))))
        for source, target in scene.edges
    ))
    return RelationalScene(
        nodes=tuple(sorted(point(value) for value in scene.nodes)),
        edges=edges,
        start=point(scene.start),
        goals=tuple(sorted(point(value) for value in scene.goals)),
        oriented_entities=tuple(sorted(
            (point(origin), direction(bearing))
            for origin, bearing in scene.oriented_entities
        )),
        stride=scene.stride,
        action_by_direction=tuple(sorted(
            (direction(source), action)
            for source, action in scene.action_by_direction
        )),
    )


def transform_path(
    path: Sequence[Point],
    *,
    anchor: Point,
    transform: tuple[bool, int, int],
) -> tuple[Point, ...]:
    return tuple(
        (
            anchor[0] + _transform_vector(
                (point[0] - anchor[0], point[1] - anchor[1]),
                transform,
            )[0],
            anchor[1] + _transform_vector(
                (point[0] - anchor[0], point[1] - anchor[1]),
                transform,
            )[1],
        )
        for point in path
    )


def canonical_frontier_key(frontier: AffordanceFrontier) -> str:
    """D4- and translation-invariant semantic identity for one frontier."""

    scene = frontier.scene
    rows = []
    for transform in (
        (False, -1, -1),
        (False, -1, 1),
        (False, 1, -1),
        (False, 1, 1),
        (True, -1, -1),
        (True, -1, 1),
        (True, 1, -1),
        (True, 1, 1),
    ):
        transformed_scene = transform_scene(scene, transform)
        transformed_prefix = transform_path(
            frontier.prefix,
            anchor=scene.start,
            transform=transform,
        )
        transformed_frontier = compile_relational_affordance_frontier(
            transformed_scene,
            prefix=transformed_prefix,
            budget=frontier.budget,
        )
        anchor = transformed_scene.start

        def relative(point: Point) -> Point:
            return (
                (point[0] - anchor[0]) // scene.stride,
                (point[1] - anchor[1]) // scene.stride,
            )

        rows.append({
            "nodes": sorted(relative(point) for point in transformed_scene.nodes),
            "edges": sorted(
                tuple(sorted((relative(source), relative(target))))
                for source, target in transformed_scene.edges
            ),
            "goals": sorted(relative(point) for point in transformed_scene.goals),
            "entities": sorted(
                (relative(origin), bearing)
                for origin, bearing in transformed_scene.oriented_entities
            ),
            "prefix": [relative(point) for point in transformed_prefix],
            "selected_route": [
                relative(point) for point in transformed_frontier.selected.route
            ],
            "selected_contact": transformed_frontier.selected.contact_kind,
            "selected_action_count": transformed_frontier.selected.action_count,
        })
    canonical = min(
        json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows
    )
    return _canonical_sha256(json.loads(canonical))


__all__ = [
    "AffordanceFrontier",
    "GoalPrototype",
    "OrientedToken",
    "PoseMotionRelation",
    "RelationalScene",
    "RouteAffordance",
    "canonical_frontier_key",
    "compile_relational_affordance_frontier",
    "discover_pose_motion_relations",
    "extract_relational_scene",
    "extract_settled_residual_scene",
    "learn_goal_prototype",
    "learn_pose_motion_relation",
    "scan_oriented_tokens",
    "transform_path",
    "transform_scene",
]
