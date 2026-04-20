from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha1


@dataclass(frozen=True)
class CommitteeBriefBinding:
    role: str
    persona: str
    focus_area: str
    profile_key: str


@dataclass(frozen=True)
class CommitteeInstantiationRecord:
    profile_source: str
    profile_keys: tuple[str, ...]
    committee_digest: str
    num_roles: int


def instantiate_fixed_committee(
    *,
    profile_source: str,
    role_keys: tuple[str, ...],
    role_definitions: dict[str, dict[str, str]],
) -> tuple[list[dict[str, str]], CommitteeInstantiationRecord]:
    committee: list[dict[str, str]] = []
    profile_keys: list[str] = []

    for role_key in role_keys:
        definition = role_definitions[role_key]
        binding = CommitteeBriefBinding(
            role=definition["role"],
            persona=definition["persona"],
            focus_area=definition["focus_area"],
            profile_key=role_key,
        )
        committee.append(
            {
                "role": binding.role,
                "persona": binding.persona,
                "focus_area": binding.focus_area,
            }
        )
        profile_keys.append(binding.profile_key)

    digest_input = "\n".join(
        f"{item['role']}|{item['persona']}|{item['focus_area']}" for item in committee
    )
    record = CommitteeInstantiationRecord(
        profile_source=profile_source,
        profile_keys=tuple(profile_keys),
        committee_digest=sha1(digest_input.encode("utf-8")).hexdigest(),
        num_roles=len(committee),
    )
    return committee, record


def record_to_dict(record: CommitteeInstantiationRecord) -> dict[str, object]:
    return asdict(record)
