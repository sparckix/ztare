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

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class AsymptoticClaimContract:
    """Optional charter-declared asymptotic-claim contract.

    This is intentionally small for GP-046 first slice:
    - ``asymptotic_claim`` says the project explicitly seeks global-tail /
      asymptotic-mechanism credit.
    - ``farther_tail_contract`` says the charter also declares an external
      farther-tail test surface, typically via a hidden holdout.
    - ``declared`` records whether the section exists at all.
    """

    declared: bool = False
    asymptotic_claim: bool = False
    farther_tail_contract: bool = False


def _parse_boolish(value: str | None) -> bool:
    normalized = (value or "").strip().lower().replace("`", "")
    return normalized in {"true", "yes", "y", "1", "on"}


def _collect_section_lines(charter_text: str | None, heading: str) -> tuple[bool, list[str]]:
    """Collect all non-heading lines under a ``##`` section.

    Accepts both fenced and unfenced key-value bodies so the first slice can
    ship without forcing a single charter authoring style.
    """

    if not charter_text:
        return False, []

    lines = charter_text.splitlines()
    in_section = False
    section_found = False
    collected: list[str] = []
    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.startswith("## "):
            if in_section:
                break
            in_section = stripped == heading
            section_found = section_found or in_section
            continue
        if not in_section:
            continue
        if stripped.startswith("### "):
            break
        if stripped.startswith("```"):
            continue
        if stripped:
            collected.append(raw_line.rstrip())
    return section_found, collected


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


def extract_asymptotic_claim_contract_from_charter(
    charter_text: str | None,
) -> AsymptoticClaimContract:
    """Read the optional ``## Asymptotic Claim Contract`` section.

    Accepted keys:
    - ``asymptotic_claim: true|false``
    - ``farther_tail_contract: true|false``

    Missing section returns the fully-false default contract.
    """

    found, lines = _collect_section_lines(charter_text, "## Asymptotic Claim Contract")
    if not found:
        return AsymptoticClaimContract()

    fields: dict[str, str] = {}
    for raw_line in lines:
        stripped = raw_line.strip()
        if stripped.startswith("- "):
            stripped = stripped[2:].strip()
        if ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        fields[key.strip().lower()] = value.strip()

    return AsymptoticClaimContract(
        declared=True,
        asymptotic_claim=_parse_boolish(fields.get("asymptotic_claim")),
        farther_tail_contract=_parse_boolish(fields.get("farther_tail_contract")),
    )


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
