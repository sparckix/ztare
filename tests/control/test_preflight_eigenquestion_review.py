# SPDX-License-Identifier: MIT
"""Tests for launch-visible eigenquestion review preflight."""
from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


_REPO = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO / "scripts" / "public" / "control" / "preflight_eigenquestion_review.py"
_SPEC = importlib.util.spec_from_file_location("preflight_eigenquestion_review", _SCRIPT)
assert _SPEC and _SPEC.loader
preflight = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = preflight
_SPEC.loader.exec_module(preflight)


class EigenquestionReviewPreflightTests(unittest.TestCase):
    def _project_with_times(self, proposal_newer: bool) -> tuple[Path, str]:
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, ignore_errors=True)
        project = "fixture_project"
        project_dir = root / "projects" / project
        project_dir.mkdir(parents=True)
        charter = project_dir / "project_charter.md"
        proposal = project_dir / "proposed_eigenquestion_20260612_010203.md"
        charter.write_text("charter\n", encoding="utf-8")
        proposal.write_text("proposal\n", encoding="utf-8")
        if proposal_newer:
            os.utime(charter, (1000, 1000))
            os.utime(proposal, (2000, 2000))
        else:
            os.utime(proposal, (1000, 1000))
            os.utime(charter, (2000, 2000))
        return root, project

    def test_pending_proposal_warns_by_default_and_fails_in_strict_mode(self) -> None:
        root, project = self._project_with_times(proposal_newer=True)

        warn = preflight.inspect_eigenquestion_review(project, repo=root, strict=False)
        strict = preflight.inspect_eigenquestion_review(project, repo=root, strict=True)
        text = preflight.render_text(warn)

        self.assertEqual(warn.status, "pending_review")
        self.assertEqual(warn.pending_count, 1)
        self.assertTrue(warn.ok)
        self.assertFalse(strict.ok)
        self.assertIn("ztare eigenquestion validate --project fixture_project", text)
        self.assertIn("never auto-rewrite project_charter.md", text)
        self.assertEqual(
            preflight.inspect_eigenquestion_review(project, repo=root, strict=False)
            .charter_exists,
            True,
        )

    def test_older_proposal_is_ok(self) -> None:
        root, project = self._project_with_times(proposal_newer=False)

        result = preflight.inspect_eigenquestion_review(project, repo=root, strict=True)
        text = preflight.render_text(result)

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.pending_count, 0)
        self.assertTrue(result.ok)
        self.assertIn("no advisory eigenquestion proposal is newer", text)

    def test_missing_project_returns_error_status(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            result = preflight.inspect_eigenquestion_review(
                "missing_project",
                repo=Path(td),
            )

        self.assertEqual(result.status, "missing_project")
        self.assertFalse(result.charter_exists)
        self.assertEqual(preflight.main(["definitely_missing_project_slug"]), 2)


if __name__ == "__main__":
    unittest.main()
