"""Compatibility import path for PDE gate registry metadata.

The canonical implementation lives in :mod:`ztare.pde.registry`. This module
keeps existing RD workbench imports stable while the PDE subkernel owns the
registry.
"""
from __future__ import annotations

from ztare.pde.registry import (
    DEFAULT_PDE_GATE_REGISTRY,
    PDEGateRegistryEntry,
    all_pde_gate_entries,
    entries_for_op,
    entry_by_gate_id,
)

__all__ = [
    "DEFAULT_PDE_GATE_REGISTRY",
    "PDEGateRegistryEntry",
    "all_pde_gate_entries",
    "entries_for_op",
    "entry_by_gate_id",
]
