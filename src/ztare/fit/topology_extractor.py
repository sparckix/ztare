"""Extract the dominant topology from Phase 1 LLM proposals.

Reads fit_result_iter_*.json from the workspace, classifies each
proposal's topology, and returns the consensus topology class.
Phase 2 can then prioritize templates from that class.

Usage:
    from ztare.fit.topology_extractor import extract_dominant_topology
    topo = extract_dominant_topology(project_dir)
    # topo = {"class": "sqrt_log", "confidence": 0.73, "proposals": 15}
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path


def classify_topology(expression: str) -> str:
    """Classify a mathematical expression into a topology class."""
    expr = expression.lower()

    if "exp" in expr and "sqrt" in expr:
        return "exp_sqrt"
    if "exp" in expr:
        return "exponential"
    if "sqrt" in expr and "log" in expr:
        return "sqrt_log"
    if "sqrt" in expr:
        return "sqrt"
    if "sin" in expr or "cos" in expr:
        return "periodic"
    if "log" in expr and "**" in expression:
        return "log_polynomial"
    if "log" in expr:
        return "logarithmic"
    if "**" in expression:
        return "power_law"
    return "other"


def extract_dominant_topology(project_dir: Path) -> dict:
    """Read Phase 1 proposals and return the dominant topology class.

    Returns:
        {
            "class": "sqrt_log",
            "confidence": 0.73,
            "proposals_analyzed": 15,
            "distribution": {"sqrt_log": 11, "exponential": 3, "other": 1},
            "priority_templates": ["sqrt_log", "sqrt_log_reciprocal", ...]
        }
    """
    workspace = project_dir / "workspace"
    if not workspace.exists():
        return {"class": "unknown", "confidence": 0, "proposals_analyzed": 0}

    topology_counts = Counter()
    total = 0

    for fit_path in sorted(workspace.glob("fit_result_iter_*.json")):
        try:
            fit = json.loads(fit_path.read_text(encoding="utf-8"))
            expr = fit.get("expression", "")
            if not expr:
                continue
            topo = classify_topology(expr)
            topology_counts[topo] += 1
            total += 1
        except Exception:
            continue

    if total == 0:
        return {"class": "unknown", "confidence": 0, "proposals_analyzed": 0}

    dominant, count = topology_counts.most_common(1)[0]
    confidence = count / total

    # Map topology class to template names for priority ordering
    template_priority = {
        "sqrt_log": ["sqrt_log", "sqrt_log_reciprocal", "sqrt_log_recip2",
                     "power_log", "power_log_recip"],
        "logarithmic": ["log_affine", "log_reciprocal", "log_scaled",
                        "loglog_affine", "loglog_reciprocal",
                        "log_power_free", "log_power_reciprocal",
                        "log_shifted_reciprocal"],
        "exponential": ["exp_decay_offset", "stretched_exp",
                       "exp_decay_linear", "power_exp_decay",
                       "two_exp_decay", "stretched_exp_log"],
        "power_law": ["power_free", "power_decay", "power_log"],
        "periodic": ["sin_affine", "cos_affine", "sin_decay",
                    "log_plus_sin", "linear_plus_sin"],
    }

    return {
        "class": dominant,
        "confidence": round(confidence, 3),
        "proposals_analyzed": total,
        "distribution": dict(topology_counts),
        "priority_templates": template_priority.get(dominant, []),
    }
