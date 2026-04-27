"""GP-152 Framer Component F — ReportWriter (v2.0).

Serializes the framing decision and provenance into a dict that travels
with the framed data through the pipeline.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .search import MDLResult


def build_framing_report(
    best: Optional[MDLResult],
    baseline: Optional[MDLResult],
    all_results: List[MDLResult],
    sym_report,
    enumeration_summary: Dict[str, int],
    framer_engaged: bool,
    disabled_reason: Optional[str] = None,
    canary: Optional[Dict[str, Any]] = None,
    gates: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Construct the framing_report dict. Schema matches spec v2.0 §4."""
    if best is not None and baseline is not None:
        mdl_gain_bits = (baseline.mdl - best.mdl) / 0.6931471805599453  # log(2)
    else:
        mdl_gain_bits = 0.0

    scores_top10 = [
        {
            "h_in": r.pair.h_in.name,
            "h_out": r.pair.h_out.name,
            "mdl": float(r.mdl),
            "sigma_sq_raw": float(r.sigma_sq_raw),
        }
        for r in all_results[:10]
    ]

    return {
        "framer_engaged": framer_engaged,
        "disabled_reason": disabled_reason,
        "h_in": best.pair.h_in.name if best else "identity",
        "h_out": best.pair.h_out.name if best else "identity",
        "h_out_inv": (best.pair.h_out.name if best else "identity") + "_inv",
        "MDL_v2": float(best.mdl) if best else None,
        "MDL_v2_baseline": float(baseline.mdl) if baseline else None,
        "MDL_gain_bits": float(mdl_gain_bits),
        "sigma_sq_raw_chosen": float(best.sigma_sq_raw) if best else None,
        "scores_top10": scores_top10,
        "enumeration": enumeration_summary,
        "symmetry_report": {
            "power_law_alpha": sym_report.power_law_alpha,
            "is_power_law": sym_report.is_power_law,
            "translation_invariant": sym_report.translation_invariant,
            "notes": sym_report.notes,
            "suggested_h_in": sym_report.suggested_h_in,
            "suggested_h_out": sym_report.suggested_h_out,
        },
        "gates": gates or {},
        "canary": canary,
    }
