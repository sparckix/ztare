"""Regression guard for catch grammar rule 3 deterministic verifier.

Pair: known-clean target must pass, known-dirty target must fail. If either
half of the pair flips, the apparatus is no longer discriminating and the
downstream multi-agent scorer loses its non-LLM floor.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.ztare.catch_grammar.rule_3_profile_check import check_profile_contains  # noqa: E402

GP023_REQUIRED_MODULES = [
    "state_incompatibility",
    "entropy_stripping",
    "dimensional_shift",
    "interface_discipline",
]


def test_bounded_discriminator_is_known_clean():
    result = check_profile_contains("bounded_discriminator", GP023_REQUIRED_MODULES)
    assert result["verdict"] == "pass", result
    assert result["missing"] == []
    assert set(result["present"]) == set(GP023_REQUIRED_MODULES)


def test_kernel_bounded_is_known_dirty():
    # kernel_bounded intentionally omits state_incompatibility, entropy_stripping,
    # and dimensional_shift. If this test ever passes, either the profile was
    # silently expanded or the required-modules list was silently shrunk — both
    # are the exact class of change rule 3 exists to catch.
    result = check_profile_contains("kernel_bounded", GP023_REQUIRED_MODULES)
    assert result["verdict"] == "fail", result
    assert "state_incompatibility" in result["missing"]
    assert "entropy_stripping" in result["missing"]
    assert "dimensional_shift" in result["missing"]


def test_unknown_profile_is_explicit():
    result = check_profile_contains("nonexistent_profile", GP023_REQUIRED_MODULES)
    assert result["verdict"] == "unknown_profile"
    assert "known_profiles" in result


if __name__ == "__main__":
    test_bounded_discriminator_is_known_clean()
    test_kernel_bounded_is_known_dirty()
    test_unknown_profile_is_explicit()
    print("all rule 3 regression checks passed")
