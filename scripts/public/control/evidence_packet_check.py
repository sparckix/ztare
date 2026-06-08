#!/usr/bin/env python3
"""Validate reviewer-facing evidence packets in docs/evidence_atlas/packets."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote


REPO = Path(__file__).resolve().parents[3]
PACKET_DIR = REPO / "docs/evidence_atlas/packets"

REQUIRED_SECTIONS = (
    "Scoped Claim",
    "Evidence Level",
    "Primary Sources",
    "Evidence Summary",
    "Non-Claims",
    "Missing Upgrade",
)

OPTIONAL_RUNNABLE_HEADINGS = (
    "Runnable Anchor",
    "Runnable Anchors",
    "Runnable Or Reproducible Anchors",
)

LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def _heading_names(text: str) -> set[str]:
    out: set[str] = set()
    for line in text.splitlines():
        match = re.match(r"^#{2,6}\s+(.+?)\s*$", line)
        if match:
            out.add(match.group(1).strip())
    return out


def _is_external(target: str) -> bool:
    return (
        target.startswith("http://")
        or target.startswith("https://")
        or target.startswith("mailto:")
        or target.startswith("#")
    )


def _link_path(source: Path, target: str) -> Path | None:
    raw = unquote(target.strip())
    raw = raw.split("#", 1)[0]
    if not raw or _is_external(raw):
        return None
    return (source.parent / raw).resolve()


def _check_packet(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    headings = _heading_names(text)
    missing = [section for section in REQUIRED_SECTIONS if section not in headings]
    if not any(section in headings for section in OPTIONAL_RUNNABLE_HEADINGS):
        missing.append("Runnable Anchor(s)")

    bad_links: list[str] = []
    local_links = 0
    for _label, target in LINK_RE.findall(text):
        resolved = _link_path(path, target)
        if resolved is None:
            continue
        local_links += 1
        try:
            resolved.relative_to(REPO)
        except ValueError:
            bad_links.append(f"{target} -> outside repo")
            continue
        if not resolved.exists():
            bad_links.append(target)

    return {
        "packet": str(path.relative_to(REPO)),
        "missing_sections": missing,
        "bad_links": bad_links,
        "local_links": local_links,
        "ok": not missing and not bad_links,
    }


def build_payload() -> dict[str, object]:
    packet_paths = sorted(
        p for p in PACKET_DIR.glob("*.md") if p.name != "README.md"
    )
    results = [_check_packet(path) for path in packet_paths]
    failures = [row for row in results if not row["ok"]]
    return {
        "ok": not failures,
        "packet_count": len(results),
        "failure_count": len(failures),
        "results": results,
    }


def main() -> int:
    payload = build_payload()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
