"""GP-110 — Statistical Fingerprint for UNDERIDENTIFIED sequences.

When the compression primitive (Stages 1-3) returns UNDERIDENTIFIED, this module
computes a typed statistical characterization of the residual structure:
spectral slope, Hurst exponent, amplitude envelope, phase linearity, and
arithmetic decomposition.

This is NOT a formula. It is a fingerprint — telling you WHAT KIND of object
the data is, even when you cannot write f(n).

All computations are deterministic. No LLM in the loop.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

try:
    import numpy as np
    from scipy.signal import lombscargle, hilbert, welch
    from scipy.optimize import curve_fit
    _SCIPY = True
except ImportError:
    _SCIPY = False


@dataclass(frozen=True)
class StatisticalFingerprint:
    spectral_slope: float
    spectral_slope_r2: float
    dominant_period: float | None
    spectral_bandwidth: float
    hurst_exponent: float
    phase_linearity_residual: float
    is_quasiperiodic: bool
    envelope_exponent: float
    envelope_prefactor: float
    arithmetic_energy_fraction: float
    detrend_method: str
    n_points: int
    n_range: tuple[float, float]
    hurst_slope_consistent: bool
    multi_window_slopes: tuple[tuple[int, float], ...] = ()  # (window, slope) pairs
    detrending_sensitive: bool = False  # True if slope varies by >0.3 across windows

    def summary_line(self) -> str:
        persistence = "anti-persistent" if self.hurst_exponent < 0.4 else "persistent" if self.hurst_exponent > 0.6 else "uncorrelated"
        spectral = f"1/f^{abs(self.spectral_slope):.2f}" if 0.5 < abs(self.spectral_slope) < 1.5 else f"slope={self.spectral_slope:.2f}"
        periodic = f"T={self.dominant_period:.1f}" if self.dominant_period else "broadband"
        phase = "quasi-periodic" if self.is_quasiperiodic else "non-periodic"
        return (
            f"CHARACTERIZED: {spectral}, {persistence} (H={self.hurst_exponent:.3f}), "
            f"{periodic}, {phase}, envelope~n^(-{self.envelope_exponent:.2f}), "
            f"arith={self.arithmetic_energy_fraction:.0%}"
        )

    def to_dict(self) -> dict:
        return {
            "spectral_slope": self.spectral_slope,
            "spectral_slope_r2": self.spectral_slope_r2,
            "dominant_period": self.dominant_period,
            "spectral_bandwidth": self.spectral_bandwidth,
            "hurst_exponent": self.hurst_exponent,
            "phase_linearity_residual": self.phase_linearity_residual,
            "is_quasiperiodic": self.is_quasiperiodic,
            "envelope_exponent": self.envelope_exponent,
            "envelope_prefactor": self.envelope_prefactor,
            "arithmetic_energy_fraction": self.arithmetic_energy_fraction,
            "detrend_method": self.detrend_method,
            "n_points": self.n_points,
            "n_range": list(self.n_range),
            "hurst_slope_consistent": bool(self.hurst_slope_consistent),
            "multi_window_slopes": [{"window": w, "slope": s} for w, s in self.multi_window_slopes],
            "detrending_sensitive": bool(self.detrending_sensitive),
            "summary": self.summary_line(),
        }


def compute_fingerprint(
    x: "np.ndarray",
    y: "np.ndarray",
    y_smooth: "np.ndarray",
    *,
    detrend_window: int | None = None,
) -> StatisticalFingerprint | None:
    """Compute statistical fingerprint of residuals after best smooth model."""
    if not _SCIPY:
        return None

    residual = y - y_smooth
    n = len(residual)
    if n < 100:
        return None

    # 1. Multi-window detrending (Munger: don't bet on one window)
    # Compute spectral slope at multiple windows to detect detrending sensitivity
    _windows_to_test = [11, 21, 43, 101]
    _multi_slopes = []
    for _w in _windows_to_test:
        if _w >= n // 2:
            continue
        _k = np.ones(_w) / _w
        _s = np.convolve(residual, _k, mode="valid")
        _t = _w // 2
        _r = residual[_t:_t + len(_s)] - _s
        if len(_r) > 50:
            _fw, _pw = welch(_r, fs=1.0, nperseg=min(1024, len(_r) // 2))
            _m = _fw > 0.005
            if np.sum(_m) > 5:
                _lf = np.log10(_fw[_m])
                _lp = np.log10(np.maximum(_pw[_m], 1e-30))
                _c = np.polyfit(_lf, _lp, 1)
                _multi_slopes.append((_w, float(_c[0])))

    # Use the specified window or default to W=21
    if detrend_window and detrend_window > 2:
        kernel = np.ones(detrend_window) / detrend_window
        smoothed_res = np.convolve(residual, kernel, mode="valid")
        trim = detrend_window // 2
        detrended = residual[trim:trim + len(smoothed_res)] - smoothed_res
        x_dt = x[trim:trim + len(smoothed_res)]
        method = f"moving_average_W{detrend_window}"
    else:
        # Linear detrend
        coeffs = np.polyfit(np.arange(n, dtype=float), residual, 1)
        detrended = residual - np.polyval(coeffs, np.arange(n, dtype=float))
        x_dt = x
        method = "linear"

    n_dt = len(detrended)
    if n_dt < 50:
        return None

    # 2. Welch periodogram → spectral slope
    freqs_w, psd = welch(detrended, fs=1.0, nperseg=min(256, n_dt // 2))
    mask = freqs_w > 0.01
    if np.sum(mask) < 5:
        return None
    log_f = np.log10(freqs_w[mask])
    log_p = np.log10(np.maximum(psd[mask], 1e-30))
    slope_coeffs = np.polyfit(log_f, log_p, 1)
    spectral_slope = slope_coeffs[0]
    # R² of the log-log fit
    predicted = np.polyval(slope_coeffs, log_f)
    ss_res = np.sum((log_p - predicted) ** 2)
    ss_tot = np.sum((log_p - np.mean(log_p)) ** 2)
    r2 = 1.0 - ss_res / max(ss_tot, 1e-30)

    if r2 < 0.3:  # no clear spectral structure
        return None

    # 3. Dominant period via Lomb-Scargle
    t = x_dt - x_dt[0]
    test_freqs = np.linspace(0.005, 0.25, 2000)
    ls_power = lombscargle(t, detrended - np.mean(detrended), test_freqs * 2 * np.pi)
    peak_idx = np.argmax(ls_power)
    peak_freq = test_freqs[peak_idx]
    peak_power = ls_power[peak_idx]
    total_power = np.sum(ls_power)
    bandwidth = float(peak_power / max(total_power, 1e-30))

    # FAP
    var_dt = float(np.var(detrended)) if np.var(detrended) > 0 else 1e-30
    z_score = peak_power / var_dt
    M = len(test_freqs)
    fap = 1.0 - (1.0 - math.exp(-z_score)) ** M if z_score < 700 else 0.0
    dominant_period = (1.0 / peak_freq) if (fap < 0.01 and peak_freq > 0) else None

    # 4. Hilbert transform → phase linearity
    analytic = hilbert(detrended)
    amplitude_env = np.abs(analytic)
    instant_phase = np.unwrap(np.angle(analytic))
    phase_slope = np.polyfit(np.arange(n_dt, dtype=float), instant_phase, 1)
    phase_residual = instant_phase - np.polyval(phase_slope, np.arange(n_dt, dtype=float))
    phase_res_std = float(np.std(phase_residual))
    is_quasiperiodic = phase_res_std < math.pi

    # 5. Amplitude envelope: A(n) ~ C * n^(-gamma)
    try:
        def env_power(n_arr, C, gamma):
            return C * n_arr ** (-gamma)
        popt_env, _ = curve_fit(env_power, x_dt, amplitude_env, p0=[1.0, 0.5], maxfev=5000)
        envelope_prefactor = float(popt_env[0])
        envelope_exponent = float(popt_env[1])
    except Exception:
        envelope_prefactor = 0.0
        envelope_exponent = 0.0

    # 6. DFA → Hurst exponent
    hurst = _dfa_hurst(detrended)

    # 7. Arithmetic energy fraction (Ramanujan test)
    arith_frac = 0.0
    if dominant_period and dominant_period > 2:
        q = int(round(dominant_period))
        if 3 <= q <= 200:
            class_means = {}
            for i in range(len(x)):
                r = int(x[i]) % q
                if r not in class_means:
                    class_means[r] = []
                class_means[r].append(float(y[i]))
            if class_means:
                means = [np.mean(v) for v in class_means.values()]
                spread = max(means) - min(means)
                overall_std = float(np.std(y))
                arith_frac = spread / max(2 * overall_std, 1e-30)

    # Hurst/slope consistency check
    beta_expected = 2 * hurst - 1  # for fGn
    consistent = abs(spectral_slope - beta_expected) < 0.3

    # Multi-window detrending sensitivity
    _mw_tuple = tuple((w, s) for w, s in _multi_slopes)
    _detrend_sensitive = False
    if len(_multi_slopes) >= 2:
        _slope_range = max(s for _, s in _multi_slopes) - min(s for _, s in _multi_slopes)
        _detrend_sensitive = _slope_range > 0.3

    return StatisticalFingerprint(
        spectral_slope=float(spectral_slope),
        spectral_slope_r2=float(r2),
        dominant_period=dominant_period,
        spectral_bandwidth=float(bandwidth),
        hurst_exponent=float(hurst),
        phase_linearity_residual=float(phase_res_std),
        is_quasiperiodic=is_quasiperiodic,
        envelope_exponent=envelope_exponent,
        envelope_prefactor=envelope_prefactor,
        arithmetic_energy_fraction=float(arith_frac),
        detrend_method=method,
        n_points=int(n),
        n_range=(float(x[0]), float(x[-1])),
        hurst_slope_consistent=consistent,
        multi_window_slopes=_mw_tuple,
        detrending_sensitive=_detrend_sensitive,
    )


def _dfa_hurst(signal: "np.ndarray") -> float:
    """Detrended Fluctuation Analysis for Hurst exponent."""
    n = len(signal)
    scales = [s for s in range(10, n // 4, max(1, n // 40)) if s >= 4]
    if len(scales) < 4:
        return 0.5

    flucts = []
    for s in scales:
        n_seg = n // s
        if n_seg < 2:
            continue
        rms_list = []
        for i in range(n_seg):
            seg = signal[i * s:(i + 1) * s]
            t = np.arange(s, dtype=float)
            coeffs = np.polyfit(t, seg, 1)
            detrended_seg = seg - np.polyval(coeffs, t)
            rms_list.append(float(np.sqrt(np.mean(detrended_seg ** 2))))
        if rms_list:
            flucts.append((s, np.mean(rms_list)))

    if len(flucts) < 4:
        return 0.5

    log_s = np.log([f[0] for f in flucts])
    log_f = np.log([f[1] for f in flucts])
    H = float(np.polyfit(log_s, log_f, 1)[0])
    return H
