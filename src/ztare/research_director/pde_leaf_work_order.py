"""Compatibility import path for PDE leaf work orders.

The canonical implementation lives in :mod:`ztare.pde.work_order`. This module
keeps existing RD workbench imports stable while the PDE subkernel owns the leaf
task schema.
"""
from __future__ import annotations

from ztare.pde.work_order import (
    PDELeafWorkOrder,
    build_pde_leaf_work_order,
    render_pde_leaf_work_order,
)

__all__ = [
    "PDELeafWorkOrder",
    "build_pde_leaf_work_order",
    "render_pde_leaf_work_order",
]
