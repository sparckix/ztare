"""GP-157 Bug #38 — sparse-indicator hard reject regression tests.

Per Gemini Pro panel mandate (2026-04-25): when a parameter is bound
to a one-hot indicator that fires on fewer than N rows in visible_data,
the parameter is statistically underdetermined and scipy will absorb noise
into it. The fit primitive must reject such forms PRE-FIT with a structural
diagnostic that gives the mutator three valid escapes (merge / drop /
continuous). No domain knowledge in the diagnostic — pure statistical
protocol applicable to every fit_primitive_features substrate.

Invariants asserted:
1. AST-based detection catches the 4 canonical patterns: `==`, `in`,
   commutative reorder, and `float(...)`-wrapped indicators.
2. Dense indicators (≥ min_rows) pass cleanly.
3. The reject diagnostic NEVER mentions specific feature axes the
   substrate exposes (no oracle / hypothesis leak).
4. The diagnostic gives all three escapes (merge / drop / continuous).
5. End-to-end: a form with both a sparse and a dense indicator is
   rejected, while the same form with only the dense indicator passes.
6. Opt-out flag works (substrates that legitimately have small visible
   sets can disable).
"""
from __future__ import annotations

import math

import pytest

from ztare.fit.fit_primitive_features import (
    _SPARSE_INDICATOR_MIN_ROWS_DEFAULT,
    _extract_indicator_bindings,
    detect_sparse_indicator_overfit,
    fit_features,
)


# ── AST detection coverage ───────────────────────────────────────────────


def test_extract_eq_indicator():
    """Pattern A: params['p'] * (features['F'] == 'V')"""
    form = "params['delta_X'] * (features['modality'] == 'audio')"
    bindings = _extract_indicator_bindings(form)
    assert bindings == [("delta_X", "modality", ("audio",))]


def test_extract_in_indicator():
    """Pattern B: params['p'] * (features['F'] in ('V1', 'V2'))"""
    form = "params['delta_VIS'] * (features['modality'] in ('image', 'video'))"
    bindings = _extract_indicator_bindings(form)
    assert bindings == [("delta_VIS", "modality", ("image", "video"))]


def test_extract_commutative_reorder():
    """Pattern C: (features['F'] == 'V') * params['p'] (param on right)"""
    form = "(features['arch'] == 'cnn') * params['delta_C']"
    bindings = _extract_indicator_bindings(form)
    assert bindings == [("delta_C", "arch", ("cnn",))]


def test_extract_float_wrapped_indicator():
    """Pattern D: params['p'] * float(features['F'] == 'V')"""
    form = "params['delta_X'] * float(features['regime'] == 'A')"
    bindings = _extract_indicator_bindings(form)
    assert bindings == [("delta_X", "regime", ("A",))]


def test_extract_multiple_bindings_in_sum():
    """Real-world form: bias + multiple indicator terms."""
    form = (
        "params['bias'] "
        "+ params['m_lang'] * (features['modality'] == 'language') "
        "+ params['m_aud'] * (features['modality'] == 'audio') "
        "+ params['a_cnn'] * (features['arch'] == 'cnn_resnet')"
    )
    bindings = _extract_indicator_bindings(form)
    # Order may vary by AST walk; check as set of tuples
    assert set(bindings) == {
        ("m_lang", "modality", ("language",)),
        ("m_aud", "modality", ("audio",)),
        ("a_cnn", "arch", ("cnn_resnet",)),
    }


def test_extract_ignores_continuous_terms():
    """Continuous variables shouldn't be flagged."""
    form = "params['k'] * features['intrinsic_dim_d'] + params['b']"
    bindings = _extract_indicator_bindings(form)
    assert bindings == []


def test_extract_handles_syntax_error():
    """Malformed forms return empty list (silent — other validators catch)."""
    form = "params['x'] * features['y'] +"  # incomplete
    assert _extract_indicator_bindings(form) == []


# ── Sparse-vs-dense detection ────────────────────────────────────────────


def _row(**kw):
    return (kw, 0.5)


def test_sparse_indicator_one_row_rejected():
    form = "params['delta_X'] * (features['modality'] == 'audio')"
    visible = [
        _row(modality="language"),
        _row(modality="language"),
        _row(modality="vision"),
        _row(modality="vision"),
        _row(modality="audio"),  # only 1 audio row → sparse
    ]
    diag = detect_sparse_indicator_overfit(form, ["delta_X"], visible)
    assert diag is not None
    assert "delta_X" in diag
    assert "1 visible row" in diag


def test_dense_indicator_passes():
    form = "params['delta_X'] * (features['modality'] == 'audio')"
    visible = [_row(modality="audio") for _ in range(5)] + [_row(modality="lang")]
    diag = detect_sparse_indicator_overfit(form, ["delta_X"], visible)
    assert diag is None


def test_in_indicator_aggregates_rows():
    """`in (a, b, c)` should sum row counts for all listed values."""
    form = "params['delta_AV'] * (features['modality'] in ('audio', 'video'))"
    # 1 audio + 2 video = 3 total → exactly at threshold (passes)
    visible = (
        [_row(modality="audio")]
        + [_row(modality="video") for _ in range(2)]
        + [_row(modality="language") for _ in range(5)]
    )
    diag = detect_sparse_indicator_overfit(form, ["delta_AV"], visible)
    assert diag is None  # 3 ≥ 3


