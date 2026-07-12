"""PDE estimate-skeleton facade."""
from __future__ import annotations

from typing import Any

from ztare.research_director.pde_estimate_skeleton import (
    generate_estimate_skeletons,
)


def generate_pde_estimate_skeletons(
    *,
    target: str,
    field: str | None = None,
    gap_type: str | None = None,
    context: dict[str, Any] | None = None,
    inequalities: list[str] | tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """Return substrate-neutral PDE estimate skeletons for a target surface."""
    return generate_estimate_skeletons(
        target=target,
        field=field,
        gap_type=gap_type,
        context=context,
        inequalities=list(inequalities or []),
    )
