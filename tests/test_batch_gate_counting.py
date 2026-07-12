"""Tests: batch_gate counting correctness for PATCH_DELTA composition candidates.

Covers:
  1. visible_total = checked rows (env-excluded rows NOT counted in total).
  2. exact <= total invariant holds for PATCH_DELTA composed carriers.
  3. Hard invariant: if counts are impossible, load_error is set to
     GATE_COUNTING_INVARIANT_VIOLATED:... (tested via monkeypatch).
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from ztare.worldmodel.episode_log import EpisodeLog

# ── shared grids ──────────────────────────────────────────────────────────────

# Grids differ so no row is an env no-op (s == s_next would create env_frames).
# t increases every step so no t-anomaly either.
GA = ((1, 2), (3, 4))
GB = ((2, 3), (4, 5))
GC = ((3, 4), (5, 6))
GD = ((4, 5), (6, 7))


def _make_patch_project(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Build a minimal project with PATCH_BASE + PATCH_DELTA carriers.

    Layout:
      raw/episodes/episode_001.jsonl  — 4 visible transitions, no env rows
      raw/episodes/episode_002.jsonl  — 2 holdout transitions
      workspace/submissions/base.py   — identity step (always returns s)
      candidate.py                    — PATCH_BASE + PATCH_DELTA that always
                                        returns GD (overrides base entirely)

    base step returns `s` (identity), so base_next == s for every row.
    delta returns GD unconditionally.

    visible episode transitions (t increases, s != s_next, no no-ops):
      row 0: s=GA, a=0, s_next=GB → base predicts GA (wrong), delta → GD (wrong)
      row 1: s=GB, a=1, s_next=GC → base predicts GB (wrong), delta → GD (wrong)
      row 2: s=GC, a=2, s_next=GD → base predicts GC (wrong), delta → GD (exact!)
      row 3: s=GD, a=3, s_next=GA → base predicts GD (wrong), delta → GD (wrong)

    So exact=1, total=4, wrong=3. No env frames.
    """
    ep_dir = tmp_path / "raw" / "episodes"
    ep_dir.mkdir(parents=True)

    vis = EpisodeLog()
    vis.append(GA, 0, GB, t=0)
    vis.append(GB, 1, GC, t=1)
    vis.append(GC, 2, GD, t=2)
    vis.append(GD, 3, GA, t=3)
    vis.write_jsonl(ep_dir / "episode_001.jsonl")

    hld = EpisodeLog()
    hld.append(GA, 0, GA, t=0)
    hld.append(GB, 1, GB, t=1)
    hld.write_jsonl(ep_dir / "episode_002.jsonl")

    sub_dir = tmp_path / "workspace" / "submissions"
    sub_dir.mkdir(parents=True)

    base_src = "def step(s, a, t):\n    return s\n"
    base_path = sub_dir / "base.py"
    base_path.write_text(base_src)
    sha = hashlib.sha256(base_src.encode()).hexdigest()

    candidate_src = (
        f'PATCH_BASE = {{"source_ref": "workspace/submissions/base.py", "sha256": "{sha}"}}\n'
        f"\n"
        f"def PATCH_DELTA(base_next, state, action, t):\n"
        f"    return {repr(GD)}\n"
    )
    candidate_path = tmp_path / "candidate.py"
    candidate_path.write_text(candidate_src)

    return tmp_path, base_path, candidate_path


