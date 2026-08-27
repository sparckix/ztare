from __future__ import annotations

from dataclasses import replace

import pytest

from ztare.common.wake_sleep_credit_router import (
    MemoryScope,
    WakeSleepCreditState,
)
from ztare.worldmodel.episode_log import EpisodeLog, Transition
from ztare.worldmodel.relational_affordance import (
    RelationalScene,
    canonical_frontier_key,
    compile_relational_affordance_frontier,
    discover_pose_motion_relations,
    scan_oriented_tokens,
    transform_path,
    transform_scene,
)
from ztare.worldmodel.relational_affordance_recall import (
    ActiveRelationalWorkingRevision,
    RelationalAffordanceMemoryRevision,
    RelationalAffordanceRecallProposal,
    SettledResidualWorkingRevision,
    advance_relational_working_revision,
    compile_active_relational_working_revision,
    discover_relational_decision_seam,
    select_relational_affordance_recall,
)
from ztare.worldmodel.transition_identity import TransitionIdentity


def _put_token(grid, origin, *, body, marker, bearing):
    marker_offset = {
        "up": (0, 1),
        "down": (2, 1),
        "left": (1, 0),
        "right": (1, 2),
    }[bearing]
    for dy in range(3):
        for dx in range(3):
            grid[origin[0] + dy][origin[1] + dx] = (
                marker if (dy, dx) == marker_offset else body
            )


def _motion_grid(source, target, *, bearing, token_at):
    grid = [[5] * 27 for _ in range(27)]
    for origin in (source, target):
        for dy in range(3):
            for dx in range(3):
                grid[origin[0] + dy][origin[1] + dx] = 0
    if source[0] == target[0]:
        x0 = min(source[1], target[1]) + 3
        for y in range(source[0], source[0] + 3):
            for x in range(x0, x0 + 3):
                grid[y][x] = 2
    else:
        y0 = min(source[0], target[0]) + 3
        for y in range(y0, y0 + 3):
            for x in range(source[1], source[1] + 3):
                grid[y][x] = 2
    _put_token(
        grid,
        token_at,
        body=9,
        marker=4,
        bearing=bearing,
    )
    return tuple(tuple(row) for row in grid)


def _motion_log():
    identity = TransitionIdentity(
        kind="dynamics",
        authority="episode_collector",
        source_epoch="e0",
        target_epoch="e0",
        evidence_refs=("synthetic:oriented-motion",),
    )
    origin = (12, 12)
    rows = []
    for action, bearing, target in (
        (0, "up", (6, 12)),
        (1, "down", (18, 12)),
        (2, "left", (12, 6)),
        (3, "right", (12, 18)),
    ):
        rows.append(Transition(
            len(rows),
            _motion_grid(origin, target, bearing="right", token_at=origin),
            action,
            _motion_grid(origin, target, bearing=bearing, token_at=target),
            identity,
        ))
    return EpisodeLog(rows)


def _scene():
    main = tuple((0, x) for x in range(0, 37, 6))
    nodes = {
        *main,
        (-6, 36),
        (6, 0),
        (6, 12),
        (6, 18),
        (6, 24),
    }
    edges = {
        tuple(sorted((main[index], main[index + 1])))
        for index in range(len(main) - 1)
    }
    edges.update({
        tuple(sorted(((-6, 36), (0, 36)))),
        tuple(sorted(((6, 0), (0, 0)))),
        tuple(sorted(((0, 12), (6, 12)))),
        tuple(sorted(((0, 18), (6, 18)))),
        tuple(sorted(((6, 12), (6, 18)))),
        tuple(sorted(((6, 18), (6, 24)))),
        tuple(sorted(((6, 24), (0, 24)))),
    })
    return RelationalScene(
        nodes=tuple(sorted(nodes)),
        edges=tuple(sorted(edges)),
        start=(6, 0),
        goals=((-6, 36),),
        oriented_entities=(((0, 24), "left"),),
        stride=6,
        action_by_direction=(
            ("down", 1),
            ("left", 2),
            ("right", 3),
            ("up", 0),
        ),
    )


def test_oriented_token_identity_quotients_palette_but_retains_bearing():
    first = [[5] * 9 for _ in range(9)]
    second = [[5] * 9 for _ in range(9)]
    _put_token(first, (3, 3), body=9, marker=4, bearing="left")
    _put_token(second, (3, 3), body=8, marker=15, bearing="up")
    first_token = scan_oriented_tokens(first, expected_size=3)[0]
    second_token = scan_oriented_tokens(second, expected_size=3)[0]
    assert first_token.structural_key == second_token.structural_key
    assert first_token.palette != second_token.palette
    assert first_token.bearing == "left"
    assert second_token.bearing == "up"


def test_pose_motion_relation_discovers_palette_stride_lattice_and_actions():
    relations = discover_pose_motion_relations(_motion_log())
    assert len(relations) == 1
    relation = relations[0]
    assert relation.passed
    assert relation.support_count == 4
    assert relation.mismatch_count == 0
    assert relation.stride == 6
    assert relation.node_baseline_value == 0
    assert relation.connector_value == 2
    assert dict(relation.action_by_direction) == {
        "up": 0,
        "down": 1,
        "left": 2,
        "right": 3,
    }


