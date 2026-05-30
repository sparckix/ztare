"""LLM-driven persona routing (GP-079).

Maps observed failure families to domain reviewer personas. Three-tier
resolution: pick from the static catalog (``config/prompts/``), generate
a dynamic persona inline if no good match, promote effective dynamic
personas back to the static set.

Driven by what the current run is failing at, not by ground-truth
knowledge. Public entry is
``select_personas_for_iteration(failure_families, seam_context)``.
"""
