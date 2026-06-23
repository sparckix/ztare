"""Fixture regression for GP-029 first-slice latent-distance observability.

Covers the pure signature extractor, the Jaccard+text distance math,
the five-label motion classifier, and the JSONL persistence contract.
All tests use real files in a tempdir — no mocking — so the on-disk
contract between the autoresearch loop and this module is exercised
end-to-end.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

from ztare.motion.latent_distance import (
    LATENT_DISTANCE_FILENAME,
    IterSignature,
    classify_motion,
    compute_distances,
    extract_iter_signature_from_paths,
    record_latent_distance,
)


def _write_eval_json(path: Path, *, score: int, families, gap_types, dag_nodes, targets, gaps) -> None:
    payload = {
        "score": score,
        "probability_dag": {"nodes": [{"id": nid, "label": lab} for nid, lab in dag_nodes]},
        "score_contract": {
            "derived_constraint_failure_families": list(families),
            "evidence_gap_types": list(gap_types),
            "derived_constraint_targets": list(targets),
            "evidence_gap_targets": list(gaps),
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_thesis(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# Signature extraction
# ---------------------------------------------------------------------------


def test_extract_signature_happy_path() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        _write_eval_json(
            d / "latest_eval_results.json",
            score=42,
            families=["floor_scaling", "magnitude_scaling"],
            gap_types=["other"],
            dag_nodes=[("N1", "Model Form Captures Qualitative Behavior"), ("N2", "Peak Fit")],
            targets=["phi exponents", "psi exponent in numerator"],
            gaps=["I_model parameters"],
        )
        _write_thesis(d / "current_iteration.md", "thesis body")
        sig = extract_iter_signature_from_paths(
            latest_eval_results_path=d / "latest_eval_results.json",
            thesis_path=d / "current_iteration.md",
        )
    assert sig is not None
    assert "floor_scaling" in sig.failure_families
    assert "other" in sig.failure_families  # gap_types folded into failure_families set
    assert any("Model Form" in x for x in sig.attack_surface)
    assert "phi exponents" in sig.named_primitives
    assert "I_model parameters" in sig.named_primitives
    assert sig.thesis_fingerprint.startswith("sha256:")


def test_extract_signature_returns_none_when_files_missing() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        sig = extract_iter_signature_from_paths(
            latest_eval_results_path=d / "missing.json",
            thesis_path=d / "missing.md",
        )
    assert sig is None


def test_extract_signature_returns_none_when_eval_json_malformed() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        (d / "latest_eval_results.json").write_text("not json", encoding="utf-8")
        (d / "current_iteration.md").write_text("thesis", encoding="utf-8")
        sig = extract_iter_signature_from_paths(
            latest_eval_results_path=d / "latest_eval_results.json",
            thesis_path=d / "current_iteration.md",
        )
    assert sig is None


# ---------------------------------------------------------------------------
# Distance math
# ---------------------------------------------------------------------------


def _sig(*, fam=(), atk=(), prim=(), text="") -> IterSignature:
    return IterSignature(
        failure_families=tuple(fam),
        attack_surface=tuple(atk),
        named_primitives=tuple(prim),
        thesis_text=text,
        thesis_fingerprint="sha256:" + ("x" * 16),
    )


def test_compute_distances_disjoint_sets_are_one() -> None:
    prev = _sig(fam=["a"], atk=["x"], prim=["p"], text="alpha")
    curr = _sig(fam=["b"], atk=["y"], prim=["q"], text="alpha")
    d = compute_distances(prev, curr)
    assert d["jaccard_failure_families"] == 1.0
    assert d["jaccard_attack_surface"] == 1.0
    assert d["jaccard_named_primitives"] == 1.0
    assert d["thesis_text_distance"] == 0.0


def test_compute_distances_identical_is_zero() -> None:
    prev = _sig(fam=["a"], atk=["x"], prim=["p"], text="alpha")
    curr = _sig(fam=["a"], atk=["x"], prim=["p"], text="alpha")
    d = compute_distances(prev, curr)
    assert d["jaccard_failure_families"] == 0.0
    assert d["thesis_text_distance"] == 0.0


# ---------------------------------------------------------------------------
# Motion classifier — five labels
# ---------------------------------------------------------------------------


def test_classify_motion_freeze() -> None:
    assert (
        classify_motion(
            {
                "jaccard_failure_families": 0.0,
                "jaccard_attack_surface": 0.0,
                "jaccard_named_primitives": 0.0,
                "thesis_text_distance": 0.0,
            },
            score_delta=0,
        )
        == "freeze"
    )


def test_classify_motion_structural() -> None:
    assert (
        classify_motion(
            {
                "jaccard_failure_families": 0.1,
                "jaccard_attack_surface": 0.9,
                "jaccard_named_primitives": 0.2,
                "thesis_text_distance": 0.4,
            },
            score_delta=0,
        )
        == "structural_move"
    )


def test_classify_motion_orbiting() -> None:
    assert (
        classify_motion(
            {
                "jaccard_failure_families": 0.05,
                "jaccard_attack_surface": 0.05,
                "jaccard_named_primitives": 0.05,
                "thesis_text_distance": 0.25,
            },
            score_delta=0,
        )
        == "orbiting"
    )


def test_classify_motion_score_only_change() -> None:
    assert (
        classify_motion(
            {
                "jaccard_failure_families": 0.05,
                "jaccard_attack_surface": 0.05,
                "jaccard_named_primitives": 0.05,
                "thesis_text_distance": 0.05,
            },
            score_delta=10,
        )
        == "score_only_change"
    )


def test_classify_motion_semantic_move_without_score_change() -> None:
    assert (
        classify_motion(
            {
                "jaccard_failure_families": 0.2,
                "jaccard_attack_surface": 0.25,
                "jaccard_named_primitives": 0.3,
                "thesis_text_distance": 0.5,
            },
            score_delta=0,
        )
        == "semantic_move_without_score_change"
    )


# ---------------------------------------------------------------------------
# record_latent_distance — JSONL persistence contract
# ---------------------------------------------------------------------------


def _make_project(tmp: Path) -> Path:
    project = tmp / "proj"
    (project / "workspace").mkdir(parents=True)
    return project


def test_record_first_iter_writes_no_prior_status() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project = _make_project(Path(tmp))
        _write_eval_json(
            project / "latest_eval_results.json",
            score=10,
            families=["a"],
            gap_types=[],
            dag_nodes=[("N1", "x")],
            targets=["t1"],
            gaps=["g1"],
        )
        _write_thesis(project / "current_iteration.md", "iter 1")

        rec = record_latent_distance(project_dir=project, iteration_index=1, score=10)

        artifact = project / "workspace" / LATENT_DISTANCE_FILENAME
        assert artifact.exists()
        lines = artifact.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        payload = json.loads(lines[0])
        assert payload["status"] == "no_prior_iter"
        assert payload["iteration_index"] == 1
        assert payload["score"] == 10
        assert payload["score_delta"] is None
        assert rec.status == "no_prior_iter"


def test_record_second_iter_computes_distance_and_classifies() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project = _make_project(Path(tmp))
        _write_eval_json(
            project / "latest_eval_results.json",
            score=10,
            families=["floor_scaling"],
            gap_types=[],
            dag_nodes=[("N1", "base")],
            targets=["t1"],
            gaps=["g1"],
        )
        _write_thesis(project / "current_iteration.md", "iter 1 body")
        record_latent_distance(project_dir=project, iteration_index=1, score=10)

        # Second iter with totally different sets — should classify structural_move.
        _write_eval_json(
            project / "latest_eval_results.json",
            score=12,
            families=["magnitude_scaling"],
            gap_types=[],
            dag_nodes=[("N9", "totally different node")],
            targets=["t99"],
            gaps=["g99"],
        )
        _write_thesis(project / "current_iteration.md", "iter 2 very different body text")
        rec = record_latent_distance(project_dir=project, iteration_index=2, score=12)

        artifact = project / "workspace" / LATENT_DISTANCE_FILENAME
        lines = artifact.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        second = json.loads(lines[1])
        assert second["status"] == "ok"
        assert second["iteration_index"] == 2
        assert second["score"] == 12
        assert second["score_delta"] == 2
        assert second["motion_class"] == "structural_move"
        assert second["distances"]["jaccard_failure_families"] == 1.0
        assert second["distances"]["jaccard_attack_surface"] == 1.0
        assert rec.status == "ok"


def test_record_source_files_missing_is_fail_silent() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project = _make_project(Path(tmp))
        rec = record_latent_distance(project_dir=project, iteration_index=1, score=10)
        assert rec.status == "source_files_missing"
        artifact = project / "workspace" / LATENT_DISTANCE_FILENAME
        payload = json.loads(artifact.read_text(encoding="utf-8").splitlines()[0])
        assert payload["status"] == "source_files_missing"


def test_record_freeze_on_repeated_iter() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        project = _make_project(Path(tmp))
        _write_eval_json(
            project / "latest_eval_results.json",
            score=7,
            families=["a"],
            gap_types=[],
            dag_nodes=[("N1", "x")],
            targets=["t1"],
            gaps=["g1"],
        )
        _write_thesis(project / "current_iteration.md", "same text")
        record_latent_distance(project_dir=project, iteration_index=1, score=7)
        rec = record_latent_distance(project_dir=project, iteration_index=2, score=7)
        # fingerprint matches -> text_distance forced to 0, sets identical -> freeze
        assert rec.motion_class == "freeze"
        assert rec.score_delta == 0


_TESTS = (
    test_extract_signature_happy_path,
    test_extract_signature_returns_none_when_files_missing,
    test_extract_signature_returns_none_when_eval_json_malformed,
    test_compute_distances_disjoint_sets_are_one,
    test_compute_distances_identical_is_zero,
    test_classify_motion_freeze,
    test_classify_motion_structural,
    test_classify_motion_orbiting,
    test_classify_motion_score_only_change,
    test_classify_motion_semantic_move_without_score_change,
    test_record_first_iter_writes_no_prior_status,
    test_record_second_iter_computes_distance_and_classifies,
    test_record_source_files_missing_is_fail_silent,
    test_record_freeze_on_repeated_iter,
)


def main() -> int:
    failed = 0
    for test in _TESTS:
        try:
            test()
        except AssertionError as exc:
            failed += 1
            print(f"FAIL {test.__name__}: {exc}")
        except Exception as exc:  # pragma: no cover - surfaced to operator
            failed += 1
            print(f"ERROR {test.__name__}: {type(exc).__name__}: {exc}")
        else:
            print(f"PASS {test.__name__}")
    print(f"\n{len(_TESTS) - failed}/{len(_TESTS)} passed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
