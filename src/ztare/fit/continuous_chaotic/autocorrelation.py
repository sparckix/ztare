"""Autocorrelation-based timescale extraction for continuous-chaotic substrates.

Canonical reference per docs/concepts/chaos_substrate_primitives.md Principle 2:
FFT peaks on chaotic broadband spectra are sampling artifacts, not physical
timescales. Use autocorrelation decorrelation time (1/e crossing) instead.

Single public function: autocorrelation_decorrelation_time.
"""
from __future__ import annotations

import numpy as np


def autocorrelation_decorrelation_time(trajectory: np.ndarray, dt: float) -> float:
    """Compute tau_decorr: first Delta_t where the normalized autocorrelation
    of the mean-centered trajectory magnitude drops below 1/e.

    Uses the Wiener-Khinchin route: autocorrelation = IFFT(|FFT(x)|^2). Note
    FFT here is used for COMPUTATION of the autocorrelation function, not to
    extract spectral peaks — that distinction matters per chaos-substrate
    Principle 2.

    Parameters
    ----------
    trajectory : array of shape (N, d)
        Full-state observation.
    dt : float
        Sampling interval.

    Returns
    -------
    float
        Decorrelation time in the same units as dt. Falls back to half
        the trajectory duration if no 1/e crossing is found.
    """
    x = trajectory - trajectory.mean(axis=0, keepdims=True)
    amp = np.linalg.norm(x, axis=1)
    amp = amp - amp.mean()
    n = amp.size
    nfft = 1 << int(np.ceil(np.log2(2 * n)))
    F = np.fft.rfft(amp, n=nfft)
    acf = np.fft.irfft(F * np.conj(F), n=nfft)[:n]
    acf = acf / acf[0]
    threshold = 1.0 / np.e
    below = np.where(acf < threshold)[0]
    if below.size == 0:
        return float(n * dt * 0.5)
    return float(below[0] * dt)
