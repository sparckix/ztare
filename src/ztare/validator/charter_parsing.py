"""Charter (project_charter.md) parsing helpers.

Split out of ``proxy_signature.py`` because the original module became
a junk drawer: it hosted proxy extraction, set distance, and charter
parsing despite being named after only the first concern. This module
owns the charter side: turning ``## Anchor Proxies`` and
``## Forecast Type`` sections into typed Python data.

Charter parsing for the deterministic charter gates (``## Deterministic
Gates``) lives in ``deterministic_charter_gates.py`` because that
parser ships alongside its evaluator. If a third charter section ever
needs parsing and is *not* coupled to its own evaluator, it belongs
here.
"""

from __future__ import annotations

import re


def normalize_anchor_proxy_name(name: str) -> str:
    """Canonicalize an anchor-proxy identifier.

    Anchor proxies declared in a charter may be written as either bare
    names (``slope_estimate``), test function names (``test_slope``),
    or already-prefixed identifiers (``proxy:slope_estimate``). This
    helper normalizes all three to the prefixed form so the drift
    comparison in ``compute_anchor_proxy_coverage`` is set-comparable.
    """

    normalized = name.strip()
    if not normalized:
        return ""
    if normalized.startswith(("proxy:", "test:", "unresolved:")):
        return normalized
    if normalized.startswith("test_"):
        return f"test:{normalized}"
    return f"proxy:{normalized}"


def normalize_forecast_type_name(name: str) -> str:
    """Map a free-text forecast type label to one of the canonical IDs.

    Returns ``""`` for an unrecognized label so callers can detect a
    parse failure rather than silently accepting bad input.
    """

    normalized = name.strip().lower().replace("`", "")
    aliases = {
        "none": "none",
        "no_forecast": "none",
        "directional": "directional_forecast",
        "directional_forecast": "directional_forecast",
        "bounded_directional": "directional_forecast",
        "bounded_directional_forecast": "directional_forecast",
        "probabilistic": "probabilistic_forecast",
        "probabilistic_forecast": "probabilistic_forecast",
        "point_probability": "probabilistic_forecast",
        "point_probability_forecast": "probabilistic_forecast",
    }
    return aliases.get(normalized, "")


def extract_forecast_type_from_charter(charter_text: str | None) -> str:
    """Read the ``## Forecast Type`` section, return the canonical ID.

    Returns ``""`` when the section is missing or its content does not
    map to a known forecast type.
    """

    if not charter_text:
        return ""

    lines = charter_text.splitlines()
    in_section = False
    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.startswith("## "):
            in_section = stripped == "## Forecast Type"
            continue
        if not in_section:
            continue
        if not stripped:
            continue
        if stripped.startswith("### "):
            break
        candidate = stripped
        if candidate.startswith("- "):
            candidate = candidate[2:].strip()
        normalized = normalize_forecast_type_name(candidate)
        if normalized:
            return normalized
    return ""


def extract_anchor_proxies_from_charter(charter_text: str | None) -> list[str]:
    """Read the ``## Anchor Proxies`` section, return normalized names.

    Each bullet under the heading becomes one entry. Order is preserved
    so callers that want stable diff output get it for free.
    """

    if not charter_text:
        return []

    lines = charter_text.splitlines()
    in_section = False
    anchors: list[str] = []
    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped.startswith("## "):
            in_section = stripped == "## Anchor Proxies"
            continue
        if not in_section:
            continue
        if not stripped:
            continue
        if stripped.startswith("### "):
            break
        match = re.match(r"^-\s+(.+?)\s*$", stripped)
        if not match:
            continue
        normalized = normalize_anchor_proxy_name(match.group(1))
        if normalized:
            anchors.append(normalized)
    return anchors
