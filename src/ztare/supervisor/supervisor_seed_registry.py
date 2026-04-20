from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from src.ztare.common.paths import REPO_ROOT


class SeedStatus(str, Enum):
    DEFERRED = "deferred"
    CLOSED = "closed"
    ACTIVE = "active"


class SeedPipelineType(str, Enum):
    BUILD = "build"
    RESEARCH = "research"
    PRODUCT = "product"


@dataclass(frozen=True)
class SeedRegistryEntry:
    seed_id: str
    spec_path: str
    status: SeedStatus
    pipeline_type: SeedPipelineType
    summary: str
    decision_reason: str
    superseded_by: tuple[str, ...] = ()


@dataclass(frozen=True)
class SeedRegistry:
    seeds: tuple[SeedRegistryEntry, ...]


def seed_registry_path() -> Path:
    return REPO_ROOT / "research_areas" / "seed_registry.json"


def load_seed_registry(path: Path | None = None) -> SeedRegistry:
    target = path or seed_registry_path()
    payload = json.loads(target.read_text())
    seeds_payload = payload.get("seeds", {})
    entries: list[SeedRegistryEntry] = []
    for seed_id, entry in seeds_payload.items():
        entries.append(
            SeedRegistryEntry(
                seed_id=seed_id,
                spec_path=str(entry["spec_path"]),
                status=SeedStatus(str(entry["status"])),
                pipeline_type=SeedPipelineType(str(entry.get("pipeline_type", "build"))),
                summary=str(entry["summary"]),
                decision_reason=str(entry["decision_reason"]),
                superseded_by=tuple(str(item) for item in entry.get("superseded_by", ())),
            )
        )
    return SeedRegistry(seeds=tuple(entries))


def seed_entry_map(registry: SeedRegistry) -> dict[str, SeedRegistryEntry]:
    return {entry.seed_id: entry for entry in registry.seeds}


def seed_entry_by_spec_path(registry: SeedRegistry) -> dict[str, SeedRegistryEntry]:
    return {entry.spec_path: entry for entry in registry.seeds}


def validate_seed_registry(path: Path | None = None) -> dict[str, object]:
    target = path or seed_registry_path()
    registry = load_seed_registry(target)
    results: list[dict[str, object]] = []
    all_passed = True

    for entry in registry.seeds:
        issues: list[str] = []
        spec = REPO_ROOT / entry.spec_path
        if not spec.exists():
            issues.append("spec_path_missing")
        if entry.status == SeedStatus.CLOSED and not entry.superseded_by:
            issues.append("closed_seed_requires_superseded_by")
        passed = not issues
        all_passed = all_passed and passed
        results.append(
            {
                "seed_id": entry.seed_id,
                "spec_path": entry.spec_path,
                "status": entry.status.value,
                "pipeline_type": entry.pipeline_type.value,
                "passed": passed,
                "issues": issues,
            }
        )

    return {
        "registry_path": str(target),
        "all_passed": all_passed,
        "num_seeds": len(registry.seeds),
        "num_passed": sum(1 for item in results if item["passed"]),
        "results": results,
    }
