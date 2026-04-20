from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from src.ztare.common.paths import REPO_ROOT


class ProgramStatus(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    FROZEN = "frozen"
    PROPOSED = "proposed"


class OwnerMode(str, Enum):
    DEBATE = "debate"
    IMPLEMENTATION = "implementation"
    FROZEN = "frozen"


@dataclass(frozen=True)
class ProgramRegistryEntry:
    program_id: str
    debate_file: str
    status: ProgramStatus
    last_turn: int
    reopen_condition: str | None
    owner_mode: OwnerMode


@dataclass(frozen=True)
class ProgramRegistry:
    programs: tuple[ProgramRegistryEntry, ...]


def registry_path() -> Path:
    return REPO_ROOT / "supervisor" / "program_registry.json"


def load_program_registry(path: Path | None = None) -> ProgramRegistry:
    target = path or registry_path()
    payload = json.loads(target.read_text())
    program_payload = payload.get("programs", {})
    entries: list[ProgramRegistryEntry] = []
    for program_id, entry in program_payload.items():
        entries.append(
            ProgramRegistryEntry(
                program_id=program_id,
                debate_file=str(entry["debate_file"]),
                status=ProgramStatus(str(entry["status"])),
                last_turn=int(entry["last_turn"]),
                reopen_condition=entry.get("reopen_condition"),
                owner_mode=OwnerMode(str(entry["owner_mode"])),
            )
        )
    return ProgramRegistry(programs=tuple(entries))


def registry_entry_map(registry: ProgramRegistry) -> dict[str, ProgramRegistryEntry]:
    return {entry.program_id: entry for entry in registry.programs}


def derive_closed_programs(registry: ProgramRegistry) -> tuple[str, ...]:
    return tuple(
        entry.program_id
        for entry in registry.programs
        if entry.status in {ProgramStatus.CLOSED, ProgramStatus.FROZEN}
    )


def validate_program_registry(path: Path | None = None) -> dict[str, object]:
    target = path or registry_path()
    registry = load_program_registry(target)
    results: list[dict[str, object]] = []
    all_passed = True

    for entry in registry.programs:
        debate_path = REPO_ROOT / entry.debate_file
        issues: list[str] = []
        observed_turn = None
        if not debate_path.exists():
            issues.append("debate_file_missing")
        else:
            observed_turn = _max_turn_in_file(debate_path)
            if observed_turn is not None and entry.last_turn > observed_turn:
                issues.append(
                    f"last_turn_exceeds_file_max:{entry.last_turn}>{observed_turn}"
                )
        if entry.status in {ProgramStatus.CLOSED, ProgramStatus.FROZEN} and entry.owner_mode != OwnerMode.FROZEN:
            issues.append("closed_or_frozen_program_requires_owner_mode_frozen")
        if entry.status == ProgramStatus.ACTIVE and entry.owner_mode == OwnerMode.FROZEN:
            issues.append("active_program_cannot_have_owner_mode_frozen")

        passed = not issues
        all_passed = all_passed and passed
        results.append(
            {
                "program_id": entry.program_id,
                "debate_file": entry.debate_file,
                "status": entry.status.value,
                "owner_mode": entry.owner_mode.value,
                "last_turn": entry.last_turn,
                "observed_turn": observed_turn,
                "passed": passed,
                "issues": issues,
            }
        )

    return {
        "registry_path": str(target),
        "all_passed": all_passed,
        "num_programs": len(registry.programs),
        "num_passed": sum(1 for item in results if item["passed"]),
        "results": results,
    }


def _max_turn_in_file(path: Path) -> int | None:
    pattern = re.compile(r"^## Turn (\d+) ")
    max_turn = None
    for line in path.read_text().splitlines():
        match = pattern.match(line)
        if match:
            turn = int(match.group(1))
            max_turn = turn if max_turn is None else max(max_turn, turn)
    return max_turn
