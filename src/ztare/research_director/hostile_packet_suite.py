"""Generic hostile-packet suite helpers for PDE execution mode."""
from __future__ import annotations

from typing import Any


def build_hostile_packet_suite(
    suite_id: str,
    packets: list[dict[str, Any]],
    packet_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Normalize substrate-supplied hostile packet specs.

    Substrates own packet content. This src helper owns only the shape that RD
    workbenches and gates consume.
    """
    if packet_ids:
        keep = set(packet_ids)
        packets = [packet for packet in packets if packet["id"] in keep]
    return {
        "suite": suite_id,
        "packets": packets,
        "required_result_fields": [
            "satisfies_hypotheses",
            "violates_conclusion",
            "verdict",
            "reason",
        ],
    }
