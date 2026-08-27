from __future__ import annotations

from ztare.common.abstraction_functor import Role
from ztare.worldmodel.episode_log import EpisodeLog, Transition
from ztare.worldmodel.object_roles import induce_roles, object_signature
from ztare.worldmodel.transition_identity import TransitionIdentity


def _grid(origin_x: int):
    grid = [[0] * 9 for _ in range(6)]
    # A translated, identity-bearing colored component.
    grid[2][origin_x:origin_x + 2] = [1, 2]
    grid[3][origin_x:origin_x + 2] = [2, 1]
    # Same palette, different component shapes. Palette membership alone must
    # not pull these static presentation features into the controlled entity.
    grid[0][0] = 1
    grid[5][8] = 2
    return tuple(tuple(row) for row in grid)


def test_induced_mover_is_component_orbit_not_palette_property():
    dynamics = TransitionIdentity(
        kind="dynamics",
        authority="episode_collector",
        source_epoch="e0",
        target_epoch="e0",
        evidence_refs=("synthetic:direct-step",),
    )
    boundary = TransitionIdentity(
        kind="epoch_boundary",
        authority="episode_collector",
        source_epoch="e0",
        target_epoch="e1",
        boundary_kind="synthetic",
    )
    log = EpisodeLog([
        Transition(0, _grid(1), 3, _grid(3), dynamics),
        Transition(1, _grid(3), 3, _grid(5), dynamics),
        # A boundary teleport is excluded from orbit support.
        Transition(2, _grid(5), 0, _grid(1), boundary),
    ])

    roles = induce_roles(log, 4).roles
    mover = next(role for role in roles if role.name == "moves_under_actions")
    assert len(mover.members) == 1
    assert mover.members[0]["kind"] == "colored_component_orbit_v1"
    assert mover.members[0]["support"] == 2
    assert mover.members[0]["action_displacements"] == [[3, 0, 2, 2]]

    agent, _resource, reactive = object_signature(_grid(3), roles)
    assert agent == frozenset({(0, 2, 3)})
    assert len(reactive) == 4


def test_object_signature_keeps_legacy_scalar_role_compatibility():
    grid = ((1, 0, 1), (0, 2, 0))
    signature = object_signature(grid, [Role("moves_under_actions", [1])])
    assert signature[0] == frozenset({(0, 0), (0, 2)})


def _oriented_mover_grid(origin_y: int, origin_x: int, facing: str):
    grid = [[0] * 25 for _ in range(25)]
    marker = {
        "up": (0, 1),
        "down": (2, 1),
        "left": (1, 0),
        "right": (1, 2),
    }[facing]
    for dy in range(3):
        for dx in range(3):
            grid[origin_y + dy][origin_x + dx] = (
                4 if (dy, dx) == marker else 9
            )
    # Same palette, incompatible component identities: neither singleton may
    # become part of the controlled object merely through color membership.
    grid[0][0] = 9
    grid[24][24] = 4
    return tuple(tuple(row) for row in grid)


def test_pose_quotient_keeps_one_mover_and_all_action_displacements():
    dynamics = TransitionIdentity(
        kind="dynamics",
        authority="episode_collector",
        source_epoch="e0",
        target_epoch="e0",
        evidence_refs=("synthetic:oriented-mover",),
    )
    specifications = (
        (0, "right", "up", 0, -4),
        (1, "up", "down", 0, 4),
        (2, "down", "left", -4, 0),
        (3, "left", "right", 4, 0),
    )
    rows = []
    observed = []
    for action, prior, facing, dx, dy in specifications:
        before = _oriented_mover_grid(10, 10, prior)
        after = _oriented_mover_grid(10 + dy, 10 + dx, facing)
        second = _oriented_mover_grid(10 + 2 * dy, 10 + 2 * dx, facing)
        rows.extend((
            Transition(len(rows), before, action, after, dynamics),
            Transition(len(rows) + 1, after, action, second, dynamics),
        ))
        observed.extend((before, after))

    roles = induce_roles(EpisodeLog(rows), 4).roles
    mover = next(role for role in roles if role.name == "moves_under_actions")
    assert len(mover.members) == 1
    member = mover.members[0]
    assert member["shape_equivalence"] == "d4_pose_v1"
    assert member["action_displacements"] == [
        [0, -4, 0, 2],
        [1, 4, 0, 2],
        [2, 0, -4, 2],
        [3, 0, 4, 2],
    ]
    assert len(member["observed_pose_shapes"]) == 4
    for grid in observed:
        agent, _resource, _reactive = object_signature(grid, roles)
        assert len(agent) == 1
        assert next(iter(agent))[0] == 0
        assert len(next(iter(agent))) == 4


