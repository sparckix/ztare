"""Test regime-shift detection fail-open bug fix.

Tests that:
1. When fingerprint is None, shifted label is "unknown" (not "no")
2. When fingerprint matches champion, shifted label is "no"
3. When fingerprint differs from champion, shifted label is "yes"
4. When champion fingerprint is None, shifted label is "n/a"
"""
from io import StringIO
from unittest.mock import patch

from ztare.orchestrator.iter_status_print import (
    print_latest_artifact_status,
    print_champion_artifact_status,
    print_champion_reconstruction_status,
)
from ztare.orchestrator.best_state_persistence import (
    score_regime_fingerprint_from_score_contract,
)


def capture_print(func, *args, **kwargs):
    """Helper to capture print output."""
    with patch("builtins.print") as mock_print:
        func(*args, **kwargs)
        if mock_print.call_args:
            return mock_print.call_args[0][0]
    return ""


class TestPrintLatestArtifactStatus:
    """Test print_latest_artifact_status shift label logic."""

    def test_fingerprint_none_champion_exists_renders_unknown(self):
        """Missing fingerprint should render as 'unknown' shift, not 'no'."""
        payload = {}  # No score_regime_fingerprint, no score_contract
        output = capture_print(
            print_latest_artifact_status,
            payload,
            previous_champion_fingerprint="abc123",
            score_regime_fingerprint_from_score_contract=score_regime_fingerprint_from_score_contract,
        )
        assert "shifted vs champion: unknown" in output
        assert "shifted vs champion: no" not in output

    def test_matching_fingerprints_renders_no(self):
        """Matching fingerprints should render as 'no' shift."""
        fp = "abc123"
        payload = {"score_contract": {"regime_fingerprint": fp}}
        output = capture_print(
            print_latest_artifact_status,
            payload,
            previous_champion_fingerprint=fp,
            score_regime_fingerprint_from_score_contract=score_regime_fingerprint_from_score_contract,
        )
        assert "shifted vs champion: no" in output

    def test_differing_fingerprints_renders_yes(self):
        """Differing fingerprints should render as 'yes' shift."""
        payload = {"score_contract": {"regime_fingerprint": "abc123"}}
        output = capture_print(
            print_latest_artifact_status,
            payload,
            previous_champion_fingerprint="def456",
            score_regime_fingerprint_from_score_contract=score_regime_fingerprint_from_score_contract,
        )
        assert "shifted vs champion: yes" in output

    def test_no_previous_champion_renders_na(self):
        """No previous champion should render as 'n/a'."""
        payload = {"score_contract": {"regime_fingerprint": "abc123"}}
        output = capture_print(
            print_latest_artifact_status,
            payload,
            previous_champion_fingerprint=None,
            score_regime_fingerprint_from_score_contract=score_regime_fingerprint_from_score_contract,
        )
        assert "shifted vs champion: n/a" in output

    def test_fingerprint_label_unknown_when_none(self):
        """Fingerprint label should show 'unknown' when None."""
        payload = {}
        output = capture_print(
            print_latest_artifact_status,
            payload,
            previous_champion_fingerprint="abc123",
            score_regime_fingerprint_from_score_contract=score_regime_fingerprint_from_score_contract,
        )
        assert "regime fingerprint: unknown" in output


class TestPrintChampionArtifactStatus:
    """Test print_champion_artifact_status shift label logic."""

    def test_new_fingerprint_none_champion_exists_renders_unknown(self):
        """Missing new fingerprint should render as 'unknown' shift, not 'no'."""
        output = capture_print(
            print_champion_artifact_status,
            previous_champion_fingerprint="abc123",
            new_champion_fingerprint=None,
        )
        assert "shifted vs previous champion: unknown" in output
        assert "shifted vs previous champion: no" not in output

    def test_matching_fingerprints_renders_no(self):
        """Matching fingerprints should render as 'no' shift."""
        fp = "abc123"
        output = capture_print(
            print_champion_artifact_status,
            previous_champion_fingerprint=fp,
            new_champion_fingerprint=fp,
        )
        assert "shifted vs previous champion: no" in output

    def test_differing_fingerprints_renders_yes(self):
        """Differing fingerprints should render as 'yes' shift."""
        output = capture_print(
            print_champion_artifact_status,
            previous_champion_fingerprint="abc123",
            new_champion_fingerprint="def456",
        )
        assert "shifted vs previous champion: yes" in output

    def test_no_previous_champion_renders_na(self):
        """No previous champion should render as 'n/a'."""
        output = capture_print(
            print_champion_artifact_status,
            previous_champion_fingerprint=None,
            new_champion_fingerprint="abc123",
        )
        assert "shifted vs previous champion: n/a" in output


class TestPrintChampionReconstructionStatus:
    """Test print_champion_reconstruction_status shift label logic."""

    def test_new_fingerprint_none_champion_exists_renders_unknown(self):
        """Missing new fingerprint should render as 'unknown' shift, not 'no'."""
        output = capture_print(
            print_champion_reconstruction_status,
            previous_champion_fingerprint="abc123",
            new_champion_fingerprint=None,
        )
        assert "shifted vs previous champion: unknown" in output
        assert "shifted vs previous champion: no" not in output

    def test_matching_fingerprints_renders_no(self):
        """Matching fingerprints should render as 'no' shift."""
        fp = "abc123"
        output = capture_print(
            print_champion_reconstruction_status,
            previous_champion_fingerprint=fp,
            new_champion_fingerprint=fp,
        )
        assert "shifted vs previous champion: no" in output

    def test_differing_fingerprints_renders_yes(self):
        """Differing fingerprints should render as 'yes' shift."""
        output = capture_print(
            print_champion_reconstruction_status,
            previous_champion_fingerprint="abc123",
            new_champion_fingerprint="def456",
        )
        assert "shifted vs previous champion: yes" in output