def test_affordance_frontier_selects_transverse_route_before_closing_node():
    scene = _scene()
    prefix = ((6, 0), (0, 0), (0, 6), (0, 12))
    frontier = compile_relational_affordance_frontier(
        scene,
        prefix=prefix,
        budget=10,
    )
    assert frontier.selected_direction == "down"
    assert frontier.selected_action == 1
    assert frontier.selected.contact_kind == "transverse"
    assert frontier.selected.action_count == 10
    assert any(row.contact_kind == "head_on" for row in frontier.candidates)


def test_affordance_frontier_commutes_with_d4_scene_transforms():
    scene = _scene()
    prefix = ((6, 0), (0, 0), (0, 6), (0, 12))
    frontier = compile_relational_affordance_frontier(
        scene,
        prefix=prefix,
        budget=10,
    )
    key = canonical_frontier_key(frontier)
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
            prefix,
            anchor=scene.start,
            transform=transform,
        )
        transformed = compile_relational_affordance_frontier(
            transformed_scene,
            prefix=transformed_prefix,
            budget=10,
        )
        assert transformed.selected_action == 1
        assert transformed.selected.contact_kind == "transverse"
        assert canonical_frontier_key(transformed) == key


def _scope(context="target-observation"):
    return MemoryScope(
        task_sha256="task",
        controller_sha256="controller",
        context_sha256=context,
        choice_set_sha256="choices",
        action_vocabulary_sha256="actions",
    )


def _recall_proposal():
    relation = discover_pose_motion_relations(_motion_log())[0]
    seam, _frontier = discover_relational_decision_seam(_scene(), budget=10)
    memory = RelationalAffordanceMemoryRevision(
        relation=relation,
        goal_kind="boundary_predecessor_uniform_goal_v1",
        goal_size=3,
        source_support_refs=("turn:0", "boundary:1"),
        boundary_support_refs=("boundary:1",),
    )
    return RelationalAffordanceRecallProposal(
        memory_revision=memory,
        scope=_scope(),
        target_observation_sha256="target-observation",
        target_entity_bearings=("left",),
        decision_seam=seam,
        predicted_decision_delta=2 / 3,
        retrieval_cost=0.05,
        primitive_action_cost=10.0,
    )


def test_decision_seam_is_discovered_before_branch_advice():
    seam, frontier = discover_relational_decision_seam(_scene(), budget=10)
    assert seam.approach_directions == ("up", "right", "right")
    assert seam.approach_actions == (0, 3, 3)
    assert {branch.direction for branch in seam.branches} == {"down", "right"}
    assert seam.selected_direction == "down"
    assert seam.selected_action == 1
    assert seam.selected_contact_kind == "transverse"
    assert seam.frontier_sha256 == canonical_frontier_key(frontier)


def test_relational_recall_selects_only_under_exact_scope():
    proposal = _recall_proposal()
    selected = select_relational_affordance_recall(
        proposal,
        WakeSleepCreditState(),
        consumption_scope=proposal.scope,
    )
    assert selected.selected
    assert selected.digest["decision_seam"]["selected_action"] == 1
    for field in (
        "task_sha256",
        "controller_sha256",
        "context_sha256",
        "choice_set_sha256",
        "action_vocabulary_sha256",
    ):
        drifted = replace(
            proposal.scope,
            **{field: f"drifted-{field}"},
        )
        refused = select_relational_affordance_recall(
            proposal,
            WakeSleepCreditState(),
            consumption_scope=drifted,
        )
        assert not refused.selected
        assert refused.recall.selections == ()


def test_source_memory_identity_excludes_target_context():
    proposal = _recall_proposal()
    other_scope = replace(
        proposal.scope,
        context_sha256="other-observation",
    )
    other = replace(
        proposal,
        scope=other_scope,
        target_observation_sha256="other-observation",
        target_entity_bearings=("up",),
    )
    assert proposal.memory_revision.sha256 == other.memory_revision.sha256
    assert proposal.sha256 != other.sha256
    with pytest.raises(ValueError, match="bind target observation"):
        replace(proposal, target_observation_sha256="wrong")


def test_decision_seam_refuses_single_route_scene():
    scene = _scene()
    start_edge = tuple(sorted((scene.start, (0, 0))))
    direct_edges = tuple(
        edge for edge in scene.edges
        if edge == start_edge or all(point[0] <= 0 for point in edge)
    )
    with pytest.raises(ValueError, match="no competing"):
        discover_relational_decision_seam(
            replace(scene, edges=direct_edges),
            budget=10,
        )


def _put_region(grid, origin, value):
    for dy in range(3):
        for dx in range(3):
            grid[origin[0] + dy][origin[1] + dx] = value


