# SPDX-License-Identifier: MIT
"""Load org/ primitives (members, roles, assignments, delegation) into
typed Python objects and expose a Registry for lookup.

Conventions (see org/README.md):
- org/members/<member_id>.yaml  — who (human or AI actor)
- org/roles/<role_id>.yaml      — what position (substrate-agnostic)
- org/assignments.yaml          — who currently fills which role
- org/delegation.yaml           — cross-role delegation / escalation / signing
- org/mandates/<role_id>_mandate.md  — role-scoped authorization (gitignored)

This loader is intentionally pure-Python and uses PyYAML (already a
transitive dependency of the existing codebase). No side effects —
it reads, validates, and returns immutable dataclasses.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

import yaml

from src.ztare.common.paths import REPO_ROOT


# Filesystem locations
ORG_DIR = REPO_ROOT / "org"
MEMBERS_DIR = ORG_DIR / "members"
ROLES_DIR = ORG_DIR / "roles"
WORKERS_DIR = ORG_DIR / "workers"
ASSIGNMENTS_PATH = ORG_DIR / "assignments.yaml"
DELEGATION_PATH = ORG_DIR / "delegation.yaml"
MANDATES_DIR = ORG_DIR / "mandates"
SESSIONS_DIR = ORG_DIR / "sessions"


# ======================================================================
# Dataclasses
# ======================================================================

@dataclass(frozen=True)
class Substrate:
    """A concrete implementation a member can inhabit (e.g. 'claude_conversational',
    'codex_cli', 'human_conversational')."""
    name: str
    kind: str                       # session_bound | persistent | per_call
    invocation: Optional[str] = None
    current_model: Optional[str] = None
    strengths: tuple[str, ...] = field(default_factory=tuple)
    weaknesses: tuple[str, ...] = field(default_factory=tuple)
    persistence: Optional[str] = None


@dataclass(frozen=True)
class Member:
    """An actor — human or AI — available to fill roles."""
    member_id: str
    kind: str                       # human | ai
    display_name: str
    description: str
    substrates: tuple[Substrate, ...]
    contact: dict                   # free-form: email, ntfy_topic, etc.
    availability: dict
    capabilities: tuple[str, ...] = field(default_factory=tuple)
    contract: dict = field(default_factory=dict)
    opened_date: Optional[str] = None
    opened_by: Optional[str] = None

    @classmethod
    def from_yaml(cls, data: dict) -> "Member":
        # Substrates may be list of strings (for humans) or list of dicts (for AI)
        subs: list[Substrate] = []
        for s in data.get("substrates", []) or []:
            if isinstance(s, str):
                subs.append(Substrate(name=s, kind="unspecified"))
            elif isinstance(s, dict):
                subs.append(Substrate(
                    name=s["name"],
                    kind=s.get("kind", "unspecified"),
                    invocation=s.get("invocation"),
                    current_model=s.get("current_model"),
                    strengths=tuple(s.get("strengths", [])),
                    weaknesses=tuple(s.get("weaknesses", [])),
                    persistence=s.get("persistence"),
                ))
        return cls(
            member_id=data["member_id"],
            kind=data["kind"],
            display_name=data.get("display_name", data["member_id"]),
            description=data.get("description", ""),
            substrates=tuple(subs),
            contact=data.get("contact", {}) or {},
            availability=data.get("availability", {}) or {},
            capabilities=tuple(data.get("capabilities", []) or []),
            contract=data.get("contract", {}) or {},
            opened_date=data.get("opened_date"),
            opened_by=data.get("opened_by"),
        )


@dataclass(frozen=True)
class BudgetConfig:
    daily_cap_usd: Optional[float] = None
    session_cap_usd: Optional[float] = None
    single_action_cap_usd: Optional[float] = None
    warn_threshold_frac: Optional[float] = None
    absolute_ceiling_usd: Optional[float] = None


@dataclass(frozen=True)
class Role:
    """A substrate-agnostic position / function in the org."""
    role_id: str
    role_class: str                 # manager | worker | reviewer | specialist | authority
    description: str
    authorized_paths: tuple[str, ...]
    forbidden_paths: tuple[str, ...]
    delegates_to: tuple[str, ...]
    escalates_to: tuple[str, ...]
    budget: BudgetConfig
    mandate_path: Optional[Path]
    sla: dict
    failure_mode: dict
    signs_gates: tuple[str, ...]
    opened_date: Optional[str] = None
    opened_by: Optional[str] = None

    @classmethod
    def from_yaml(cls, data: dict) -> "Role":
        budget_raw = data.get("budget", {}) or {}
        mandate = data.get("mandate_path")
        mandate_path = (REPO_ROOT / mandate) if mandate else None
        return cls(
            role_id=data["role_id"],
            role_class=data.get("role_class", "specialist"),
            description=data.get("description", ""),
            authorized_paths=tuple(data.get("authorized_paths", []) or []),
            forbidden_paths=tuple(data.get("forbidden_paths", []) or []),
            delegates_to=tuple(data.get("delegates_to", []) or []),
            escalates_to=tuple(data.get("escalates_to", []) or []),
            budget=BudgetConfig(
                daily_cap_usd=budget_raw.get("daily_cap_usd"),
                session_cap_usd=budget_raw.get("session_cap_usd"),
                single_action_cap_usd=budget_raw.get("single_action_cap_usd"),
                warn_threshold_frac=budget_raw.get("warn_threshold_frac"),
                absolute_ceiling_usd=budget_raw.get("absolute_ceiling_usd"),
            ),
            mandate_path=mandate_path,
            sla=data.get("sla", {}) or {},
            failure_mode=data.get("failure_mode", {}) or {},
            signs_gates=tuple(data.get("signs_gates", []) or []),
            opened_date=data.get("opened_date"),
            opened_by=data.get("opened_by"),
        )


@dataclass(frozen=True)
class Worker:
    """Ephemeral tool-invocation membrane (GP-129 Margulis pull-forward).

    Workers are per-call actors with no persistent identity. This
    dataclass captures the input/output contract a role must satisfy
    when invoking them.
    """
    worker_id: str
    description: str
    invocation: dict                # substrate, tool_name, subagent_type, fan_out_ok
    input_contract: dict            # accepts, reads_from, must_receive
    output_contract: dict           # produces, deposits_to, contract_guarantees
    permissions: dict               # read / write / forbidden
    limits: dict                    # cost cap, wall-clock cap
    opened_date: Optional[str] = None
    opened_by: Optional[str] = None

    @classmethod
    def from_yaml(cls, data: dict) -> "Worker":
        return cls(
            worker_id=data["worker_id"],
            description=data.get("description", ""),
            invocation=data.get("invocation", {}) or {},
            input_contract=data.get("input_contract", {}) or {},
            output_contract=data.get("output_contract", {}) or {},
            permissions=data.get("permissions", {}) or {},
            limits=data.get("limits", {}) or {},
            opened_date=data.get("opened_date"),
            opened_by=data.get("opened_by"),
        )


@dataclass(frozen=True)
class Assignment:
    """Binding of (member, role, substrate) over a validity window."""
    member_id: str          # without the "member." prefix
    role_id: str            # without the "role." prefix
    substrate: str
    is_primary: bool
    valid_from: str
    valid_until: Optional[str]
    notes: str = ""


@dataclass(frozen=True)
class Registry:
    """Aggregate view of all members + roles + assignments.

    Built by load_registry(). Treat as immutable — rebuild from disk
    when YAML files change.
    """
    members: dict[str, Member]
    roles: dict[str, Role]
    workers: dict[str, Worker]
    assignments: tuple[Assignment, ...]
    delegation: dict                # raw parsed delegation.yaml

    # ------- Query helpers -------

    def member(self, member_id: str) -> Member:
        key = member_id.removeprefix("member.")
        if key not in self.members:
            raise KeyError(f"Unknown member: {member_id}")
        return self.members[key]

    def role(self, role_id: str) -> Role:
        key = role_id.removeprefix("role.")
        if key not in self.roles:
            raise KeyError(f"Unknown role: {role_id}")
        return self.roles[key]

    def worker(self, worker_id: str) -> Worker:
        key = worker_id.removeprefix("worker.")
        if key not in self.workers:
            raise KeyError(f"Unknown worker: {worker_id}")
        return self.workers[key]

    def active_assignments(self, *, role_id: Optional[str] = None,
                            member_id: Optional[str] = None
                            ) -> tuple[Assignment, ...]:
        """All assignments currently valid (no valid_until OR valid_until
        in the future), optionally filtered."""
        from datetime import date

        today = date.today().isoformat()

        def active(a: Assignment) -> bool:
            if a.valid_from and a.valid_from > today:
                return False
            if a.valid_until and a.valid_until < today:
                return False
            return True

        result = [a for a in self.assignments if active(a)]
        if role_id is not None:
            key = role_id.removeprefix("role.")
            result = [a for a in result if a.role_id == key]
        if member_id is not None:
            key = member_id.removeprefix("member.")
            result = [a for a in result if a.member_id == key]
        return tuple(result)

    def who_fills(self, role_id: str, *, primary_only: bool = False
                  ) -> tuple[Member, ...]:
        """Members currently assigned to the given role."""
        assigns = self.active_assignments(role_id=role_id)
        if primary_only:
            assigns = tuple(a for a in assigns if a.is_primary)
        return tuple(self.member(a.member_id) for a in assigns)

    def roles_of(self, member_id: str, *, primary_only: bool = False
                 ) -> tuple[Role, ...]:
        """Roles currently filled by the given member."""
        assigns = self.active_assignments(member_id=member_id)
        if primary_only:
            assigns = tuple(a for a in assigns if a.is_primary)
        return tuple(self.role(a.role_id) for a in assigns)

    def gate_signers(self, gate_reason: str) -> tuple[Role, ...]:
        """Roles authorized to sign gates of the given reason/type."""
        signers = self.delegation.get("gate_signers", {}).get(gate_reason)
        if signers is None:
            return ()
        if isinstance(signers, str):
            signers = [signers]
        return tuple(self.role(s) for s in signers if s.startswith("role."))


# ======================================================================
# Loader
# ======================================================================

def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_registry(*, validate: bool = True, org_dir: Optional[Path] = None) -> Registry:
    """Parse all org/ files and build a Registry.

    Parameters
    ----------
    validate : bool
        If True, check the invariants listed in delegation.yaml:
        - every role referenced exists
        - no delegation cycles
        - every escalation chain terminates at role.principal
        - authority roles have a primary assignment
        - every assignment's substrate is in the member's substrates
    org_dir : Path | None
        If provided, load from this directory instead of ORG_DIR. Used
        by schema-compatibility fixture tests to load frozen v1 org/
        snapshots without touching the live org/.

    Raises
    ------
    ValueError
        If validation fails. Contains a list of all invariant violations.
    """
    base = org_dir if org_dir is not None else ORG_DIR
    members_dir = base / "members"
    roles_dir = base / "roles"
    workers_dir = base / "workers"
    assignments_path = base / "assignments.yaml"
    delegation_path = base / "delegation.yaml"

    # Members
    members: dict[str, Member] = {}
    if members_dir.exists():
        for p in sorted(members_dir.glob("*.yaml")):
            data = _load_yaml(p)
            m = Member.from_yaml(data)
            members[m.member_id] = m

    # Roles
    roles: dict[str, Role] = {}
    if roles_dir.exists():
        for p in sorted(roles_dir.glob("*.yaml")):
            data = _load_yaml(p)
            r = Role.from_yaml(data)
            roles[r.role_id] = r

    # Workers
    workers: dict[str, Worker] = {}
    if workers_dir.exists():
        for p in sorted(workers_dir.glob("*.yaml")):
            data = _load_yaml(p)
            if not data:
                continue
            w = Worker.from_yaml(data)
            workers[w.worker_id] = w

    # Assignments
    assignments: list[Assignment] = []
    if assignments_path.exists():
        data = _load_yaml(assignments_path)
        for a in data.get("assignments", []) or []:
            assignments.append(Assignment(
                member_id=a["member"].removeprefix("member."),
                role_id=a["role"].removeprefix("role."),
                substrate=a["substrate"],
                is_primary=bool(a.get("is_primary", False)),
                valid_from=a.get("valid_from", ""),
                valid_until=a.get("valid_until"),
                notes=a.get("notes", ""),
            ))

    # Delegation graph
    delegation = _load_yaml(delegation_path) if delegation_path.exists() else {}

    registry = Registry(
        members=members,
        roles=roles,
        workers=workers,
        assignments=tuple(assignments),
        delegation=delegation,
    )

    if validate:
        errors = _validate(registry)
        if errors:
            raise ValueError(
                "org/ registry failed validation:\n  - "
                + "\n  - ".join(errors)
            )

    return registry


# ======================================================================
# Validation
# ======================================================================

def _validate(registry: Registry) -> list[str]:
    errors: list[str] = []

    # Every referenced role must exist
    known_roles = set(registry.roles.keys())
    known_members = set(registry.members.keys())
    known_workers = set(registry.workers.keys())

    for role in registry.roles.values():
        for target in role.delegates_to:
            if target.startswith("role."):
                key = target.removeprefix("role.")
                if key not in known_roles:
                    errors.append(
                        f"role.{role.role_id} delegates_to unknown role: {target}"
                    )
            elif target.startswith("worker."):
                key = target.removeprefix("worker.")
                if key not in known_workers:
                    errors.append(
                        f"role.{role.role_id} delegates_to unknown worker: {target}"
                    )
        for target in role.escalates_to:
            if target.startswith("role."):
                key = target.removeprefix("role.")
                if key not in known_roles:
                    errors.append(
                        f"role.{role.role_id} escalates_to unknown role: {target}"
                    )

    # Assignments
    for a in registry.assignments:
        if a.role_id not in known_roles:
            errors.append(
                f"assignment references unknown role: {a.role_id}"
            )
        if a.member_id not in known_members:
            errors.append(
                f"assignment references unknown member: {a.member_id}"
            )
        # Substrate sanity
        if a.member_id in registry.members:
            sub_names = {s.name for s in registry.members[a.member_id].substrates}
            if a.substrate not in sub_names:
                errors.append(
                    f"assignment {a.member_id} -> {a.role_id} uses substrate "
                    f"{a.substrate} which is not in member's substrates list"
                )

    # Authority roles need a primary assignment
    for role in registry.roles.values():
        if role.role_class == "authority":
            has_primary = any(
                a.is_primary and a.role_id == role.role_id
                and (a.valid_until is None or True)  # simple: ignore time bounds
                for a in registry.assignments
            )
            if not has_primary:
                errors.append(
                    f"authority role {role.role_id} has no primary assignment"
                )

    # Principal has no upstream
    if "principal" in registry.roles:
        if registry.roles["principal"].escalates_to:
            errors.append(
                "principal role must not have outgoing escalates_to edges"
            )

    # Escalation chains terminate at principal
    for role_id in known_roles:
        chain = []
        current = role_id
        seen = set()
        while current and current not in seen:
            seen.add(current)
            chain.append(current)
            role = registry.roles.get(current)
            if not role or not role.escalates_to:
                break
            nxt = role.escalates_to[0]
            if nxt.startswith("role."):
                current = nxt.removeprefix("role.")
            else:
                current = None
        if chain[-1] not in ("principal", None):
            if role_id != "principal":  # principal terminates itself
                errors.append(
                    f"escalation chain from {role_id} does not terminate at "
                    f"role.principal (got: {' -> '.join(chain)})"
                )

    # Gate signers consistency: delegation.yaml is authoritative.
    # Every (gate, role) pair in delegation.yaml.gate_signers must
    # appear in that role's signs_gates field, and vice versa.
    ds = registry.delegation.get("gate_signers", {}) or {}
    from_delegation: set[tuple[str, str]] = set()
    for gate, signers in ds.items():
        if isinstance(signers, str):
            signers = [signers]
        for s in signers:
            if not s.startswith("role."):
                continue
            role_key = s.removeprefix("role.")
            if role_key not in known_roles:
                errors.append(
                    f"delegation.yaml gate_signers[{gate}] references unknown role: {s}"
                )
                continue
            from_delegation.add((gate, role_key))

    from_roles: set[tuple[str, str]] = set()
    for role in registry.roles.values():
        for gate in role.signs_gates:
            from_roles.add((gate, role.role_id))

    only_in_delegation = from_delegation - from_roles
    only_in_roles = from_roles - from_delegation
    for gate, role_key in sorted(only_in_delegation):
        errors.append(
            f"gate {gate!r}: delegation.yaml lists role.{role_key} as signer, "
            f"but org/roles/{role_key}.yaml.signs_gates does not include it"
        )
    for gate, role_key in sorted(only_in_roles):
        errors.append(
            f"gate {gate!r}: role.{role_key}.signs_gates claims it, but "
            f"delegation.yaml.gate_signers does not list role.{role_key}"
        )

    # Delegation cycle detection (simple DFS)
    def has_cycle(start: str) -> bool:
        stack = [(start, [start])]
        while stack:
            cur, path = stack.pop()
            role = registry.roles.get(cur)
            if not role:
                continue
            for tgt in role.delegates_to:
                if not tgt.startswith("role."):
                    continue
                next_role = tgt.removeprefix("role.")
                if next_role in path:
                    return True
                stack.append((next_role, path + [next_role]))
        return False

    for role_id in known_roles:
        if has_cycle(role_id):
            errors.append(f"delegation cycle detected starting from {role_id}")

    return errors
