"""Compatibility import path for PDE formal-feedback cards.

The canonical implementation lives in :mod:`ztare.pde.formal_feedback`.
LeanMill remains the service provider for premise retrieval, typed exits, proof
cache, and repair memory; PDE only adapts those signals into leaf work.
"""
from __future__ import annotations

from ztare.pde.formal_feedback import (
    PDEFormalFeedbackCard,
    build_pde_formal_feedback_card,
    render_pde_formal_feedback_card,
)

__all__ = [
    "PDEFormalFeedbackCard",
    "build_pde_formal_feedback_card",
    "render_pde_formal_feedback_card",
]
