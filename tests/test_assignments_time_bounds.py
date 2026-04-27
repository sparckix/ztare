"""Hole 11: time-bounds for Registry.active_assignments().

Builds an in-memory Registry with synthetic assignments covering past,
current, future, and open-ended windows, and checks that the filter
returns the correct subset for each.
"""

from __future__ import annotations

from datetime import date, timedelta

from src.ztare.roles.loader import (
    Assignment,
    BudgetConfig,
    Member,
    Registry,
    Role,
)


def _role(role_id: str) -> Role:
    return Role(
        role_id=role_id,
        role_class="specialist",
        description="",
        authorized_paths=(),
        forbidden_paths=(),
        delegates_to=(),
        escalates_to=(),
        budget=BudgetConfig(),
        mandate_path=None,
        sla={},
        failure_mode={},
        signs_gates=(),
    )


def _member(member_id: str) -> Member:
    return Member(
        member_id=member_id,
        kind="human",
        display_name=member_id,
        description="",
        substrates=(),
        contact={},
        availability={},
    )


def _registry() -> Registry:
    today = date.today()
    past = (today - timedelta(days=10)).isoformat()
    yesterday = (today - timedelta(days=1)).isoformat()
    tomorrow = (today + timedelta(days=1)).isoformat()
    far_future = (today + timedelta(days=30)).isoformat()

    assigns = (
        # Fully expired
        Assignment(
            member_id="alice", role_id="r1", substrate="s",
            is_primary=True, valid_from=past, valid_until=yesterday,
        ),
        # Open-ended, already valid
        Assignment(
            member_id="alice", role_id="r2", substrate="s",
            is_primary=True, valid_from=past, valid_until=None,
        ),
        # Starts in the future
        Assignment(
            member_id="bob", role_id="r1", substrate="s",
            is_primary=True, valid_from=tomorrow, valid_until=far_future,
        ),
        # Currently valid bounded window
        Assignment(
            member_id="bob", role_id="r2", substrate="s",
            is_primary=False, valid_from=past, valid_until=far_future,
        ),
    )
    return Registry(
        members={"alice": _member("alice"), "bob": _member("bob")},
        roles={"r1": _role("r1"), "r2": _role("r2")},
        workers={},
        assignments=assigns,
        delegation={},
    )


def test_expired_assignments_excluded():
    r = _registry()
    active = r.active_assignments()
    pairs = {(a.member_id, a.role_id) for a in active}
    assert ("alice", "r1") not in pairs  # expired
    assert ("alice", "r2") in pairs      # open-ended
    assert ("bob", "r2") in pairs        # currently valid
    assert ("bob", "r1") not in pairs    # starts tomorrow


def test_filter_by_role():
    r = _registry()
    r2 = r.active_assignments(role_id="r2")
    members = {a.member_id for a in r2}
    assert members == {"alice", "bob"}


def test_filter_by_member():
    r = _registry()
    alice = r.active_assignments(member_id="alice")
    roles = {a.role_id for a in alice}
    assert roles == {"r2"}  # only her open-ended one


def test_filter_accepts_role_and_member_prefix():
    r = _registry()
    assert r.active_assignments(role_id="role.r2", member_id="member.alice")
