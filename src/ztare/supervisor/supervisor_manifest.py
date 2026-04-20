from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

from src.ztare.common.paths import REPO_ROOT


class ManifestPacketStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    BLOCKED = "blocked"
    DEFERRED = "deferred"


@dataclass(frozen=True)
class ManifestPacket:
    packet_id: str
    title: str
    status: ManifestPacketStatus
    target: str
    summary: str
    depends_on: tuple[str, ...] = ()
    allowed_artifacts: tuple[str, ...] = ()
    read_bundle: tuple[str, ...] = ()
    token_budget: dict[str, int] | None = None
    success_condition: str | None = None
    verification_command: str | None = None


@dataclass(frozen=True)
class ProgramManifest:
    program_id: str
    completion_policy: str
    packets: tuple[ManifestPacket, ...]
    auto_promote_contract_promotion: bool | None = None
    bundle_invariants: tuple[str, ...] = ()
    document_manifest_path: str | None = None
    api_prompt_versions: dict[str, str] | None = None


def manifest_directory() -> Path:
    return REPO_ROOT / "supervisor" / "program_manifests"


def manifest_path_for_program(program_id: str) -> Path:
    return manifest_directory() / f"{program_id}.json"


def load_optional_program_manifest(program_id: str) -> ProgramManifest | None:
    path = manifest_path_for_program(program_id)
    if not path.exists():
        return None
    payload = _read_manifest_payload(path)
    packets = tuple(
        ManifestPacket(
            packet_id=str(item["packet_id"]),
            title=str(item["title"]),
            status=ManifestPacketStatus(str(item["status"])),
            target=str(item["target"]),
            summary=str(item["summary"]),
            depends_on=tuple(str(dep) for dep in item.get("depends_on", ())),
            allowed_artifacts=tuple(str(path) for path in item.get("allowed_artifacts", ())),
            read_bundle=tuple(str(path) for path in item.get("read_bundle", ())),
            token_budget=(
                {
                    str(key): int(value)
                    for key, value in dict(item.get("token_budget", {})).items()
                    if value is not None
                }
                or None
            ),
            success_condition=item.get("success_condition"),
            verification_command=item.get("verification_command"),
        )
        for item in payload.get("packets", ())
    )
    return ProgramManifest(
        program_id=str(payload["program_id"]),
        completion_policy=str(payload.get("completion_policy", "manifest_exhausted_to_D")),
        auto_promote_contract_promotion=(
            bool(payload["auto_promote_contract_promotion"])
            if payload.get("auto_promote_contract_promotion") is not None
            else None
        ),
        bundle_invariants=tuple(str(path) for path in payload.get("bundle_invariants", ())),
        document_manifest_path=(
            str(payload["document_manifest_path"])
            if payload.get("document_manifest_path") is not None
            else None
        ),
        api_prompt_versions=(
            {
                str(key): str(value)
                for key, value in dict(payload.get("api_prompt_versions", {})).items()
                if value is not None
            }
            or None
        ),
        packets=packets,
    )


