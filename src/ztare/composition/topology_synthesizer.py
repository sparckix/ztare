"""Compatibility wrapper for `ztare.composition.symbolic_regression_synthesizer`.

Grammar-guided symbolic-regression synthesis used to live in this module under
an older GP-era module name. Keep this import path stable for older tests,
artifacts, and external scripts while new code imports the named capability
directly.
"""
from __future__ import annotations

from src.ztare.composition.symbolic_regression_synthesizer import *  # noqa: F401,F403
