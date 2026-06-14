#!/usr/bin/env python3
"""Validate reviewer-facing evidence packets in docs/evidence_atlas/packets."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote


REPO = Path(__file__).resolve().parents[3]
PACKET_DIR = REPO / "docs/evidence_atlas/packets"
CLAIM_CARDS = REPO / "docs/evidence_atlas/claim_cards.md"

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
EVIDENCE_LEVEL_RE = re.compile(r"\bL[0-5](?:\s*[-–]\s*L[0-5])?\b")

REQUIRED_CARD_FIELDS = (
    "Claim",
    "Evidence level",
    "Primary sources",
    "Runnable anchor",
    "Non-claims",
    "Next falsifier",
)


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

    evidence_section = _section_text(text, "Evidence Level")
    evidence_level_ok = bool(EVIDENCE_LEVEL_RE.search(evidence_section))
    if not evidence_level_ok:
        missing.append("Evidence Level value")

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
        "evidence_level_ok": evidence_level_ok,
        "ok": not missing and not bad_links,
    }


def _section_text(text: str, heading: str) -> str:
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$([\s\S]*?)(?=^##\s+|\Z)",
        re.MULTILINE,
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def _claim_card_chunks(text: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"^##\s+(Card\s+\d+:[^\n]+)\s*$", text, re.MULTILINE))
    chunks: list[tuple[str, str]] = []
    for idx, match in enumerate(matches):
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        chunks.append((match.group(1).strip(), text[match.end():end]))
    return chunks


def _field_present(chunk: str, field: str) -> bool:
    if field == "Runnable anchor":
        return bool(re.search(r"\*\*Runnable anchors?\.\*\*", chunk, re.IGNORECASE))
    return bool(re.search(rf"\*\*{re.escape(field)}\.\*\*", chunk, re.IGNORECASE))


def _check_local_links(source: Path, text: str) -> tuple[list[str], int]:
    bad_links: list[str] = []
    local_links = 0
    for _label, target in LINK_RE.findall(text):
        resolved = _link_path(source, target)
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
    return bad_links, local_links


def _check_claim_cards(path: Path | None = None) -> dict[str, object]:
    if path is None:
        path = CLAIM_CARDS
    text = path.read_text(encoding="utf-8")
    cards = _claim_card_chunks(text)
    results: list[dict[str, object]] = []
    for title, chunk in cards:
        missing = [field for field in REQUIRED_CARD_FIELDS if not _field_present(chunk, field)]
        evidence_text = ""
        match = re.search(
            r"\*\*Evidence level\.\*\*([\s\S]*?)(?=\n\*\*[A-Z][^*]+\.\*\*|\Z)",
            chunk,
            re.IGNORECASE,
        )
        if match:
            evidence_text = match.group(1)
        evidence_level_ok = bool(EVIDENCE_LEVEL_RE.search(evidence_text))
        if not evidence_level_ok:
            missing.append("Evidence level value")
        bad_links, local_links = _check_local_links(path, chunk)
        results.append(
            {
                "card": title,
                "missing_fields": missing,
                "bad_links": bad_links,
                "local_links": local_links,
                "evidence_level_ok": evidence_level_ok,
                "ok": not missing and not bad_links,
            }
        )
    failures = [row for row in results if not row["ok"]]
    return {
        "ok": bool(cards) and not failures,
        "card_count": len(cards),
        "failure_count": len(failures),
        "results": results,
    }


def build_payload() -> dict[str, object]:
    packet_paths = sorted(
        p for p in PACKET_DIR.glob("*.md") if p.name != "README.md"
    )
    results = [_check_packet(path) for path in packet_paths]
    failures = [row for row in results if not row["ok"]]
    claim_cards = _check_claim_cards()
    return {
        "ok": not failures and bool(claim_cards["ok"]),
        "packet_count": len(results),
        "failure_count": len(failures) + int(claim_cards["failure_count"]),
        "results": results,
        "claim_cards": claim_cards,
    }


def main() -> int:
    payload = build_payload()
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
