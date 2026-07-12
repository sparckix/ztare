"""Grid quantity plugin for the general invariant bridge (GP-250).

Registers the grid-specific quantity kinds; re-exports the substrate-agnostic
certificate machinery so worldmodel callers keep one import.
"""

from __future__ import annotations

from ztare.common.invariant_certificate import (   # noqa: F401 — re-export
    InvariantCertificate, admissible, enforced, register_quantity)


def _count(grid, color) -> int:
    return sum(1 for row in grid for v in row if v == color)


register_quantity("count", _count)


def prediction_is_admissible(certs, before, after) -> bool:
    """A predicted successor is admissible unless it violates an enforced
    (kernel-ratified) invariant — theorem-impossible transitions are dropped,
    never real reachable states."""
    return admissible(certs, before, after)


import re as _re


def invariant_from_theorem(statement: str, status: str = "conjectured",
                           theorem: str = "") -> "InvariantCertificate | None":
    """DETERMINISTIC theorem-statement -> certificate (external-review #3: even
    the certificate must not be LLM-written). Parses the exact generated shape
    `countColor (specStep ...) C <relation> countColor g C`; returns None if it
    does not match (never guesses). The proof's PARAMETERS are extracted by
    regex over the STATEMENT; the quantity CODE is the fixed registered `count`
    function — so no code is ever synthesized from a proof."""
    body = statement.replace("\n", " ")
    m = _re.search(r"countColor\s*\(\s*specStep[^)]*\)\s*(\d+)\s*(≤|<=|≥|>=|=)\s*"
                   r"countColor\s+\w+\s+(\d+)", body)
    if not m:
        return None
    c_out, rel, c_in = int(m.group(1)), m.group(2), int(m.group(3))
    if c_out != c_in:
        return None
    relation = {"≤": "non_increasing", "<=": "non_increasing",
                "≥": "non_decreasing", ">=": "non_decreasing",
                "=": "constant"}[rel]
    return InvariantCertificate(("count", c_out), relation, status, theorem)
