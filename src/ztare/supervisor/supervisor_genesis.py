from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ztare.common.paths import REPO_ROOT
from ztare.supervisor.supervisor_registry import (
    ProgramStatus,
    load_program_registry,
    registry_entry_map,
)
from ztare.supervisor.supervisor_seed_registry import (
    SeedStatus,
    load_seed_registry,
    seed_entry_by_spec_path,
)


@dataclass(frozen=True)
class ProgramGenesis:
    program_id: str
    seed_spec_path: str
    origin_programs: tuple[str, ...]
    origin_turn_refs: tuple[str, ...]
    problem_statement: str
    contract_boundary: str
    success_condition: str
    out_of_scope: tuple[str, ...]
    opened_date: str
    opened_by: str


def program_genesis_dir() -> Path:
    return REPO_ROOT / "supervisor" / "program_genesis"


def genesis_path_for_program(program_id: str) -> Path:
    return program_genesis_dir() / f"{program_id}.json"


def load_program_genesis(path: Path) -> ProgramGenesis:
    payload = json.loads(path.read_text())
    return ProgramGenesis(
        program_id=str(payload["program_id"]),
        seed_spec_path=str(payload["seed_spec_path"]),
        origin_programs=tuple(str(item) for item in payload.get("origin_programs", ())),
        origin_turn_refs=tuple(str(item) for item in payload.get("origin_turn_refs", ())),
        problem_statement=str(payload["problem_statement"]),
        contract_boundary=str(payload["contract_boundary"]),
        success_condition=str(payload["success_condition"]),
        out_of_scope=tuple(str(item) for item in payload.get("out_of_scope", ())),
        opened_date=str(payload["opened_date"]),
        opened_by=str(payload["opened_by"]),
    )


def load_optional_program_genesis(program_id: str) -> ProgramGenesis | None:
    path = genesis_path_for_program(program_id)
    if not path.exists():
        return None
    return load_program_genesis(path)


def validate_program_genesis(
    path: Path,
    *,
    registry_path: Path | None = None,
    seed_registry_path: Path | None = None,
) -> dict[str, object]:
    genesis = load_program_genesis(path)
    issues: list[str] = []

    seed_spec = REPO_ROOT / genesis.seed_spec_path
    if not seed_spec.exists():
        issues.append("seed_spec_path_missing")

    seed_registry = load_seed_registry(seed_registry_path)
    seeds_by_path = seed_entry_by_spec_path(seed_registry)
    seed_entry = seeds_by_path.get(genesis.seed_spec_path)
    if seed_entry is None:
        issues.append("seed_spec_not_registered")

    program_registry = load_program_registry(registry_path)
    programs = registry_entry_map(program_registry)
    for origin in genesis.origin_programs:
        entry = programs.get(origin)
        if entry is None:
            issues.append(f"origin_program_missing:{origin}")
            continue
        if entry.status not in {ProgramStatus.CLOSED, ProgramStatus.FROZEN}:
            issues.append(f"origin_program_not_closed_or_frozen:{origin}")

    if not genesis.out_of_scope:
        issues.append("out_of_scope_empty")

    passed = not issues
    return {
        "genesis_path": str(path),
        "program_id": genesis.program_id,
        "seed_spec_path": genesis.seed_spec_path,
        "passed": passed,
        "issues": issues,
    }
