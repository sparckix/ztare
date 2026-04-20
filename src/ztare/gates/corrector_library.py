"""GP-074 Finite Corrector Library for contamination gate enumeration.

Contains ~25 standard corrector topologies. The contamination gate
enumerates this library to check whether a 2-bit descriptor narrows the
candidate space below the suppression threshold N.

Each entry is a callable (v, k) -> float where k is a single free
parameter. The library is intentionally small and curated — the gate
must be computable in O(library) time per iteration.

Forms outside this library trigger default suppression in the
contamination gate.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class CorrectorForm:
    name: str
    fn: Callable[[float, float], float]
    is_smooth: bool
    is_monotone: bool


def _round_kv(v: float, k: float) -> float:
    return round(k * v)


def _floor_kv(v: float, k: float) -> float:
    return math.floor(k * v)


def _ceil_kv(v: float, k: float) -> float:
    return math.ceil(k * v)


def _v_mod_k(v: float, k: float) -> float:
    if k == 0:
        return 0.0
    return v % k


def _floor_v_div_k(v: float, k: float) -> float:
    if k == 0:
        return 0.0
    return math.floor(v / k)


def _ceil_v_div_k(v: float, k: float) -> float:
    if k == 0:
        return 0.0
    return math.ceil(v / k)


def _round_v_div_k(v: float, k: float) -> float:
    if k == 0:
        return 0.0
    return round(v / k)


def _power_law(v: float, k: float) -> float:
    if v <= 0:
        return 0.0
    return round(v ** k)


def _log_growth(v: float, k: float) -> float:
    if v <= 0:
        return 0.0
    return round(k * math.log(v))


def _sqrt_growth(v: float, k: float) -> float:
    if v < 0:
        return 0.0
    return round(k * math.sqrt(v))


def _linear(v: float, k: float) -> float:
    return round(k * v)


def _quadratic(v: float, k: float) -> float:
    return round(k * v * v)


def _harmonic_step(v: float, k: float) -> float:
    if k == 0:
        return 0.0
    return math.floor(v / k) * int(k)


def _heaviside(v: float, k: float) -> float:
    return 1.0 if v >= k else 0.0


def _abs_centered(v: float, k: float) -> float:
    return round(abs(v - k))


def _triangular_wave(v: float, k: float) -> float:
    if k == 0:
        return 0.0
    return round(k * abs((v / k) - math.floor(v / k + 0.5)))


def _sigmoid_approx(v: float, k: float) -> float:
    x = k * v
    if x > 20:
        return 1.0
    if x < -20:
        return 0.0
    return round(1.0 / (1.0 + math.exp(-x)))


def _tanh_approx(v: float, k: float) -> float:
    return round(math.tanh(k * v))


def _step_at_k(v: float, k: float) -> float:
    return 1.0 if v > k else 0.0


def _ramp(v: float, k: float) -> float:
    return round(max(0.0, k * (v - k)))


def _constant(v: float, k: float) -> float:
    return round(k)


def _v_minus_floor(v: float, k: float) -> float:
    return round(v - math.floor(v / k) * k) if k != 0 else 0.0


def _cubic_root(v: float, k: float) -> float:
    return round(k * (v ** (1.0 / 3.0)))


def _inverse(v: float, k: float) -> float:
    if v == 0:
        return 0.0
    return round(k / v)


def _exp_decay(v: float, k: float) -> float:
    return round(k * math.exp(-v / max(k, 0.01)))


def _sawtooth(v: float, k: float) -> float:
    if k == 0:
        return 0.0
    return round(k * (v / k - math.floor(v / k)))


# --- Parity-scaled forms (GP-077: OEIS log-space correctors) ---

def _parity_sign(v: float) -> float:
    return 1.0 if int(v) % 2 == 0 else -1.0


def _parity_floor_kv(v: float, k: float) -> float:
    return _parity_sign(v) * math.floor(abs(k * v))


def _parity_round_kv(v: float, k: float) -> float:
    return _parity_sign(v) * round(abs(k * v))


def _parity_inverse(v: float, k: float) -> float:
    if v == 0:
        return 0.0
    return _parity_sign(v) * round(abs(k / v))


def _parity_sqrt(v: float, k: float) -> float:
    if v <= 0:
        return 0.0
    return _parity_sign(v) * round(abs(k) * math.sqrt(v))


def _parity_log(v: float, k: float) -> float:
    if v <= 0:
        return 0.0
    return _parity_sign(v) * round(abs(k) * math.log(v))


def _parity_exp_decay(v: float, k: float) -> float:
    return _parity_sign(v) * round(abs(k) * math.exp(-v / max(abs(k), 0.01)))


CORRECTOR_LIBRARY: tuple[CorrectorForm, ...] = (
    CorrectorForm("round(k*v)", _round_kv, is_smooth=False, is_monotone=True),
    CorrectorForm("floor(k*v)", _floor_kv, is_smooth=False, is_monotone=True),
    CorrectorForm("ceil(k*v)", _ceil_kv, is_smooth=False, is_monotone=True),
    CorrectorForm("v mod k", _v_mod_k, is_smooth=False, is_monotone=False),
    CorrectorForm("floor(v/k)", _floor_v_div_k, is_smooth=False, is_monotone=True),
    CorrectorForm("ceil(v/k)", _ceil_v_div_k, is_smooth=False, is_monotone=True),
    CorrectorForm("round(v/k)", _round_v_div_k, is_smooth=False, is_monotone=True),
    CorrectorForm("v^k (rounded)", _power_law, is_smooth=False, is_monotone=True),
    CorrectorForm("k*log(v) (rounded)", _log_growth, is_smooth=False, is_monotone=True),
    CorrectorForm("k*sqrt(v) (rounded)", _sqrt_growth, is_smooth=False, is_monotone=True),
    CorrectorForm("k*v (rounded, linear)", _linear, is_smooth=False, is_monotone=True),
    CorrectorForm("k*v^2 (rounded)", _quadratic, is_smooth=False, is_monotone=True),
    CorrectorForm("harmonic step floor(v/k)*k", _harmonic_step, is_smooth=False, is_monotone=True),
    CorrectorForm("heaviside(v >= k)", _heaviside, is_smooth=False, is_monotone=True),
    CorrectorForm("|v - k| (rounded)", _abs_centered, is_smooth=False, is_monotone=False),
    CorrectorForm("triangular wave", _triangular_wave, is_smooth=False, is_monotone=False),
    CorrectorForm("sigmoid(k*v) (rounded)", _sigmoid_approx, is_smooth=False, is_monotone=True),
    CorrectorForm("tanh(k*v) (rounded)", _tanh_approx, is_smooth=False, is_monotone=True),
    CorrectorForm("step at v=k", _step_at_k, is_smooth=False, is_monotone=True),
    CorrectorForm("ramp max(0, k*(v-k))", _ramp, is_smooth=False, is_monotone=True),
    CorrectorForm("constant k", _constant, is_smooth=False, is_monotone=True),
    CorrectorForm("v - floor(v/k)*k", _v_minus_floor, is_smooth=False, is_monotone=False),
    CorrectorForm("k*v^(1/3) (rounded)", _cubic_root, is_smooth=False, is_monotone=True),
    CorrectorForm("k/v (rounded)", _inverse, is_smooth=False, is_monotone=False),
    CorrectorForm("k*exp(-v/k) (rounded)", _exp_decay, is_smooth=False, is_monotone=False),
    CorrectorForm("sawtooth k*(v/k - floor(v/k))", _sawtooth, is_smooth=False, is_monotone=False),
    # Parity-scaled forms (GP-077: OEIS log-space correctors)
    CorrectorForm("(-1)^v * floor(k*v)", _parity_floor_kv, is_smooth=False, is_monotone=False),
    CorrectorForm("(-1)^v * round(k*v)", _parity_round_kv, is_smooth=False, is_monotone=False),
    CorrectorForm("(-1)^v * round(k/v)", _parity_inverse, is_smooth=False, is_monotone=False),
    CorrectorForm("(-1)^v * round(k*sqrt(v))", _parity_sqrt, is_smooth=False, is_monotone=False),
    CorrectorForm("(-1)^v * round(k*log(v))", _parity_log, is_smooth=False, is_monotone=False),
    CorrectorForm("(-1)^v * round(k*exp(-v/k))", _parity_exp_decay, is_smooth=False, is_monotone=False),
)


def filter_by_descriptor(
    *, is_smooth: bool, is_monotone: bool,
) -> tuple[CorrectorForm, ...]:
    return tuple(
        f for f in CORRECTOR_LIBRARY
        if f.is_smooth == is_smooth and f.is_monotone == is_monotone
    )
