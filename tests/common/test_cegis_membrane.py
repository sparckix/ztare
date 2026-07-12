from __future__ import annotations

from ztare.common.cegis_membrane import (
    CANDIDATE_AUTHOR,
    EVALUATION,
    assess_cegis_membrane,
)


def test_evaluation_with_exposed_holdout_forbids_clean_transfer() -> None:
    out = assess_cegis_membrane(
        role="EVALUATION",
        withheld_refs=("holdout",),
        exposed_refs=("holdout",),
        candidate_gate_passed=True,
    )
    assert out.run_role == EVALUATION
    assert "clean_transfer" in out.forbidden_claims
    assert out.fresh_holdout_required is True
    assert out.claim_class != "clean_transfer"


def test_evaluation_clean_membrane_still_supports_clean_transfer() -> None:
    out = assess_cegis_membrane(
        role="EVALUATION",
        withheld_refs=("holdout",),
        candidate_gate_passed=True,
    )
    assert out.claim_class == "clean_transfer"
    assert "clean_transfer" not in out.forbidden_claims
    assert out.fresh_holdout_required is False


def test_candidate_author_role_is_preserved_and_membrane_consumed() -> None:
    out = assess_cegis_membrane(
        role="candidate_author",
        withheld_refs=("holdout",),
        exposed_refs=("holdout",),
    )
    assert out.run_role == CANDIDATE_AUTHOR
    assert out.membrane_status == "candidate_author_membrane_consumed"
    assert "clean_transfer" in out.forbidden_claims
    assert out.fresh_holdout_required is True
    assert out.to_dict()["role"] == "candidate_author"


def test_candidate_author_clean_membrane_allows_candidate_attempt() -> None:
    out = assess_cegis_membrane(role="candidate_author")
    assert out.run_role == CANDIDATE_AUTHOR
    assert out.membrane_status == "candidate_author_membrane_clean"
    assert out.claim_class == "candidate_attempt"
