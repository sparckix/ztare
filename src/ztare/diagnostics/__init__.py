"""GP-166 Statistical Meta-Diagnostics — ZTARE 3.0.

The apparatus stops assuming the data's epistemology and starts
measuring it. Pre-flight tests for heteroscedasticity, non-Gaussian
residuals, autocorrelation, and errors-in-X auto-route the solver
architecture before iter 1 begins.
"""
from src.ztare.diagnostics.noise_profile import (
    NoiseProfile,
    classify_noise_profile,
    auto_route_solver,
)

__all__ = ["NoiseProfile", "classify_noise_profile", "auto_route_solver"]
