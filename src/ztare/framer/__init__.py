"""GP-152 Framer — pre-solver representation search (v2.0).

Public API:
  frame(x, y, meta, rubric_data) -> (framed_x, framed_y, framing_report)
  fit_with_framer(fit_fn, evidence_text, decl, score_mode, rubric_data) -> fit_result

Spec: research_areas/private/specs/active/GP-152_framer_architecture_spec_v2.md
Backtest: scripts/framer/backtest_framer_mdl_v2_vs_v1.py
"""
from .active_framer import frame
from .solver_wrapper import fit_with_framer

__all__ = ["frame", "fit_with_framer"]
