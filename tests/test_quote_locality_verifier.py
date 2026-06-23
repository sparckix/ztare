"""Regression guard for the quote/locality sidecar.

These tests do NOT call an LLM. They feed hand-crafted `AuditorHit` objects
into the verifier to prove the sidecar catches the specific failure classes
it is designed to catch.

Coverage matrix:
  - verified: real claim + real mechanism in same paragraph
  - killed: fabricated claim quote (does not exist in target)
  - killed: real quotes but cross-paragraph mechanism (the probe 01 drift)
  - killed: claim_line_start pointing at a blank line
  - killed: missing mechanism when require_mechanism=True
  - verified: single-claim rule with no mechanism requirement
  - killed: line number off by more than the tolerance window
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ztare.catch_grammar.quote_locality_verifier import (  # noqa: E402
    AuditorHit,
    verify_hit,
)

# Synthetic target. Line numbers are 1-indexed.
# Paragraph 0: lines 1-3
# Paragraph 1: lines 5-7
# Paragraph 2: lines 9-11
TARGET = (
    "This is impossible because the constraint is definitional.\n"  # 1
    "The mechanism would require a non-existent degree of freedom.\n"  # 2
    "No experiment is proposed.\n"  # 3
    "\n"  # 4 blank
    "A separate paragraph about an unrelated topic.\n"  # 5
    "It does not connect to the first paragraph.\n"  # 6
    "It ends here.\n"  # 7
    "\n"  # 8 blank
    "A second claim about impossibility appears here.\n"  # 9
    "We would run experiment X with observable Y as the falsifier.\n"  # 10
    "Threshold is 0.02 normalized RMS.\n"  # 11
)


def test_verified_claim_with_mechanism_same_paragraph():
    hit = AuditorHit(
        rule="defining_yourself_into_victory",
        claim_quote="A second claim about impossibility appears here.",
        claim_line_start=9,
        mechanism_quote="We would run experiment X with observable Y as the falsifier.",
        mechanism_line_start=10,
    )
    r = verify_hit(TARGET, hit, require_mechanism=True)
    assert r.verdict == "verified", r.reasons
    assert r.paragraph_index_claim == r.paragraph_index_mechanism
    assert r.paragraph_index_claim == 2


def test_killed_fabricated_claim_quote():
    hit = AuditorHit(
        rule="defining_yourself_into_victory",
        claim_quote="This sentence does not exist in the target at all.",
        claim_line_start=1,
        mechanism_quote="The mechanism would require a non-existent degree of freedom.",
        mechanism_line_start=2,
    )
    r = verify_hit(TARGET, hit, require_mechanism=True)
    assert r.verdict == "killed"
    assert any("claim_quote not found" in x for x in r.reasons)


def test_killed_cross_paragraph_mechanism_drift():
    """Exact structural failure probe 01's grader caught: claim in one
    paragraph, mechanism claimed from a different paragraph."""
    hit = AuditorHit(
        rule="defining_yourself_into_victory",
        claim_quote="This is impossible because the constraint is definitional.",
        claim_line_start=1,
        mechanism_quote="We would run experiment X with observable Y as the falsifier.",
        mechanism_line_start=10,
    )
    r = verify_hit(TARGET, hit, require_mechanism=True)
    assert r.verdict == "killed"
    assert any("paragraph-locality violated" in x for x in r.reasons)


def test_killed_claim_line_in_blank():
    hit = AuditorHit(
        rule="defining_yourself_into_victory",
        claim_quote="",  # intentionally empty to also trip quote check
        claim_line_start=4,
        mechanism_quote=None,
        mechanism_line_start=None,
    )
    r = verify_hit(TARGET, hit, require_mechanism=True)
    assert r.verdict == "killed"
    # two reasons expected: quote not found AND claim line outside any paragraph
    assert any("outside any paragraph" in x for x in r.reasons) or any(
        "rule requires mechanism" in x for x in r.reasons
    )


def test_killed_missing_mechanism_when_required():
    hit = AuditorHit(
        rule="defining_yourself_into_victory",
        claim_quote="This is impossible because the constraint is definitional.",
        claim_line_start=1,
        mechanism_quote=None,
        mechanism_line_start=None,
    )
    r = verify_hit(TARGET, hit, require_mechanism=True)
    assert r.verdict == "killed"
    assert any("rule requires mechanism" in x for x in r.reasons)


def test_verified_single_claim_when_mechanism_not_required():
    hit = AuditorHit(
        rule="some_rule_without_mechanism",
        claim_quote="This is impossible because the constraint is definitional.",
        claim_line_start=1,
    )
    r = verify_hit(TARGET, hit, require_mechanism=False)
    assert r.verdict == "verified", r.reasons


def test_killed_line_number_out_of_tolerance():
    hit = AuditorHit(
        rule="defining_yourself_into_victory",
        claim_quote="This is impossible because the constraint is definitional.",
        claim_line_start=9,  # real line is 1, tolerance is ±2
        mechanism_quote="The mechanism would require a non-existent degree of freedom.",
        mechanism_line_start=2,
    )
    r = verify_hit(TARGET, hit, require_mechanism=True)
    assert r.verdict == "killed"
    assert any("claim_quote not found at or near" in x for x in r.reasons)


if __name__ == "__main__":
    test_verified_claim_with_mechanism_same_paragraph()
    test_killed_fabricated_claim_quote()
    test_killed_cross_paragraph_mechanism_drift()
    test_killed_claim_line_in_blank()
    test_killed_missing_mechanism_when_required()
    test_verified_single_claim_when_mechanism_not_required()
    test_killed_line_number_out_of_tolerance()
    print("all quote/locality sidecar regression checks passed")
