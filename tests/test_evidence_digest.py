"""Hermetic tests for the bounded evidence digest (FIX A).

Invariants: budget respected, small residual sets included, large residual
sets quotiented, deterministic (same input -> same digest), and a no-op for
non-interactive projects.
"""
from types import SimpleNamespace

from ztare.worldmodel.evidence_digest import (
    default_budget,
    digest_transitions,
    maybe_digest_evidence,
)


def _grid(block_x):
    """5x5 background of 0 with a 2-cell mover (color 2) at column block_x."""
    g = [[0] * 5 for _ in range(5)]
    g[2][block_x] = 2
    g[3][block_x] = 2
    return g


def _rows(n):
    """n rightward-move transitions (one diff-signature cluster). Residual rows
    carry a distinctive action=9 flip so they can be counted unambiguously."""
    rows = []
    for i in range(n):
        col = i % 4
        s = _grid(col)
        sn = _grid(col + 1) if col + 1 <= 4 else _grid(col)
        if i in (3, 11):                       # planted residuals
            sn = [r[:] for r in s]
            sn[0][0] = 7                        # a mechanic the "champion" misses
            rows.append(SimpleNamespace(t=i, s=s, a=9, s_next=sn))
        else:
            rows.append(SimpleNamespace(t=i, s=s, a=0, s_next=sn))
    return rows


def test_small_residuals_kept_even_over_tiny_budget():
    rows = _rows(200)
    d = digest_transitions(rows, residual_indices=[3, 11], budget=200)
    assert "UNEXPLAINED / RESIDUAL" in d
    assert d.count("a=9") == 2                  # both residual rows verbatim...
    assert len(d) > 200                         # ...even though that blows the tiny budget


def test_large_residuals_are_quotiented_under_budget():
    rows = _rows(200)
    d = digest_transitions(rows, residual_indices=list(range(120)), budget=4000)
    assert "QUOTIENTED RESIDUAL TRANSITIONS" in d
    assert "diff-signature classes" in d
    assert "sample_indices=" in d
    assert len(d) <= 4000
    assert d.count("(t=") < 120


def test_budget_respected_when_residuals_fit():
    rows = _rows(400)
    budget = 4000
    d = digest_transitions(rows, residual_indices=[3, 11], budget=budget)
    assert len(d) <= budget
    assert d.count("a=9") == 2                  # residuals present
    assert "NEWEST TRANSITIONS" in d            # fill section ran
    assert d.count("(t=") < 400                 # and got truncated at the budget


def test_deterministic():
    rows = _rows(120)
    a = digest_transitions(rows, residual_indices=[3, 11], budget=6000)
    b = digest_transitions(rows, residual_indices=[3, 11], budget=6000)
    assert a == b


def test_header_reports_invariants():
    rows = _rows(40)
    d = digest_transitions(rows, residual_indices=[], budget=50000, env_frames=2)
    assert "rows=40" in d and "grid=5x5" in d and "env_frames=2" in d
    assert "per-color count invariant" in d


def test_no_residuals_is_valid():
    rows = _rows(30)
    d = digest_transitions(rows, residual_indices=None, budget=50000)
    assert "EVIDENCE DIGEST" in d
    assert "UNEXPLAINED / RESIDUAL" not in d    # nothing to explain -> no residual block


def test_default_digest_budget_stays_prompt_bounded(monkeypatch):
    monkeypatch.delenv("ZTARE_EVIDENCE_DIGEST_CHARS", raising=False)
    assert 12000 <= default_budget() <= 32000


def test_noninteractive_project_returns_raw(tmp_path):
    raw = "Evidence for a research paper.\nVisible data: prose, not transitions.\n"
    assert maybe_digest_evidence(str(tmp_path), raw) == raw   # no episode log -> unchanged


def test_disabled_returns_raw(tmp_path, monkeypatch):
    monkeypatch.setenv("ZTARE_EVIDENCE_DIGEST", "0")
    raw = "anything at all"
    assert maybe_digest_evidence(str(tmp_path), raw) == raw