def _connect_regions(grid, source, target):
    if source[0] == target[0]:
        x0 = min(source[1], target[1]) + 3
        for y in range(source[0], source[0] + 3):
            for x in range(x0, x0 + 3):
                grid[y][x] = 2
    else:
        y0 = min(source[0], target[0]) + 3
        for y in range(y0, y0 + 3):
            for x in range(source[1], source[1] + 3):
                grid[y][x] = 2


def _working_grid(controlled_origin, controlled_bearing, *, target=True):
    main = tuple((18, x) for x in range(6, 43, 6))
    nodes = {
        *main,
        (12, 42),
        (24, 6),
        (24, 18),
        (24, 24),
        (24, 30),
    }
    edges = {
        tuple(sorted((main[index], main[index + 1])))
        for index in range(len(main) - 1)
    }
    edges.update({
        tuple(sorted(((12, 42), (18, 42)))),
        tuple(sorted(((18, 6), (24, 6)))),
        tuple(sorted(((18, 18), (24, 18)))),
        tuple(sorted(((24, 18), (24, 24)))),
        tuple(sorted(((24, 24), (24, 30)))),
        tuple(sorted(((24, 30), (18, 30)))),
    })
    grid = [[5] * 51 for _ in range(39)]
    for node in nodes:
        _put_region(grid, node, 14 if node == (12, 42) else 0)
    for source, successor in edges:
        _connect_regions(grid, source, successor)
    _put_token(
        grid,
        controlled_origin,
        body=9,
        marker=4,
        bearing=controlled_bearing,
    )
    if target:
        _put_token(
            grid,
            (18, 30),
            body=8,
            marker=15,
            bearing="left",
        )
    return tuple(tuple(row) for row in grid)


def test_recurrent_working_revision_rebinds_then_settles_target_transport():
    memory = _recall_proposal().memory_revision
    states = (
        ((24, 6), "up", True),
        ((18, 6), "up", True),
        ((18, 12), "right", True),
        ((18, 18), "right", True),
        ((24, 18), "down", True),
        ((24, 24), "right", True),
        ((24, 30), "right", True),
        ((18, 30), "up", False),
        ((18, 36), "right", False),
        ((18, 42), "right", False),
    )
    expected_actions = (0, 3, 3, 1, 3, 3, 0, 3, 3, 0)
    revision = compile_active_relational_working_revision(
        memory,
        target_grid=_working_grid(*states[0][:2], target=states[0][2]),
        observation_sha256="observation:0",
        scope=_scope("observation:0"),
        remaining_budget=10,
    )
    revisions = [revision]
    target_settlements = []
    for index, expected_action in enumerate(expected_actions):
        assert revision.selected_action == expected_action
        assert revision.memory_revision.sha256 == memory.sha256
        if index == len(expected_actions) - 1:
            break
        origin, bearing, target = states[index + 1]
        advance = advance_relational_working_revision(
            revision,
            successor_grid=_working_grid(origin, bearing, target=target),
            successor_observation_sha256=f"observation:{index + 1}",
            successor_scope=_scope(f"observation:{index + 1}"),
            remaining_budget=9 - index,
        )
        if (
            advance.settlement is not None
            and advance.settlement.status != "not_tested"
        ):
            target_settlements.append(advance.settlement)
        assert (
            advance.revision.predecessor_revision_sha256
            == revision.sha256
        )
        revision = advance.revision
        revisions.append(revision)

    assert isinstance(revisions[6], ActiveRelationalWorkingRevision)
    assert revisions[6].tests_target_transport
    assert isinstance(revisions[7], SettledResidualWorkingRevision)
    assert all(
        isinstance(row, SettledResidualWorkingRevision)
        for row in revisions[7:]
    )
    assert len(target_settlements) == 1
    assert target_settlements[0].status == "target_transport_refuted"
    assert target_settlements[0].observed_target_entities == ()
    assert len({row.sha256 for row in revisions}) == len(revisions)


def test_working_revision_refuses_stale_scope_and_residual_target_reentry():
    memory = _recall_proposal().memory_revision
    start_grid = _working_grid((24, 6), "up", target=True)
    with pytest.raises(ValueError, match="does not bind observation"):
        compile_active_relational_working_revision(
            memory,
            target_grid=start_grid,
            observation_sha256="current",
            scope=_scope("stale"),
            remaining_budget=10,
        )

    revision = compile_active_relational_working_revision(
        memory,
        target_grid=_working_grid((24, 30), "right", target=True),
        observation_sha256="contact-source",
        scope=_scope("contact-source"),
        remaining_budget=4,
    )
    advance = advance_relational_working_revision(
        revision,
        successor_grid=_working_grid((18, 30), "up", target=False),
        successor_observation_sha256="contact-successor",
        successor_scope=_scope("contact-successor"),
        remaining_budget=3,
    )
    with pytest.raises(ValueError, match="still contains target entity"):
        advance_relational_working_revision(
            advance.revision,
            successor_grid=_working_grid((18, 36), "right", target=True),
            successor_observation_sha256="target-reappeared",
            successor_scope=_scope("target-reappeared"),
            remaining_budget=2,
        )
