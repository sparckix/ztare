"""Tests: evidence_consolidation and batch_gate (consolidation or batch_gate)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# resolve_episode_paths imported below after sys.path is set

import pytest

# Ensure src is on path
_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "src"))

from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.evidence_consolidation import build_row_bitmap, residual_view, resolve_episode_paths
from ztare.worldmodel.grid_dsl import Grid


# ── fixtures ──────────────────────────────────────────────────────────────────

G1: Grid = ((1, 2), (3, 4))
G2: Grid = ((2, 2), (3, 4))
G3: Grid = ((1, 2), (3, 5))


def _write_identity_carrier(td: str) -> str:
    """Carrier: returns s unchanged (identity)."""
    p = os.path.join(td, "identity.py")
    with open(p, "w") as f:
        f.write("def step(s, a, t):\n    return s\n")
    return p


def _write_episode(td: str, name: str, transitions) -> str:
    """Write transitions as JSONL. transitions = list of (s, a, s_next, t)."""
    p = os.path.join(td, name)
    log = EpisodeLog()
    for (s, a, s_next, t) in transitions:
        log.append(s, a, s_next, t=t)
    log.write_jsonl(p)
    return p


# ── evidence_consolidation tests ──────────────────────────────────────────────

class TestBitmapCorrectness:
    def test_exact_and_wrong(self, tmp_path):
        ep = _write_episode(str(tmp_path), "ep.jsonl", [
            (G1, 0, G1, 0),   # identity predicts G1 → G1 ✓
            (G2, 1, G1, 1),   # identity predicts G2 → G2, but s_next=G1 ✗
        ])
        carrier = _write_identity_carrier(str(tmp_path))
        bm = build_row_bitmap(carrier, ep, persist_dir=str(tmp_path))

        assert bm["total_rows"] == 2
        assert bm["exact_count"] == 1
        assert bm["wrong_rows"] == [1]
        assert bm["bits"] == [True, False]

    def test_all_exact(self, tmp_path):
        ep = _write_episode(str(tmp_path), "ep.jsonl", [
            (G1, 0, G1, 0),
            (G2, 1, G2, 1),
        ])
        carrier = _write_identity_carrier(str(tmp_path))
        bm = build_row_bitmap(carrier, ep, persist_dir=str(tmp_path))
        assert bm["exact_count"] == 2
        assert bm["wrong_rows"] == []

    def test_all_wrong(self, tmp_path):
        ep = _write_episode(str(tmp_path), "ep.jsonl", [
            (G1, 0, G2, 0),  # identity returns G1, but s_next=G2
            (G2, 1, G3, 1),  # identity returns G2, but s_next=G3
        ])
        carrier = _write_identity_carrier(str(tmp_path))
        bm = build_row_bitmap(carrier, ep, persist_dir=str(tmp_path))
        assert bm["exact_count"] == 0
        assert bm["wrong_rows"] == [0, 1]


class TestResidualView:
    def test_residual_is_wrong_rows(self, tmp_path):
        ep = _write_episode(str(tmp_path), "ep.jsonl", [
            (G1, 0, G1, 0),
            (G2, 1, G1, 1),
            (G3, 2, G3, 2),
        ])
        carrier = _write_identity_carrier(str(tmp_path))
        bm = build_row_bitmap(carrier, ep, persist_dir=str(tmp_path))
        assert residual_view(bm) == [1]

    def test_residual_empty_when_all_exact(self, tmp_path):
        ep = _write_episode(str(tmp_path), "ep.jsonl", [(G1, 0, G1, 0)])
        carrier = _write_identity_carrier(str(tmp_path))
        bm = build_row_bitmap(carrier, ep, persist_dir=str(tmp_path))
        assert residual_view(bm) == []


class TestCacheAndReconsolidation:
    def test_cache_hit_returns_same(self, tmp_path):
        ep = _write_episode(str(tmp_path), "ep.jsonl", [(G1, 0, G1, 0)])
        carrier = _write_identity_carrier(str(tmp_path))
        bm1 = build_row_bitmap(carrier, ep, persist_dir=str(tmp_path))
        bm2 = build_row_bitmap(carrier, ep, persist_dir=str(tmp_path))
        assert bm1["exact_count"] == bm2["exact_count"]
        assert bm1["episode_hash"] == bm2["episode_hash"]
        assert len(bm1["evaluator_sha256"]) == 64

    def test_reconsolidation_on_evaluator_change(self, tmp_path, monkeypatch):
        """A cached verdict cannot survive a change in judge semantics."""
        from ztare.worldmodel import evidence_consolidation as consolidation

        ep = _write_episode(str(tmp_path), "ep.jsonl", [(G1, 0, G1, 0)])
        carrier = _write_identity_carrier(str(tmp_path))
        monkeypatch.setattr(
            consolidation,
            "_row_bitmap_evaluator_sha256",
            lambda: "a" * 64,
        )
        first = consolidation.build_row_bitmap(
            carrier, ep, persist_dir=str(tmp_path)
        )
        monkeypatch.setattr(
            consolidation,
            "_row_bitmap_evaluator_sha256",
            lambda: "b" * 64,
        )
        second = consolidation.build_row_bitmap(
            carrier, ep, persist_dir=str(tmp_path)
        )

        assert first["evaluator_sha256"] == "a" * 64
        assert second["evaluator_sha256"] == "b" * 64
        assert len(list(tmp_path.glob("*.json"))) == 2

    def test_load_failure_is_not_persisted(self, tmp_path, monkeypatch):
        """A transient lowering failure cannot poison later cache reads."""
        from ztare.worldmodel import evidence_consolidation as consolidation

        ep = _write_episode(str(tmp_path), "ep.jsonl", [(G1, 0, G1, 0)])
        carrier = _write_identity_carrier(str(tmp_path))
        original_loader = consolidation._load_carrier_from_source
        with monkeypatch.context() as patcher:
            patcher.setattr(
                consolidation,
                "_load_carrier_from_source",
                lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("transient")),
            )
            failed = consolidation.build_row_bitmap(
                carrier, ep, project_dir=tmp_path, persist_dir=str(tmp_path)
            )

        recovered = consolidation.build_row_bitmap(
            carrier, ep, project_dir=tmp_path, persist_dir=str(tmp_path)
        )
        assert original_loader is consolidation._load_carrier_from_source
        assert failed["load_error"] == "transient"
        assert recovered["exact_count"] == 1
        assert "load_error" not in recovered

    def test_reconsolidation_on_lowering_config_change(self, tmp_path):
        """Project lowering policy is part of bitmap judgment identity."""
        ep = _write_episode(str(tmp_path), "ep.jsonl", [(G1, 0, G1, 0)])
        carrier = _write_identity_carrier(str(tmp_path))
        rubric = tmp_path / "rubric.json"
        rubric.write_text('{"dynamics_assumption":"markovian"}')
        first = build_row_bitmap(
            carrier, ep, project_dir=tmp_path, persist_dir=str(tmp_path)
        )
        rubric.write_text('{"dynamics_assumption":"lawful_time"}')
        second = build_row_bitmap(
            carrier, ep, project_dir=tmp_path, persist_dir=str(tmp_path)
        )

        assert first["lowering_config_sha256"] != second["lowering_config_sha256"]
        assert len(list(tmp_path.glob("*.json"))) == 3  # rubric + two bitmaps

    def test_reconsolidation_on_evidence_append(self, tmp_path):
        """New evidence (appended row) produces a different episode hash and recomputes."""
        log = EpisodeLog()
        log.append(G1, 0, G1, t=0)
        ep1 = str(tmp_path / "ep1.jsonl")
        log.write_jsonl(ep1)

        log.append(G2, 1, G1, t=1)   # append new row
        ep2 = str(tmp_path / "ep2.jsonl")
        log.write_jsonl(ep2)

        carrier = _write_identity_carrier(str(tmp_path))
        bm1 = build_row_bitmap(carrier, ep1, persist_dir=str(tmp_path))
        bm2 = build_row_bitmap(carrier, ep2, persist_dir=str(tmp_path))

        assert bm1["episode_hash"] != bm2["episode_hash"], "episode hash must change on append"
        assert bm2["total_rows"] == 2, "recomputed bitmap has the new row"

    def test_reconsolidation_on_carrier_change(self, tmp_path):
        """New carrier sha produces a new bitmap file."""
        ep = _write_episode(str(tmp_path), "ep.jsonl", [(G1, 0, G2, 0)])
        c1 = _write_identity_carrier(str(tmp_path))

        # Different carrier: always returns G2
        c2_path = str(tmp_path / "const.py")
        with open(c2_path, "w") as f:
            f.write(f"_G2 = {repr(G2)}\ndef step(s, a, t):\n    return _G2\n")

        bm1 = build_row_bitmap(c1, ep, persist_dir=str(tmp_path))
        bm2 = build_row_bitmap(c2_path, ep, persist_dir=str(tmp_path))

        assert bm1["carrier_sha256"] != bm2["carrier_sha256"]
        assert bm1["exact_count"] == 0   # identity predicts G1, s_next=G2 → wrong
        assert bm2["exact_count"] == 1   # const predicts G2, s_next=G2 → exact


# ── batch_gate tests ──────────────────────────────────────────────────────────

class TestBatchGate:
    def _make_project(self, tmp_path: Path) -> Path:
        """Build a minimal fake project structure."""
        ep_dir = tmp_path / "raw" / "episodes"
        ep_dir.mkdir(parents=True)

        # episode_001 (visible): 3 transitions
        vis = EpisodeLog()
        vis.append(G1, 0, G1, t=0)
        vis.append(G2, 1, G1, t=1)
        vis.append(G3, 2, G3, t=2)
        vis.write_jsonl(ep_dir / "episode_001.jsonl")

        # episode_002 (holdout): 2 transitions
        hld = EpisodeLog()
        hld.append(G1, 0, G1, t=0)
        hld.append(G3, 2, G3, t=1)
        hld.write_jsonl(ep_dir / "episode_002.jsonl")

        return tmp_path

    def test_batch_visible_exact(self, tmp_path):
        from ztare.worldmodel.batch_gate import batch_gate
        project = self._make_project(tmp_path)

        # Identity carrier: predicts rows 0,2 exact (s_next=s), wrong on row 1
        c1 = str(tmp_path / "c1.py")
        with open(c1, "w") as f:
            f.write("def step(s, a, t):\n    return s\n")

        results = batch_gate(str(project), [c1], episodes=("visible",))
        assert len(results) == 1
        r = results[0]
        assert r["visible_exact"] == 2, f"expected 2 exact, got {r}"
        assert r["wrong_rows"] == [1]
        assert r["partial"] is False

    def test_batch_holdout_depth(self, tmp_path):
        from ztare.worldmodel.batch_gate import batch_gate
        project = self._make_project(tmp_path)

        # rollout_depth propagates the candidate's own predictions (not teacher-forced).
        # Identity carries: step 0: current=G1, predict=G1, s_next=G1 ✓ → depth=1.
        # Step 1: current=G1 (propagated), predict=G1, but s_next=G3 ✗ → stop at 1.
        c1 = str(tmp_path / "c1.py")
        with open(c1, "w") as f:
            f.write("def step(s, a, t):\n    return s\n")

        results = batch_gate(str(project), [c1], episodes=("visible", "holdout"))
        assert results[0]["holdout_depth"] == 1

    def test_batch_multiple_candidates(self, tmp_path):
        from ztare.worldmodel.batch_gate import batch_gate
        project = self._make_project(tmp_path)

        c_identity = str(tmp_path / "identity.py")
        with open(c_identity, "w") as f:
            f.write("def step(s, a, t):\n    return s\n")

        # Always-None carrier: predicts nothing
        c_none = str(tmp_path / "none_carrier.py")
        with open(c_none, "w") as f:
            f.write("def step(s, a, t):\n    return None\n")

        results = batch_gate(str(project), [c_identity, c_none], episodes=("visible",))
        assert len(results) == 2
        id_r = next(r for r in results if "identity" in r["candidate"])
        none_r = next(r for r in results if "none_carrier" in r["candidate"])
        assert id_r["visible_exact"] == 2
        assert none_r["visible_exact"] == 0

    def test_early_abort_marks_partial(self, tmp_path):
        from ztare.worldmodel.batch_gate import batch_gate
        project = self._make_project(tmp_path)

        # None carrier will accumulate 3 wrong rows (all rows wrong)
        c_none = str(tmp_path / "none_carrier.py")
        with open(c_none, "w") as f:
            f.write("def step(s, a, t):\n    return None\n")

        # Champion has 1 wrong row; abort margin=0 → abort after 2nd wrong row
        champion_bitmap = {"wrong_rows": [1], "exact_count": 2}
        results = batch_gate(
            str(project), [c_none],
            episodes=("visible",),
            champion_bitmap=champion_bitmap,
            early_abort_on_worse=0,
        )
        assert results[0]["partial"] is True
        assert "abort_reason" in results[0]
        # holdout should NOT be evaluated for partial results
        assert results[0]["holdout_depth"] == -1


# ── equivalence test against real gate_harness.py ─────────────────────────────

PROJECT_DIR = _REPO / "projects" / "arc3_ls20_gov"
HARNESS = PROJECT_DIR / "gate_harness.py"


@pytest.mark.skipif(
    not HARNESS.exists(),
    reason="arc3_ls20_gov project not found",
)
class TestEquivalenceVsHarness:
    """batch_gate results must match gate_harness.py subprocess output exactly."""

    def _harness_scores(self, candidate_path: Path) -> dict:
        result = subprocess.run(
            [sys.executable, str(HARNESS), "--candidate-path", str(candidate_path)],
            capture_output=True, text=True, timeout=180,
            cwd=str(HARNESS.parent),
        )
        return json.loads(result.stdout)

    def _extract_scores(self, harness_out: dict) -> tuple:
        """Return (visible_exact, holdout_depth) from harness output."""
        gates = harness_out.get("gates", {})
        vis = gates.get("visible_replay_exact", {})
        hld = gates.get("holdout_rollout_exact", {})
        diag = vis.get("diagnostics", {})
        exact = diag.get("exact_rows", -1)
        depth = hld.get("value", -1)
        return exact, depth

    def test_champion_equivalence(self):
        from ztare.worldmodel.batch_gate import batch_gate
        champion = PROJECT_DIR / "test_model.py"
        if not champion.exists():
            pytest.skip("test_model.py not found")

        harness_out = self._harness_scores(champion)
        h_exact, h_depth = self._extract_scores(harness_out)

        batch_out = batch_gate(str(PROJECT_DIR), [str(champion)])
        b = batch_out[0]
        b_exact = b["visible_exact"]
        b_depth = b["holdout_depth"]

        assert b_exact == h_exact, (
            f"visible_exact mismatch: batch={b_exact} harness={h_exact}\n"
            f"harness gates: {json.dumps(harness_out.get('gates'), indent=2)}\n"
            f"batch result: {json.dumps(b, indent=2)}"
        )
        assert b_depth == h_depth, (
            f"holdout_depth mismatch: batch={b_depth} harness={h_depth}"
        )

    def test_candidate_1_equivalence(self):
        from ztare.worldmodel.batch_gate import batch_gate
        # Use a real workspace candidate
        candidates = list((PROJECT_DIR / "workspace").glob("candidate_*.py"))
        if not candidates:
            pytest.skip("no workspace candidates found")
        c = candidates[0]

        harness_out = self._harness_scores(c)
        h_exact, h_depth = self._extract_scores(harness_out)
        if h_exact < 0:
            pytest.skip(f"harness returned import_error for {c.name}")

        batch_out = batch_gate(str(PROJECT_DIR), [str(c)])
        b = batch_out[0]
        assert b["visible_exact"] == h_exact, (
            f"{c.name}: visible_exact batch={b['visible_exact']} harness={h_exact}"
        )
        assert b["holdout_depth"] == h_depth, (
            f"{c.name}: holdout_depth batch={b['holdout_depth']} harness={h_depth}"
        )

    def test_candidate_2_equivalence(self):
        from ztare.worldmodel.batch_gate import batch_gate
        candidates = list((PROJECT_DIR / "workspace").glob("candidate_*.py"))
        if len(candidates) < 2:
            pytest.skip("need at least 2 workspace candidates")
        c = candidates[1]

        harness_out = self._harness_scores(c)
        h_exact, h_depth = self._extract_scores(harness_out)
        if h_exact < 0:
            pytest.skip(f"harness returned import_error for {c.name}")

        batch_out = batch_gate(str(PROJECT_DIR), [str(c)])
        b = batch_out[0]
        assert b["visible_exact"] == h_exact, (
            f"{c.name}: visible_exact batch={b['visible_exact']} harness={h_exact}"
        )
        assert b["holdout_depth"] == h_depth, (
            f"{c.name}: holdout_depth batch={b['holdout_depth']} harness={h_depth}"
        )


# ── timing test ───────────────────────────────────────────────────────────────

@pytest.mark.skipif(
    not HARNESS.exists(),
    reason="arc3_ls20_gov project not found",
)
class TestTiming:
    """Compare batch_gate timing vs subprocess path (K=5 candidates)."""

    def test_timing_comparison(self, capsys):
        from ztare.worldmodel.batch_gate import batch_gate

        candidates = list((PROJECT_DIR / "workspace").glob("candidate_*.py"))[:5]
        champion = PROJECT_DIR / "test_model.py"
        all_candidates = ([str(champion)] + [str(c) for c in candidates])[:5]

        if len(all_candidates) < 2:
            pytest.skip("need at least 2 candidates for timing comparison")

        # Batch path
        t0 = time.perf_counter()
        batch_results = batch_gate(str(PROJECT_DIR), all_candidates)
        t_batch = time.perf_counter() - t0

        # Subprocess path
        t1 = time.perf_counter()
        for cpath in all_candidates:
            subprocess.run(
                [sys.executable, str(HARNESS), "--candidate-path", cpath],
                capture_output=True, timeout=180,
                cwd=str(HARNESS.parent),
            )
        t_subprocess = time.perf_counter() - t1

        speedup = t_subprocess / max(t_batch, 0.001)
        k = len(all_candidates)

        with capsys.disabled():
            print(f"\n# Timing: K={k} candidates")
            print(f"#   batch_gate:  {t_batch:.2f}s ({t_batch/k:.2f}s/candidate)")
            print(f"#   subprocess:  {t_subprocess:.2f}s ({t_subprocess/k:.2f}s/candidate)")
            print(f"#   speedup:     {speedup:.1f}x")

        # Batch should be faster (at minimum not slower by more than 2x for K≥3)
        if k >= 3:
            assert t_batch < t_subprocess * 1.5, (
                f"batch ({t_batch:.1f}s) should be faster than subprocess ({t_subprocess:.1f}s)"
            )


# ── resolve_episode_paths tests ───────────────────────────────────────────────

class TestResolveEpisodePaths:
    """Verify the three-tier resolution: fallback → rubric → MANIFEST."""

    def _make_project(self, tmp_path: Path, ep_names: list[str] = None) -> Path:
        """Create a minimal project dir under tmp_path/projects/<name>/."""
        proj = tmp_path / "projects" / "test_proj"
        ep_dir = proj / "raw" / "episodes"
        ep_dir.mkdir(parents=True)
        if ep_names is None:
            ep_names = ["episode_001.jsonl", "episode_002.jsonl"]
        for name in ep_names:
            (ep_dir / name).write_text("{}", encoding="utf-8")
        return proj

    def test_fallback_sorted_order(self, tmp_path):
        """Fallback picks first and second sorted .jsonl files."""
        proj = self._make_project(tmp_path, ["episode_001.jsonl", "episode_002.jsonl"])
        result = resolve_episode_paths(proj)
        assert result["visible"].name == "episode_001.jsonl"
        assert result["holdout"].name == "episode_002.jsonl"

    def test_fallback_single_episode_holdout_none(self, tmp_path):
        """Single-episode project → holdout is None."""
        proj = self._make_project(tmp_path, ["episode_001.jsonl"])
        result = resolve_episode_paths(proj)
        assert result["visible"].name == "episode_001.jsonl"
        assert result["holdout"] is None

    def test_fallback_no_episodes_both_none(self, tmp_path):
        """No episode files → both None."""
        proj = tmp_path / "projects" / "empty_proj"
        (proj / "raw" / "episodes").mkdir(parents=True)
        result = resolve_episode_paths(proj)
        assert result["visible"] is None
        assert result["holdout"] is None

    def test_manifest_override_wins(self, tmp_path):
        """MANIFEST.json episode_roles overrides fallback convention."""
        proj = self._make_project(tmp_path, ["episode_001.jsonl", "episode_002.jsonl"])
        # Write a third file that MANIFEST points visible at
        ep_dir = proj / "raw" / "episodes"
        (ep_dir / "episode_custom.jsonl").write_text("{}", encoding="utf-8")
        manifest = {
            "episode_roles": {
                "visible": str(ep_dir / "episode_custom.jsonl"),
                "holdout": str(ep_dir / "episode_002.jsonl"),
            }
        }
        (proj / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
        result = resolve_episode_paths(proj)
        assert result["visible"].name == "episode_custom.jsonl"
        assert result["holdout"].name == "episode_002.jsonl"

    def test_manifest_top_level_keys(self, tmp_path):
        """MANIFEST top-level visible_episode/holdout_episode also work."""
        proj = self._make_project(tmp_path, ["episode_001.jsonl", "episode_002.jsonl"])
        ep_dir = proj / "raw" / "episodes"
        manifest = {
            "visible_episode": str(ep_dir / "episode_001.jsonl"),
            "holdout_episode": str(ep_dir / "episode_002.jsonl"),
        }
        (proj / "MANIFEST.json").write_text(json.dumps(manifest), encoding="utf-8")
        result = resolve_episode_paths(proj)
        assert result["visible"].name == "episode_001.jsonl"
        assert result["holdout"].name == "episode_002.jsonl"

    def test_corrupt_manifest_cannot_fall_back_and_swap_roles(self, tmp_path):
        proj = self._make_project(tmp_path, ["a_holdout.jsonl", "z_visible.jsonl"])
        (proj / "MANIFEST.json").write_text("{broken", encoding="utf-8")
        with pytest.raises(ValueError, match="unreadable episode-role manifest"):
            resolve_episode_paths(proj)

    def test_batch_gate_no_crash_without_holdout(self, tmp_path):
        """batch_gate with holdout=None in resolver must not crash (guard short-circuits)."""
        from ztare.worldmodel.batch_gate import batch_gate
        proj = self._make_project(tmp_path, ["episode_001.jsonl"])
        # Pass episodes=("holdout",) but resolver returns holdout=None → guard skips load
        results = batch_gate(str(proj), [], episodes=("holdout",))
        assert results == []
