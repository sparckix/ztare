from __future__ import annotations

import hashlib

from ztare.common.candidate_memory import admissible_candidate_memory_records


def test_candidate_memory_accepts_legacy_patch_base_prefix_chain(tmp_path) -> None:
    submissions = tmp_path / "workspace" / "submissions"
    submissions.mkdir(parents=True)
    base = submissions / "base.py"
    base.write_text("def step(grid, action, t):\n    return grid\n", encoding="utf-8")
    digest = hashlib.sha256(base.read_bytes()).hexdigest()
    candidate = submissions / "candidate.py"
    candidate.write_text(
        'PATCH_BASE = {"source_ref":"workspace/submissions/base.py",'
        f'"sha256":"{digest[:12]}"}}\n'
        "def PATCH_DELTA(base_next, state, action):\n"
        "    return base_next\n",
        encoding="utf-8",
    )

    rows = admissible_candidate_memory_records(
        tmp_path,
        [
            {
                "source_type": "deterministic_near_miss",
                "submission": "workspace/submissions/candidate.py",
            }
        ],
    )

    assert len(rows) == 1


def test_candidate_memory_allows_patch_base_full_digest_chain(tmp_path) -> None:
    submissions = tmp_path / "workspace" / "submissions"
    submissions.mkdir(parents=True)
    base = submissions / "base.py"
    base.write_text("def step(grid, action, t):\n    return grid\n", encoding="utf-8")
    digest = hashlib.sha256(base.read_bytes()).hexdigest()
    candidate = submissions / "candidate.py"
    candidate.write_text(
        'PATCH_BASE = {"source_ref":"workspace/submissions/base.py",'
        f'"sha256":"{digest}"}}\n'
        "def PATCH_DELTA(base_next, state, action):\n"
        "    return base_next\n",
        encoding="utf-8",
    )

    rows = admissible_candidate_memory_records(
        tmp_path,
        [
            {
                "source_type": "deterministic_near_miss",
                "submission": "workspace/submissions/candidate.py",
            }
        ],
    )

    assert len(rows) == 1
