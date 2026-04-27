"""GP-128 AI-Native M-Form primitives: members, roles, assignments.

Three peer dataclasses loaded from `org/members/`, `org/roles/`, and
`org/assignments.yaml` respectively. A registry aggregates them and
exposes queries by member_id / role_id / gate type. Mandates are
referenced by role but not parsed — they are principal-facing markdown.

See `org/README.md` for the organizing conventions.
"""

from .loader import (
    Role, Member, Assignment, Registry,
    load_registry, ROLES_DIR, MEMBERS_DIR, ASSIGNMENTS_PATH, DELEGATION_PATH,
)

__all__ = [
    "Role", "Member", "Assignment", "Registry",
    "load_registry",
    "ROLES_DIR", "MEMBERS_DIR", "ASSIGNMENTS_PATH", "DELEGATION_PATH",
]
