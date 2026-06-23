"""Deterministic adversarial packet suite for residual/theorem proposals.

This is the PDE analogue of a cheap falsifier bench: the profile supplies
symbolic packet families and feature triggers; this runner says which packet
families are hit, which are merely triggered, and what escape theorem would be
needed before a proposal can claim novelty.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ztare.research_director.residual_normal_form import (
    extract_feature_hits,
    extract_feature_set,
    load_profile,
)


def run_packet_suite(text: str, profile: dict[str, Any]) -> dict[str, Any]:
    features = extract_feature_set(text, profile)
    feature_hits = extract_feature_hits(text, profile)
    return run_packet_suite_from_features(features, feature_hits, profile)


def run_packet_suite_from_features(
    features: set[str],
    feature_hits: list[dict[str, Any]],
    profile: dict[str, Any],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for packet in profile.get("packet_falsifiers", []):
        triggers = set(packet.get("triggers", []))
        trigger_mode = packet.get("trigger_mode", "any")
        kills_if_any = set(packet.get("kills_if_any", []))
        kills_if_all = set(packet.get("kills_if_all", []))
        blocked_by = set(packet.get("blocked_by_features", []))
        trigger_hits = sorted(triggers & features)
        any_hits = sorted(kills_if_any & features)
        all_hits = sorted(kills_if_all & features)
        blocked_hits = sorted(blocked_by & features)
        if blocked_hits:
            rows.append({
                "packet_id": packet.get("id"),
                "name": packet.get("name"),
                "status": "BLOCKED_BY_ESCAPE",
                "trigger_hits": trigger_hits,
                "kill_hits": sorted(set(any_hits) | set(all_hits)),
                "blocked_by_hits": blocked_hits,
                "what_it_tests": packet.get("what_it_tests"),
                "required_escape": packet.get("required_escape"),
            })
            continue
        if trigger_mode == "all":
            triggered = triggers.issubset(features)
        else:
            triggered = not triggers or bool(trigger_hits)
        countermodel_hit = triggered and (
            bool(any_hits) or (bool(kills_if_all) and kills_if_all.issubset(features))
        )
        if countermodel_hit:
            status = "COUNTERMODEL_HIT"
        elif triggered:
            status = "TRIGGERED_REQUIRES_ESCAPE_CHECK"
        else:
            status = "NOT_TRIGGERED"
        rows.append({
            "packet_id": packet.get("id"),
            "name": packet.get("name"),
            "status": status,
            "trigger_hits": trigger_hits,
            "kill_hits": sorted(set(any_hits) | set(all_hits)),
            "blocked_by_hits": [],
            "what_it_tests": packet.get("what_it_tests"),
            "required_escape": packet.get("required_escape"),
        })

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return {
        "profile_name": profile.get("name", "unnamed_profile"),
        "feature_hits": feature_hits,
        "status_counts": counts,
        "packets": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Run symbolic adversarial packet templates over a proposal."
    )
    ap.add_argument("--profile", required=True)
    ap.add_argument("--text")
    ap.add_argument("--text-file", action="append")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    chunks: list[str] = []
    if args.text:
        chunks.append(args.text)
    for path in args.text_file or []:
        chunks.append(Path(path).read_text(encoding="utf-8"))
    text = "\n".join(chunks)
    if not text.strip():
        raise SystemExit("provide --text or --text-file")

    result = run_packet_suite(text, load_profile(args.profile))
    if args.json:
        print(json.dumps(result, indent=2))
        return 0
    print(f"profile: {result['profile_name']}")
    print(f"status_counts: {result['status_counts']}")
    for row in result["packets"]:
        if row["status"] == "NOT_TRIGGERED":
            continue
        print(f"- {row['packet_id']}: {row['status']} -> {row['required_escape']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