def _read_manifest_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def _write_manifest_payload(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def next_manifest_packet(manifest: ProgramManifest | None) -> ManifestPacket | None:
    if manifest is None:
        return None
    for packet in manifest.packets:
        if packet.status in {ManifestPacketStatus.PENDING, ManifestPacketStatus.IN_PROGRESS}:
            return packet
    return None


def packet_for_target(
    manifest: ProgramManifest | None,
    *,
    target: str,
) -> ManifestPacket | None:
    if manifest is None:
        return None
    for packet in manifest.packets:
        if packet.target == target:
            return packet
    return None


def packet_for_id(
    manifest: ProgramManifest | None,
    *,
    packet_id: str,
) -> ManifestPacket | None:
    if manifest is None:
        return None
    for packet in manifest.packets:
        if packet.packet_id == packet_id:
            return packet
    return None


def derive_packet_read_bundle(
    manifest: ProgramManifest | None,
    *,
    packet: ManifestPacket | None = None,
    packet_id: str | None = None,
    target: str | None = None,
) -> tuple[str, ...]:
    if manifest is None:
        return ()
    resolved_packet = packet
    if resolved_packet is None and packet_id is not None:
        resolved_packet = packet_for_id(manifest, packet_id=packet_id)
    if resolved_packet is None and target is not None:
        resolved_packet = packet_for_target(manifest, target=target)
    if resolved_packet is None:
        return ()

    bundle: list[str] = list(manifest.bundle_invariants)
    for dependency_id in resolved_packet.depends_on:
        dependency = packet_for_id(manifest, packet_id=dependency_id)
        if dependency is None:
            continue
        bundle.extend(str(path) for path in dependency.allowed_artifacts if path)
    bundle.extend(str(path) for path in resolved_packet.allowed_artifacts if path)
    bundle.extend(str(path) for path in resolved_packet.read_bundle if path)
    return tuple(dict.fromkeys(bundle))


def should_auto_promote_contract_promotion(manifest: ProgramManifest | None) -> bool:
    if manifest is None:
        return False
    if manifest.auto_promote_contract_promotion is not None:
        return manifest.auto_promote_contract_promotion
    return manifest.document_manifest_path is None


def advance_manifest_packet(
    program_id: str,
    *,
    packet_id: str | None = None,
    target: str | None = None,
) -> dict[str, object]:
    path = manifest_path_for_program(program_id)
    if not path.exists():
        return {
            "manifest_path": str(path),
            "updated": False,
            "completed_packet_id": None,
            "unblocked_packet_ids": [],
            "reason": "manifest_missing",
        }

    payload = _read_manifest_payload(path)
    packets = list(payload.get("packets", ()))
    if not packets:
        return {
            "manifest_path": str(path),
            "updated": False,
            "completed_packet_id": None,
            "unblocked_packet_ids": [],
            "reason": "manifest_empty",
        }

    target_index: int | None = None
    for index, packet in enumerate(packets):
        status = str(packet.get("status", ""))
        packet_matches = False
        if packet_id is not None and str(packet.get("packet_id")) == packet_id:
            packet_matches = True
        elif (
            packet_id is None
            and target is not None
            and status in {
                ManifestPacketStatus.PENDING.value,
                ManifestPacketStatus.IN_PROGRESS.value,
            }
            and str(packet.get("target")) == target
        ):
            packet_matches = True
        elif (
            packet_id is None
            and target is None
            and status in {
                ManifestPacketStatus.PENDING.value,
                ManifestPacketStatus.IN_PROGRESS.value,
            }
        ):
            packet_matches = True
        if packet_matches:
            target_index = index
            break

    if target_index is None:
        return {
            "manifest_path": str(path),
            "updated": False,
            "completed_packet_id": None,
            "unblocked_packet_ids": [],
            "reason": "packet_not_found",
        }

    completed_packet = packets[target_index]
    if str(completed_packet.get("status")) != ManifestPacketStatus.COMPLETE.value:
        completed_packet["status"] = ManifestPacketStatus.COMPLETE.value

    completed_ids = {
        str(packet.get("packet_id"))
        for packet in packets
        if str(packet.get("status")) == ManifestPacketStatus.COMPLETE.value
    }
    unblocked_packet_ids: list[str] = []
    for packet in packets:
        if str(packet.get("status")) != ManifestPacketStatus.BLOCKED.value:
            continue
        dependencies = [str(dep) for dep in packet.get("depends_on", ())]
        if dependencies and all(dependency in completed_ids for dependency in dependencies):
            packet["status"] = ManifestPacketStatus.PENDING.value
            unblocked_packet_ids.append(str(packet.get("packet_id")))

    _write_manifest_payload(path, payload)
    return {
        "manifest_path": str(path),
        "updated": True,
        "completed_packet_id": str(completed_packet.get("packet_id")),
        "unblocked_packet_ids": unblocked_packet_ids,
        "reason": "manifest_advanced",
    }


def manifest_summary(manifest: ProgramManifest | None) -> dict[str, object] | None:
    if manifest is None:
        return None
    next_packet = next_manifest_packet(manifest)
    return {
        "manifest_path": str(manifest_path_for_program(manifest.program_id)),
        "completion_policy": manifest.completion_policy,
        "auto_promote_contract_promotion": should_auto_promote_contract_promotion(manifest),
        "bundle_invariants": list(manifest.bundle_invariants),
        "document_manifest_path": manifest.document_manifest_path,
        "api_prompt_versions": dict(manifest.api_prompt_versions or {}),
        "next_packet": (
            {
                "packet_id": next_packet.packet_id,
                "title": next_packet.title,
                "status": next_packet.status.value,
                "target": next_packet.target,
                "summary": next_packet.summary,
                "allowed_artifacts": list(next_packet.allowed_artifacts),
                "read_bundle": list(next_packet.read_bundle),
                "derived_read_bundle": list(
                    derive_packet_read_bundle(manifest, packet=next_packet)
                ),
                "token_budget": dict(next_packet.token_budget or {}),
                "success_condition": next_packet.success_condition,
                "verification_command": next_packet.verification_command,
            }
            if next_packet is not None
            else None
        ),
        "num_packets": len(manifest.packets),
        "num_complete": sum(
            1 for packet in manifest.packets if packet.status == ManifestPacketStatus.COMPLETE
        ),
        "num_pending_like": sum(
            1
            for packet in manifest.packets
            if packet.status in {ManifestPacketStatus.PENDING, ManifestPacketStatus.IN_PROGRESS}
        ),
    }


def validate_program_manifest(program_id: str) -> dict[str, object]:
    manifest = load_optional_program_manifest(program_id)
    issues: list[str] = []
    if manifest is None:
        issues.append("manifest_missing")
        return {
            "program_id": program_id,
            "passed": False,
            "issues": issues,
        }
    if manifest.program_id != program_id:
        issues.append(f"program_id_mismatch:{manifest.program_id}")

    packet_ids: set[str] = set()
    for packet in manifest.packets:
        if packet.packet_id in packet_ids:
            issues.append(f"duplicate_packet_id:{packet.packet_id}")
        packet_ids.add(packet.packet_id)
        for dependency in packet.depends_on:
            if dependency == packet.packet_id:
                issues.append(f"self_dependency:{packet.packet_id}")
    for packet in manifest.packets:
        for dependency in packet.depends_on:
            if dependency not in packet_ids:
                issues.append(f"missing_dependency:{packet.packet_id}->{dependency}")

    return {
        "program_id": program_id,
        "manifest_path": str(manifest_path_for_program(program_id)),
        "passed": not issues,
        "issues": issues,
    }
