#!/usr/bin/env python3
"""Compatibility wrapper for scripts/public/models/gnn_lemma_relevance/v31_candidate_generator.py."""

from __future__ import annotations

import runpy
from pathlib import Path

runpy.run_path(
    str(Path(__file__).resolve().parent / "gnn_lemma_relevance" / "v31_candidate_generator.py"),
    run_name="__main__",
)
