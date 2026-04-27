"""GP-152 Framer Gates (v2.0): runtime safety checks for the Framer pipeline.

Three runtime gates + one canary:
  - G-LIB-COVER       library coverage (no in-library transform helps → fail)
  - G-FILTER-INDEP    SymmetryScanner ⊥ DimensionalFilter independence
  - G-SYM-FN          SymmetryScanner false-negative rate on canary substrates
  - framer_helped_canary  iatrogenesis detector (run inside frame())

Spec: research_areas/private/specs/active/GP-152_framer_architecture_spec_v2.md §4.
"""
from .library_coverage_gate import run_library_coverage_gate
from .filter_independence_gate import run_filter_independence_gate
from .symmetry_false_negative_gate import run_symmetry_false_negative_gate
from .framer_helped_canary import run_framer_helped_canary

__all__ = [
    "run_library_coverage_gate",
    "run_filter_independence_gate",
    "run_symmetry_false_negative_gate",
    "run_framer_helped_canary",
]