def test_in_indicator_still_sparse_when_total_below_threshold():
    form = "params['delta_AV'] * (features['modality'] in ('audio', 'video'))"
    # 1 audio + 1 video = 2 total → below threshold of 3
    visible = [
        _row(modality="audio"),
        _row(modality="video"),
        _row(modality="language"),
        _row(modality="language"),
        _row(modality="language"),
    ]
    diag = detect_sparse_indicator_overfit(form, ["delta_AV"], visible)
    assert diag is not None


def test_threshold_configurable():
    form = "params['delta_X'] * (features['m'] == 'audio')"
    visible = [_row(m="audio"), _row(m="audio"), _row(m="lang"), _row(m="lang")]
    # 2 audio rows: rejected at default min=3, accepted at min=2
    assert detect_sparse_indicator_overfit(form, ["delta_X"], visible, min_rows=3) is not None
    assert detect_sparse_indicator_overfit(form, ["delta_X"], visible, min_rows=2) is None


# ── Diagnostic content (no oracle/hypothesis leak) ───────────────────────


def test_diagnostic_provides_three_escapes():
    """The diagnostic must give all three structural escapes."""
    form = "params['delta_X'] * (features['m'] == 'rare')"
    visible = [_row(m="rare")] + [_row(m="common") for _ in range(5)]
    diag = detect_sparse_indicator_overfit(form, ["delta_X"], visible)
    assert diag is not None
    # All three escape paths must be named
    assert "MERGE" in diag
    assert "DROP" in diag
    assert "CONTINUOUS" in diag


def test_diagnostic_does_not_leak_substrate_specific_features():
    """The diagnostic must NOT name specific feature axes that would
    constitute a hypothesis injection (e.g., 'use fit_convention').
    The mutator is told THAT something is broken, not WHICH axis to try."""
    form = "params['delta_X'] * (features['modality'] == 'audio')"
    visible = [_row(modality="audio"), _row(modality="lang"), _row(modality="lang")]
    diag = detect_sparse_indicator_overfit(form, ["delta_X"], visible)
    assert diag is not None
    # Forbidden substrings — these would be substrate-specific hints
    forbidden = [
        "fit_convention",
        "Kaplan",
        "Chinchilla",
        "Bahri",
        "Sharma",
        "intrinsic_dim_d",
        "regime_hint",
        "log10_N",
    ]
    for bad in forbidden:
        assert bad not in diag, f"diagnostic leaks substrate-specific hint: {bad!r}"


# ── End-to-end fit_features integration ──────────────────────────────────


def test_fit_features_rejects_sparse_indicator_form():
    """Real fit_features call: sparse indicator → FitFailure with structural
    diagnostic, no scipy.optimize burn."""
    form = (
        "params['bias'] "
        "+ params['m_aud'] * (features['modality'] == 'audio')"
    )
    visible = (
        [({"modality": "lang", "intrinsic_dim_d": 5.0}, 0.3) for _ in range(8)]
        + [({"modality": "audio", "intrinsic_dim_d": 3.0}, 0.5)]  # 1 audio row
    )
    result = fit_features(form, ["bias", "m_aud"], visible, n_starts=1, seed=42)
    assert not result.success
    assert "Sparse-indicator overfitting" in (result.error_message or "")
    assert "m_aud" in (result.error_message or "")


def test_fit_features_passes_dense_indicator_form():
    """Same form structure but with enough rows in each category — fit runs."""
    form = (
        "params['bias'] "
        "+ params['m_aud'] * (features['modality'] == 'audio')"
    )
    # 5 audio + 5 lang rows
    visible = (
        [({"modality": "lang"}, 0.3) for _ in range(5)]
        + [({"modality": "audio"}, 0.5) for _ in range(5)]
    )
    result = fit_features(form, ["bias", "m_aud"], visible, n_starts=1, seed=42)
    assert result.success, f"dense form should fit; got: {result.error_message}"
    assert result.k_params == 2


def test_fit_features_opt_out_flag_respected():
    """Substrates with intentionally tiny visible sets can opt out."""
    form = "params['bias'] + params['m_aud'] * (features['m'] == 'audio')"
    visible = [({"m": "audio"}, 0.5), ({"m": "lang"}, 0.3), ({"m": "lang"}, 0.4)]
    # Default: rejected (1 audio row < 3)
    result_default = fit_features(form, ["bias", "m_aud"], visible, n_starts=1, seed=42)
    assert not result_default.success
    # Opt-out: fit runs
    result_opted_out = fit_features(
        form, ["bias", "m_aud"], visible,
        n_starts=1, seed=42,
        disable_sparse_indicator_reject=True,
    )
    assert result_opted_out.success


def test_fit_features_pure_continuous_form_unaffected():
    """Forms without categorical indicators are never affected by the
    sparse-indicator detector — it should be a no-op."""
    form = "params['a'] * features['x'] + params['b']"
    visible = [({"x": float(i)}, 2.0 * i + 1.0) for i in range(10)]
    result = fit_features(form, ["a", "b"], visible, n_starts=1, seed=42)
    assert result.success
    # Recovers approximately a=2, b=1
    assert math.isclose(result.fitted_params["a"], 2.0, abs_tol=0.1)
    assert math.isclose(result.fitted_params["b"], 1.0, abs_tol=0.1)


def test_default_threshold_is_three():
    """Lock the threshold default — Gemini Pro recommended 3."""
    assert _SPARSE_INDICATOR_MIN_ROWS_DEFAULT == 3
