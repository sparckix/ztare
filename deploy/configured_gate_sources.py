#!/usr/bin/env python3
"""List/copy configured commit-membrane gate data sources.

The deploy manifest should describe generic code/config to ship to the VPS.
Substrate-specific relapse/amnesia data belongs in the structural-anchor
registry, then this helper resolves that config at deploy time.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Iterable

try:
    import yaml
except Exception as exc:  # pragma: no cover - deploy-time guard
    raise SystemExit(f"PyYAML is required to read structural anchors: {exc}")


GATE_ALLOWED_PREFIXES = ("projects/",)
VPS_SYNC_ALLOWED_PREFIXES = ("projects/", "ztare_proofs/")
REGISTRY_REL = Path("org/structural_anchors/registry.yaml")


def _valid_relpath(raw: object, *, allowed_prefixes: tuple[str, ...]) -> str:
    rel = str(raw or "").strip()
    if not rel:
        raise ValueError("empty path")
    p = Path(rel)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError(f"non repo-relative guard source path: {rel!r}")
    rel_posix = p.as_posix()
    if not any(rel_posix.startswith(prefix) for prefix in allowed_prefixes):
        raise ValueError(
            f"guard source {rel_posix!r} outside allowed prefixes "
            f"{allowed_prefixes}"
        )
    return rel_posix


def _iter_relapse_sources(registry: dict) -> Iterable[str]:
    for substrate, cfg in sorted(registry.items()):
        if substrate == "schema_version" or not isinstance(cfg, dict):
            continue
        gate_sources = cfg.get("gate_guard_sources") or {}
        raw_sources: list[object] = []
        if isinstance(gate_sources, dict):
            raw = gate_sources.get("relapse_fingerprint") or []
            raw_sources.extend(raw if isinstance(raw, list) else [raw])
        raw = cfg.get("relapse_guard_sources") or []
        raw_sources.extend(raw if isinstance(raw, list) else [raw])
        for raw_path in raw_sources:
            try:
                yield _valid_relpath(
                    raw_path,
                    allowed_prefixes=GATE_ALLOWED_PREFIXES,
                )
            except ValueError as exc:
                raise ValueError(
                    f"{substrate}: invalid configured gate source: {exc}"
                ) from exc


def _iter_vps_sync_sources(registry: dict) -> Iterable[str]:
    yield from _iter_relapse_sources(registry)
    for substrate, cfg in sorted(registry.items()):
        if substrate == "schema_version" or not isinstance(cfg, dict):
            continue
        raw_sources = cfg.get("vps_sync_sources") or []
        for raw_path in raw_sources if isinstance(raw_sources, list) else [raw_sources]:
            try:
                yield _valid_relpath(
                    raw_path,
                    allowed_prefixes=VPS_SYNC_ALLOWED_PREFIXES,
                )
            except ValueError as exc:
                raise ValueError(
                    f"{substrate}: invalid configured VPS sync source: {exc}"
                ) from exc


def configured_sources(repo: Path) -> list[str]:
    registry_path = repo / REGISTRY_REL
    if not registry_path.is_file():
        raise FileNotFoundError(f"structural-anchor registry missing: {registry_path}")
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    return sorted(set(_iter_relapse_sources(registry)))


def configured_vps_sync_sources(repo: Path) -> list[str]:
    registry_path = repo / REGISTRY_REL
    if not registry_path.is_file():
        raise FileNotFoundError(f"structural-anchor registry missing: {registry_path}")
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    return sorted(set(_iter_vps_sync_sources(registry)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="repo root to read from")
    ap.add_argument("--list", action="store_true", help="print configured sources")
    ap.add_argument("--list-vps-sync", action="store_true", help="print configured VPS sync sources")
    ap.add_argument("--check", action="store_true", help="verify configured sources exist")
    ap.add_argument("--copy-to", default="", help="copy configured sources under this repo-shaped root")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    try:
        sources = (
            configured_vps_sync_sources(repo)
            if args.list_vps_sync
            else configured_sources(repo)
        )
    except Exception as exc:
        print(f"configured_gate_sources: ERROR: {exc}", file=sys.stderr)
        return 2

    missing = [rel for rel in sources if not (repo / rel).is_file()]
    if missing:
        print(
            "configured_gate_sources: missing configured source(s): "
            + ", ".join(missing),
            file=sys.stderr,
        )
        return 1

    if args.list or args.list_vps_sync:
        for rel in sources:
            print(rel)

    if args.copy_to:
        dest_root = Path(args.copy_to).resolve()
        for rel in sources:
            src = repo / rel
            dst = dest_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        print(f"configured_gate_sources: copied {len(sources)} source(s)")

    if args.check and not args.list and not args.copy_to:
        print(f"configured_gate_sources: OK ({len(sources)} source(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