def test_within_epoch_view_does_not_mix_prior_chart_presentations():
    e0 = TransitionIdentity(
        kind="dynamics",
        authority="episode_collector",
        source_epoch="e0",
        target_epoch="e0",
        evidence_refs=("synthetic:direct-step",),
    )
    e1 = TransitionIdentity(
        kind="dynamics",
        authority="episode_collector",
        source_epoch="e1",
        target_epoch="e1",
        evidence_refs=("synthetic:direct-step",),
    )
    rows = [
        Transition(0, _grid(1), 3, _grid(3), e0),
        Transition(0, _grid(3), 3, _grid(5), e1),
    ]
    active = EpisodeLog(rows).within_epoch_view("e1")
    assert active.transitions() == (rows[1],)
    assert EpisodeLog(rows).within_epoch_view().transitions() == tuple(rows)
    assert len(EpisodeLog(rows).within_epoch_view("missing")) == 0


def test_untrusted_epoch_label_cannot_scope_the_evidence_view():
    trusted = TransitionIdentity(
        kind="dynamics",
        authority="episode_collector",
        source_epoch="e0",
        target_epoch="e0",
        evidence_refs=("synthetic:direct-step",),
    )
    claimed = TransitionIdentity(
        kind="dynamics",
        authority="candidate",
        source_epoch="fabricated",
        target_epoch="fabricated",
    )
    rows = [
        Transition(0, _grid(1), 3, _grid(3), trusted),
        Transition(1, _grid(3), 3, _grid(5), claimed),
    ]
    # Without an adapter-owned lifecycle the bank is not silently scoped.
    # The candidate label cannot acquire chart authority: an explicit trusted
    # request selects e0, while the fabricated chart remains empty.
    assert EpisodeLog(rows).within_epoch_view().transitions() == tuple(rows)
    assert EpisodeLog(rows).within_epoch_view("e0").transitions() == (rows[0],)
    assert len(EpisodeLog(rows).within_epoch_view("fabricated")) == 0


def test_resource_monotonicity_uses_epoch_identity_before_clock_value():
    e0 = TransitionIdentity(
        kind="dynamics",
        authority="episode_collector",
        source_epoch="e0",
        target_epoch="e0",
        evidence_refs=("synthetic:direct-step",),
    )
    e1 = TransitionIdentity(
        kind="dynamics",
        authority="episode_collector",
        source_epoch="e1",
        target_epoch="e1",
        evidence_refs=("synthetic:direct-step",),
    )

    def bar(count: int):
        return (tuple([7] * count + [0] * (4 - count)),)

    # Both epoch starts deliberately use non-zero, increasing clock values.
    # A clock-only segmenter would see the 2 -> 4 refill and reject the role.
    log = EpisodeLog([
        Transition(5, bar(3), 0, bar(2), e0),
        Transition(6, bar(2), 0, bar(1), e0),
        Transition(7, bar(4), 0, bar(3), e1),
        Transition(8, bar(3), 0, bar(2), e1),
    ])
    resource = next(
        role for role in induce_roles(log, 1).roles
        if role.name == "monotone_depleting"
    )
    assert 7 in resource.members
