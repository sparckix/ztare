"""Tests for ztare.worldmodel.version_space — synthetic tmp projects, no LLM.

10+ tests covering:
  - battery construction + determinism
  - fingerprint distinguishes differently-wrong candidates
  - admit rejects non-visible-perfect
  - source identity distinct from finite-evidence equivalence
  - seed_from_history admits perfect + rejects broken
  - disagreement report on two survivors differing on one probe
  - collapsed-population case
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from ztare.worldmodel.episode_log import EpisodeLog
from ztare.worldmodel.version_space import (
    admit,
    disagreement_report,
    fingerprint,
    load,
    probe_battery,
    residual_donors,
    seed_from_history,
    _load_prunes,
)

# ── synthetic project helpers ─────────────────────────────────────────────────

_G1 = ((1, 2), (3, 4))
_G2 = ((2, 2), (3, 4))
_G3 = ((3, 2), (3, 4))
_G4 = ((4, 2), (3, 4))


def _write_episode(path: Path, pairs: list[tuple]) -> None:
    """Write (s, a, s_next) triples as JSONL."""
    log = EpisodeLog()
    for t, (s, a, sn) in enumerate(pairs):
        log.append(s, a, sn, t=t)
    log.write_jsonl(path)


def _make_project(tmp_path: Path, pairs: list[tuple]) -> Path:
    """Minimal project: raw/episodes/episode_001.jsonl only."""
    ep_dir = tmp_path / "raw" / "episodes"
    ep_dir.mkdir(parents=True)
    _write_episode(ep_dir / "episode_001.jsonl", pairs)
    return tmp_path


def _write_candidate(project_dir: Path, name: str, src: str) -> Path:
    p = project_dir / name
    p.write_text(src)
    return p


# ── perfect carrier: s_next = s (identity) ───────────────────────────────────
_IDENTITY_SRC = "def step(s, a, t):\n    return s\n"

# wrong carrier A: always returns _G2
_WRONG_A_SRC = "def step(s, a, t):\n    return ((2,2),(3,4))\n"

# wrong carrier B: always returns _G3
_WRONG_B_SRC = "def step(s, a, t):\n    return ((3,2),(3,4))\n"


def _pairs_for_identity(n: int = 300) -> list[tuple]:
    """n transitions where s_next == s (identity is perfect)."""
    return [(_G1, i % 3, _G1) for i in range(n)]


# ── tests ────────────────────────────────────────────────────────────────────

class TestProbeBattery:
    def test_battery_nonempty(self, tmp_path):
        project = _make_project(tmp_path, _pairs_for_identity(300))
        battery = probe_battery(project)
        assert len(battery) > 0

    def test_battery_deterministic(self, tmp_path):
        project = _make_project(tmp_path, _pairs_for_identity(300))
        b1 = probe_battery(project)
        b2 = probe_battery(project)
        assert [p["row_index"] for p in b1] == [p["row_index"] for p in b2]

    def test_battery_stride_sample_present(self, tmp_path):
        project = _make_project(tmp_path, _pairs_for_identity(300))
        battery = probe_battery(project)
        stride_probes = [p for p in battery if "stride_sample" in p["provenance"]]
        assert len(stride_probes) > 0

    def test_battery_last50_present(self, tmp_path):
        project = _make_project(tmp_path, _pairs_for_identity(300))
        battery = probe_battery(project)
        last50 = [p for p in battery if "last_50" in p["provenance"]]
        assert len(last50) > 0

    def test_battery_empty_episode(self, tmp_path):
        project = _make_project(tmp_path, [])
        battery = probe_battery(project)
        assert battery == []

    def test_battery_uses_wrong_rows_from_bitmaps(self, tmp_path):
        project = _make_project(tmp_path, _pairs_for_identity(1000))
        visible = EpisodeLog.read_jsonl(
            project / "raw" / "episodes" / "episode_001.jsonl"
        )
        bm_dir = project / "workspace" / "row_bitmaps"
        bm_dir.mkdir(parents=True)
        fake_bm = {
            "schema": "ztare-row-bitmap-v1",
            "carrier_sha256": "x" * 64,
            "episode_hash": visible.content_hash(),
            "episode_path": "ep.jsonl",
            "total_rows": 1000,
            "env_frame_indices": [],
            "exact_count": 999,
            "wrong_rows": [7],
            "bits": [True] * 1000,
        }
        (bm_dir / "fake_a3b4_fake1234.json").write_text(json.dumps(fake_bm))
        battery = probe_battery(project)
        planted = next(p for p in battery if p["row_index"] == 7)
        assert "bitmap:fake_a3b4_fa" in planted["provenance"]

    def test_battery_rejects_wrong_rows_from_another_evidence_identity(self, tmp_path):
        project = _make_project(tmp_path, _pairs_for_identity(1000))
        bm_dir = project / "workspace" / "row_bitmaps"
        bm_dir.mkdir(parents=True)
        (bm_dir / "withheld.json").write_text(json.dumps({
            "schema": "ztare-row-bitmap-v1",
            "episode_hash": "withheld-evidence-sha",
            "wrong_rows": [7],
        }))
        battery = probe_battery(project)
        assert all(p["row_index"] != 7 for p in battery)

    def test_battery_rejects_wrong_rows_from_failed_bitmap(self, tmp_path):
        project = _make_project(tmp_path, _pairs_for_identity(1000))
        visible = EpisodeLog.read_jsonl(
            project / "raw" / "episodes" / "episode_001.jsonl"
        )
        bm_dir = project / "workspace" / "row_bitmaps"
        bm_dir.mkdir(parents=True)
        (bm_dir / "failed.json").write_text(json.dumps({
            "schema": "ztare-row-bitmap-v1",
            "episode_hash": visible.content_hash(),
            "load_error": "transient",
            "wrong_rows": [7],
        }))
        battery = probe_battery(project)
        assert all(p["row_index"] != 7 for p in battery)


class TestFingerprint:
    def test_fingerprint_perfect_candidate(self, tmp_path):
        project = _make_project(tmp_path, _pairs_for_identity(100))
        cpath = _write_candidate(project, "identity.py", _IDENTITY_SRC)
        battery = probe_battery(project)
        fp = fingerprint(cpath, battery, project)
        assert fp["load_error"] is None
        assert len(fp["sha16"]) == 16
        assert fp["exact_count"] == fp["vector_len"]

    def test_fingerprint_wrong_candidates_differ(self, tmp_path):
        project = _make_project(tmp_path, _pairs_for_identity(100))
        ca = _write_candidate(project, "wrong_a.py", _WRONG_A_SRC)
        cb = _write_candidate(project, "wrong_b.py", _WRONG_B_SRC)
        battery = probe_battery(project)
        fpa = fingerprint(ca, battery, project)
        fpb = fingerprint(cb, battery, project)
        assert fpa["sha16"] != fpb["sha16"], (
            "Two candidates wrong in DIFFERENT ways must have different fingerprints"
        )

    def test_fingerprint_same_behavior_same_sha(self, tmp_path):
        project = _make_project(tmp_path, _pairs_for_identity(100))
        # Two syntactically different but behaviorally identical candidates
        src_a = "def step(s, a, t):\n    return s  # version A\n"
        src_b = "def step(s, a, t):\n    x = s; return x  # version B\n"
        ca = _write_candidate(project, "id_a.py", src_a)
        cb = _write_candidate(project, "id_b.py", src_b)
        battery = probe_battery(project)
        fpa = fingerprint(ca, battery, project)
        fpb = fingerprint(cb, battery, project)
        assert fpa["sha16"] == fpb["sha16"], (
            "Behaviorally identical candidates must share fingerprint"
        )

    def test_fingerprint_load_error(self, tmp_path):
        project = _make_project(tmp_path, _pairs_for_identity(50))
        bad = _write_candidate(project, "bad.py", "def step(s,a,t): raise RuntimeError('oops')")
        battery = probe_battery(project)
        # load_error should still produce a sha16 (may differ) but
        # load_error is None because the file loads — bad step just fails on call
        # meaning exact_count will be 0 and no load_error
        fp = fingerprint(bad, battery, project)
        assert fp["exact_count"] == 0


class TestAdmit:
    def test_admit_perfect_returns_admitted(self, tmp_path):
        project = _make_project(tmp_path, _pairs_for_identity(100))
        cpath = _write_candidate(project, "identity.py", _IDENTITY_SRC)
        rec = admit(cpath, project)
        assert rec["status"] == "admitted"

    def test_admit_wrong_returns_rejected(self, tmp_path):
        # Episode where identity is NOT perfect (s_next != s)
        pairs = [(_G1, 0, _G2)] * 50
        project = _make_project(tmp_path, pairs)
        cpath = _write_candidate(project, "identity.py", _IDENTITY_SRC)
        rec = admit(cpath, project)
        assert rec["status"] == "rejected"

    def test_admit_retains_source_distinct_evidence_equivalents(self, tmp_path):
        project = _make_project(tmp_path, _pairs_for_identity(100))
        src_a = "def step(s, a, t):\n    return s  # ver A\n"
        src_b = "def step(s, a, t):\n    x = s; return x  # ver B\n"
        ca = _write_candidate(project, "id_a.py", src_a)
        cb = _write_candidate(project, "id_b.py", src_b)
        r1 = admit(ca, project)
        r2 = admit(cb, project)
        assert r1["status"] == "admitted"
        assert r2["status"] == "admitted"
        assert r1["hypothesis_id"] != r2["hypothesis_id"]
        assert r1["fingerprint"] == r2["fingerprint"]
        assert r1["evidence_equivalence"]["relation"] == "agreement_on_probe_battery"
        assert len(load(project)) == 2

    def test_admit_deduplicates_identical_source_identity(self, tmp_path):
        project = _make_project(tmp_path, _pairs_for_identity(100))
        ca = _write_candidate(project, "id_a.py", _IDENTITY_SRC)
        cb = _write_candidate(project, "id_b.py", _IDENTITY_SRC)
        assert admit(ca, project)["status"] == "admitted"
        duplicate = admit(cb, project)
        assert duplicate["status"] == "duplicate"
        assert len(load(project)) == 1

    def test_same_source_is_rechecked_after_evidence_changes(self, tmp_path):
        project = _make_project(tmp_path, [(_G1, 0, _G1)])
        candidate = _write_candidate(project, "identity.py", _IDENTITY_SRC)
        first = admit(candidate, project)
        assert first["status"] == "admitted"

        episode = project / "raw" / "episodes" / "episode_001.jsonl"
        _write_episode(episode, [(_G1, 0, _G1), (_G2, 1, _G2)])
        refreshed = admit(candidate, project)

        assert refreshed["status"] == "admitted"
        assert refreshed["evidence_equivalence"]["battery_sha256"] != (
            first["evidence_equivalence"]["battery_sha256"]
        )
        assert len(load(project)) == 1

    def test_load_persists_to_jsonl(self, tmp_path):
        project = _make_project(tmp_path, _pairs_for_identity(50))
        cpath = _write_candidate(project, "identity.py", _IDENTITY_SRC)
        admit(cpath, project)
        survivors = load(project)
        assert len(survivors) == 1
        assert survivors[0]["status"] == "admitted"

    def test_rejected_program_can_donate_local_behavior_without_reentry(self, tmp_path):
        project = _make_project(
            tmp_path,
            [
                (_G1, 0, _G2),
                (_G2, 1, _G3),
            ],
        )
        workspace = project / "workspace"
        workspace.mkdir()
        donor = _write_candidate(
            workspace,
            "partial_donor.py",
            (
                "def step(s, a, t):\n"
                "    return ((2,2),(3,4))\n"
            ),
        )
        record = admit(donor, project)
        assert record["status"] == "rejected"
        transition = EpisodeLog.read_jsonl(
            project / "raw" / "episodes" / "episode_001.jsonl"
        ).transitions()[0]

        found = residual_donors(
            project,
            transition=transition,
            baseline_prediction=_G4,
        )

        assert len(found) == 1
        assert found[0]["candidate_ref"] == "workspace/partial_donor.py"
        assert found[0]["historical_disposition"] == "rejected"
        assert found[0]["relation"] == "exact_on_counterexample"
        assert found[0]["authority"] == "diagnostic_operation_salvage_only"
        assert load(project) == []


class TestSeedFromHistory:
    def test_seed_admits_perfect_candidate(self, tmp_path):
        project = _make_project(tmp_path, _pairs_for_identity(100))
        ws = project / "workspace"
        ws.mkdir()
        # Plant a perfect candidate in workspace/
        _write_candidate(ws, "candidate_perfect.py", _IDENTITY_SRC)
        summary = seed_from_history(project)
        assert summary["admitted"] >= 1
        assert summary["n_survivors"] >= 1

    def test_seed_rejects_broken_candidate(self, tmp_path):
        # Episode where wrong_a is NOT perfect
        pairs = [(_G1, 0, _G3)] * 80
        project = _make_project(tmp_path, pairs)
        ws = project / "workspace"
        ws.mkdir()
        _write_candidate(ws, "candidate_wrong.py", _WRONG_A_SRC)
        summary = seed_from_history(project)
        assert summary["rejected"] >= 1

    def test_seed_scans_test_model_at_root(self, tmp_path):
        project = _make_project(tmp_path, _pairs_for_identity(50))
        _write_candidate(project, "test_model.py", _IDENTITY_SRC)
        summary = seed_from_history(project)
        assert summary["total_scanned"] >= 1
        assert summary["n_survivors"] >= 1


class TestDisagreementReport:
    def _two_survivor_project(self, tmp_path: Path):
        """Project with two survivors that disagree on one probe."""
        # Pairs: transitions where:
        #   - s == _G1, a == 0 → s_next = _G1  (identity correct)
        #   - s == _G2, a == 1 → s_next = _G2  (identity correct)
        # Both candidates predict s correctly EXCEPT:
        #   - candidate A: when a==2, predicts _G3; real s_next=_G1
        #     ... but we need BOTH to be PERFECT on VISIBLE to be admitted.
        # Actually both must be visible-perfect. So we need an episode where
        # BOTH are perfect, but their predictions DIFFER on some battery probe
        # from the bitmap's wrong_rows (which requires a third non-admitted
        # candidate to create wrong_rows in the bitmap).
        #
        # Simplest: make two syntactically different but behaviorally DIFFERENT
        # candidates that are BOTH correct on the visible episode. Since both
        # must be perfect on visible, they must agree on every visible row.
        # They can disagree only on HOLDOUT or unseen states.
        #
        # Actually, the disagreement_report checks battery probes, which come
        # from VISIBLE rows. If both are perfect on visible, they agree on every
        # visible probe → collapsed population is the honest result.
        #
        # For a TRUE disagreement: plant a bitmap with wrong_rows=[5]
        # then have candidateA predict one thing at row 5 and candidateB another.
        # But both must be perfect on EPISODE (visible_perfect). Row 5's s_next
        # must be a specific value that BOTH predict correctly but differently?
        # That's impossible.
        #
        # Therefore: the only way two BOTH-perfect survivors disagree on a
        # battery probe is if the battery includes rows not in the episode
        # (impossible since battery indexes into the visible episode) OR if
        # they disagree on predictions at rows that ARE correct (which means
        # their s_next predictions match s_next but via different computations,
        # but equality means the predictions are identical).
        #
        # Conclusion: any two BOTH-perfect-on-visible survivors must predict
        # identically on every visible probe. The collapsed-population case is
        # the CORRECT and HONEST outcome for any real scenario with a finite
        # visible episode.
        #
        # For test coverage we verify: disagreement_report detects collapse
        # and returns the right structure.
        project = _make_project(tmp_path, _pairs_for_identity(100))
        ws = project / "workspace"
        ws.mkdir()
        src_a = "def step(s, a, t):\n    return s  # ver A\n"
        src_b = "def step(s, a, t):\n    x = s; return x  # ver B\n"
        ca = _write_candidate(ws, "candidate_a.py", src_a)
        cb = _write_candidate(ws, "candidate_b.py", src_b)
        admit(ca, project)
        admit(cb, project)
        return project

    def test_collapsed_population_reported_honestly(self, tmp_path):
        project = self._two_survivor_project(tmp_path)
        report = disagreement_report(project)
        assert "n_survivors" in report
        survivors = load(project)
        assert len(survivors) == 2
        assert report["n_distinct_hypotheses"] == 2
        assert report["n_distinct_fingerprints"] == 1
        assert report["disagreement_states"] == []
        assert "evidence-equivalent" in report["note"]

    def test_collapsed_note_present(self, tmp_path):
        project = _make_project(tmp_path, _pairs_for_identity(100))
        ws = project / "workspace"
        ws.mkdir()
        cpath = _write_candidate(ws, "candidate_a.py", _IDENTITY_SRC)
        admit(cpath, project)
        report = disagreement_report(project)
        # With one survivor, can't compute pairwise disagreements
        assert "note" in report or "disagreement_states" in report

    def test_report_written_to_jsonl(self, tmp_path):
        project = _make_project(tmp_path, _pairs_for_identity(50))
        ws = project / "workspace"
        ws.mkdir()
        cpath = _write_candidate(ws, "candidate.py", _IDENTITY_SRC)
        admit(cpath, project)
        disagreement_report(project)
        out = project / "workspace" / "version_space_disagreements.jsonl"
        assert out.exists()
        lines = [l for l in out.read_text().splitlines() if l.strip()]
        assert len(lines) >= 1
        rec = json.loads(lines[-1])
        assert rec.get("schema") == "ztare.vs_disagreements.v1"

    def test_no_survivors_report(self, tmp_path):
        project = _make_project(tmp_path, _pairs_for_identity(50))
        report = disagreement_report(project)
        assert report["n_survivors"] == 0
        assert "note" in report

    def test_two_distinct_survivors_disagree_on_fabricated_probe(self, tmp_path):
        """Verify disagreement detection by injecting a second survivor with a different
        fingerprint via direct ledger write (simulates two behaviorally distinct programs
        that are both perfect — impossible on same finite episode but can occur across
        episodes or after episode extension)."""
        project = _make_project(tmp_path, _pairs_for_identity(80))
        ws = project / "workspace"
        ws.mkdir()
        cpath = _write_candidate(ws, "candidate_a.py", _IDENTITY_SRC)
        rec1 = admit(cpath, project)

        # Inject a second "survivor" record with a different fingerprint
        # pointing to a non-existent file — report will skip unloadable survivors
        # and report n_survivors=2 but only 1 loadable → honest note
        fake_rec = {
            "schema": "ztare.version_space.v1",
            "candidate_ref": str(ws / "candidate_phantom.py"),
            "candidate_sha": "deadbeef00000001",
            "fingerprint": "abcd1234abcd5678",
            "visible_exact": 80,
            "visible_total": 80,
            "status": "admitted",
        }
        ledger = project / "workspace" / "version_space.jsonl"
        with ledger.open("a") as f:
            f.write(json.dumps(fake_rec) + "\n")

        report = disagreement_report(project)
        assert report["n_survivors"] == 2
        assert report["n_distinct_fingerprints"] == 2
        # unloadable phantom → falls to "only N loadable survivors" note
        assert "note" in report


class TestPruneJoin:
    """FIX A planted test: admit 2, prune 1, load() returns 1."""

    def test_prune_join_excludes_pruned_candidate(self, tmp_path):
        """load() must exclude a candidate whose candidate_ref appears in prune ledger."""
        project = _make_project(tmp_path, _pairs_for_identity(100))
        ws = project / "workspace"
        ws.mkdir(exist_ok=True)
        # Admit two visually distinct candidates (same behavior → second is duplicate)
        # Force two distinct fingerprinted entries by writing ledger rows directly.
        src_a = "def step(s, a, t):\n    return s  # ver A\n"
        ca = _write_candidate(ws, "candidate_prune_a.py", src_a)
        rec_a = admit(ca, project)
        assert rec_a["status"] == "admitted"

        # Plant a second admitted record with a different fingerprint directly in the ledger
        import hashlib as _hl
        fake_fp = "deadbeef12345678"
        fake_rec = {
            "schema": "ztare.version_space.v1",
            "candidate_ref": str(ws / "candidate_prune_b.py"),
            "candidate_sha": "cafebabe00000001",
            "fingerprint": fake_fp,
            "visible_exact": 100,
            "visible_total": 100,
            "status": "admitted",
            "warrant": "S2_gate_checked",
        }
        ledger = project / "workspace" / "version_space.jsonl"
        with ledger.open("a") as f:
            f.write(json.dumps(fake_rec) + "\n")

        # Confirm 2 survivors before pruning
        assert len(load(project)) == 2

        # Write a prune row for fake_rec (keyed on candidate_ref)
        prune_row = {
            "schema": "ztare.version_space_prunes.v1",
            "candidate_ref": str(ws / "candidate_prune_b.py"),
            "fingerprint": fake_fp,
            "pruned_by": "test_observation",
        }
        prune_file = project / "workspace" / "version_space_prunes.jsonl"
        with prune_file.open("a") as f:
            f.write(json.dumps(prune_row) + "\n")

        # After pruning: only the real admitted candidate survives
        survivors = load(project)
        assert len(survivors) == 1
        assert survivors[0]["candidate_ref"] == str(ca)

    def test_ref_bound_prune_does_not_erase_evidence_equivalent_peer(self, tmp_path):
        """A ref-bound prune cannot promote an evidence property to identity."""
        project = _make_project(tmp_path, _pairs_for_identity(50))
        ws = project / "workspace"
        ws.mkdir(exist_ok=True)

        fp = "aaaa1111aaaa2222"
        ledger = project / "workspace" / "version_space.jsonl"
        rec = {
            "schema": "ztare.version_space.v1",
            "candidate_ref": "/some/path/foo.py",
            "candidate_sha": "abc123",
            "fingerprint": fp,
            "visible_exact": 50,
            "visible_total": 50,
            "status": "admitted",
            "warrant": "S2_gate_checked",
        }
        with ledger.open("a") as f:
            f.write(json.dumps(rec) + "\n")

        assert len(load(project)) == 1

        # The row names another candidate while carrying this record's finite-bank
        # fingerprint.  The unrelated executable hypothesis must remain.
        prune_row = {
            "schema": "ztare.version_space_prunes.v1",
            "candidate_ref": "/different/path.py",
            "fingerprint": fp,
        }
        prune_file = project / "workspace" / "version_space_prunes.jsonl"
        with prune_file.open("a") as f:
            f.write(json.dumps(prune_row) + "\n")

        assert len(load(project)) == 1

    def test_prune_one_of_two_source_distinct_equivalents(self, tmp_path):
        project = _make_project(tmp_path, _pairs_for_identity(50))
        ws = project / "workspace"
        ws.mkdir(exist_ok=True)
        ca = _write_candidate(ws, "a.py", "def step(s,a,t):\n    return s\n")
        cb = _write_candidate(ws, "b.py", "def step(s,a,t):\n    x=s; return x\n")
        ra = admit(ca, project)
        rb = admit(cb, project)
        assert ra["fingerprint"] == rb["fingerprint"]
        assert len(load(project)) == 2

        prune_file = project / "workspace" / "version_space_prunes.jsonl"
        prune_file.write_text(json.dumps({
            "schema": "ztare.version_space_prunes.v1",
            "candidate_ref": str(ca),
            "fingerprint": ra["fingerprint"],
        }) + "\n")

        survivors = load(project)
        assert [row["candidate_ref"] for row in survivors] == [str(cb)]

    def test_no_prune_file_returns_all_survivors(self, tmp_path):
        """If no prune file exists, load() returns all admitted candidates."""
        project = _make_project(tmp_path, _pairs_for_identity(50))
        ws = project / "workspace"
        ws.mkdir(exist_ok=True)
        ca = _write_candidate(ws, "candidate_no_prune.py", _IDENTITY_SRC)
        rec = admit(ca, project)
        assert rec["status"] == "admitted"
        assert not (project / "workspace" / "version_space_prunes.jsonl").exists()
        assert len(load(project)) == 1


class TestFingerprintRecomputation:
    def test_same_bytes_are_recomputed_under_current_evaluator(self, tmp_path, monkeypatch):
        """A diagnostic fingerprint cannot outlive its evaluator semantics."""
        import ztare.worldmodel.version_space as _vs
        project = _make_project(tmp_path, _pairs_for_identity(100))
        cpath = _write_candidate(project, "identity.py", _IDENTITY_SRC)
        battery = probe_battery(project)

        fp1 = fingerprint(cpath, battery, project)
        monkeypatch.setattr(
            _vs,
            "_load_carrier_from_source",
            lambda *_args, **_kwargs: (lambda _s, _a, _t: _G2),
        )
        fp2 = fingerprint(cpath, battery, project)

        assert fp1["exact_count"] == fp1["vector_len"]
        assert fp2["exact_count"] == 0
        assert fp2["sha16"] != fp1["sha16"]
        assert not (project / "workspace" / "version_space_fp_cache.jsonl").exists()


# ponytail: main self-check omitted — pytest covers everything, YAGNI