class TestPatchDeltaCounting:
    def test_exact_le_total(self, tmp_path):
        """visible_exact must never exceed visible_total for a PATCH_DELTA candidate."""
        from ztare.worldmodel.batch_gate import batch_gate

        project, _, cpath = _make_patch_project(tmp_path)
        results = batch_gate(str(project), [str(cpath)], episodes=("visible",))
        r = results[0]

        assert r.get("load_error") is None, f"unexpected load_error: {r.get('load_error')}"
        assert r["carrier"] == "patch_base", f"expected patch_base carrier, got {r['carrier']}"
        assert r["visible_exact"] <= r["visible_total"], (
            f"impossible: visible_exact={r['visible_exact']} > visible_total={r['visible_total']}"
        )

    def test_correct_counts(self, tmp_path):
        """visible_exact=1, visible_total=4 (no env rows), visible_env_excluded=0."""
        from ztare.worldmodel.batch_gate import batch_gate

        project, _, cpath = _make_patch_project(tmp_path)
        results = batch_gate(str(project), [str(cpath)], episodes=("visible",))
        r = results[0]

        assert r.get("load_error") is None, f"load_error: {r.get('load_error')}"
        assert r["visible_total"] == 4, f"expected total=4, got {r['visible_total']}"
        assert r["visible_env_excluded"] == 0, f"expected 0 env rows, got {r['visible_env_excluded']}"
        assert r["visible_exact"] == 1, (
            f"expected exact=1 (only row 2 where s_next=GD matches delta output), "
            f"got {r['visible_exact']}"
        )
        assert len(r["wrong_rows"]) == 3, f"expected 3 wrong rows, got {r['wrong_rows']}"

    def test_total_excludes_env_rows(self, tmp_path):
        """visible_total = visible_env_excluded + len(wrong_rows) + visible_exact."""
        from ztare.worldmodel.batch_gate import batch_gate

        project, _, cpath = _make_patch_project(tmp_path)
        results = batch_gate(str(project), [str(cpath)], episodes=("visible",))
        r = results[0]

        assert r.get("load_error") is None
        reconstructed = r["visible_env_excluded"] + len(r["wrong_rows"]) + r["visible_exact"]
        # visible_total = checked rows = env_excl + wrong + exact
        # but visible_total does NOT include env_excl — it IS checked rows.
        # So: visible_exact + len(wrong_rows) == visible_total
        assert r["visible_exact"] + len(r["wrong_rows"]) == r["visible_total"], (
            f"exact + wrong != total: {r['visible_exact']} + {len(r['wrong_rows'])} "
            f"!= {r['visible_total']}"
        )


class TestCountingInvariant:
    """Hard invariant: batch_gate must fail loud, not return impossible counts."""

    def test_invariant_triggers_on_impossible_exact(self, tmp_path, monkeypatch):
        """Monkeypatch _eval_visible to return exact > total → load_error set."""
        from ztare.worldmodel import batch_gate as bg_module
        from ztare.worldmodel.batch_gate import batch_gate

        project, _, cpath = _make_patch_project(tmp_path)

        # Force an impossible count: exact=100 but env_excl=0, so total=4, exact>total
        original_eval = bg_module._eval_visible

        def _bad_eval(program, visible, **kwargs):
            exact, wrong, env_excl, partial, abort = original_eval(program, visible, **kwargs)
            return 100, wrong, env_excl, partial, abort  # exact inflated to 100

        monkeypatch.setattr(bg_module, "_eval_visible", _bad_eval)

        results = batch_gate(str(project), [str(cpath)], episodes=("visible",))
        r = results[0]

        assert r.get("load_error") is not None, (
            "expected load_error for impossible count, got None"
        )
        assert r["load_error"].startswith("GATE_COUNTING_INVARIANT_VIOLATED"), (
            f"load_error must start with GATE_COUNTING_INVARIANT_VIOLATED, got: {r['load_error']}"
        )
        assert "visible_exact=100" in r["load_error"]

    def test_invariant_clean_candidate_no_error(self, tmp_path):
        """A clean candidate must NOT trigger the invariant."""
        from ztare.worldmodel.batch_gate import batch_gate

        project, _, cpath = _make_patch_project(tmp_path)
        results = batch_gate(str(project), [str(cpath)], episodes=("visible", "holdout"))
        r = results[0]

        # No violation expected
        assert r.get("load_error") is None or "GATE_COUNTING_INVARIANT" not in r.get(
            "load_error", ""
        ), f"Unexpected invariant violation on clean candidate: {r.get('load_error')}"
