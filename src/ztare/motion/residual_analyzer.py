"""Compatibility wrapper for `ztare.motion.residual_diagnostics`.

Residual diagnostics used to live in this module under an older GP-era module
name. Keep this import path stable for older rubrics, artifacts, and downstream
scripts while new code imports the named capability directly.
"""
from __future__ import annotations

from ztare.motion.residual_diagnostics import *  # noqa: F401,F403
