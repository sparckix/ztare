from dataclasses import replace
import json
import subprocess
import sys

import pytest

from ztare.common.content_identity import canonical_json, content_sha256
from ztare.common.content_bound_evidence import (
    EvidenceAuthority,
    ContentBoundEvidenceError,
    make_content_bound_evidence,
    replay_content_bound_evidence,
)
from ztare.leanmill.theory_ir import content_hash


def test_common_identity_preserves_leanmill_wire_hash() -> None:
    value = {"b": [2, 3], "a": 1}
    assert canonical_json(value) == '{"a":1,"b":[2,3]}'
    assert content_sha256(value) == (
        "efbd0040190fb0871831e606c581f8a66db79d8e2bb836745a70051306956070"
    )
    assert content_hash(value) == content_sha256(value)


def test_formal_kernel_authority_cannot_be_minted_by_label() -> None:
    assert "formal_kernel" in {
        authority.value for authority in EvidenceAuthority
    }
    with pytest.raises(ContentBoundEvidenceError) as error:
        make_content_bound_evidence(
            claim_id="forged.kernel.claim",
            subject_id="forged.target",
            context_sha256="1" * 64,
            authority=EvidenceAuthority.FORMAL_KERNEL,
            scope_id="all_order",
            conclusion={"passed": True},
            evidence_sha256="2" * 64,
        )
    assert error.value.code == "formal_kernel_authority_requires_ratification"


def test_content_bound_evidence_round_trip_binds_every_identity_axis() -> None:
    receipt = make_content_bound_evidence(
        claim_id="alien.lower_bound",
        subject_id="alien.filtered_tail",
        context_sha256="1" * 64,
        authority=EvidenceAuthority.ADAPTER_EXACT,
        scope_id="all_order",
        conclusion={"bound": "2"},
        evidence_sha256="2" * 64,
    )
    assert replay_content_bound_evidence(receipt) == receipt
    assert receipt.to_dict()["conclusion"] == {"bound": "2"}


@pytest.mark.parametrize(
    ("field", "value", "error_code"),
    (
        ("claim_id", "changed", "evidence_receipt_digest_mismatch"),
        ("context_sha256", "3" * 64, "evidence_receipt_digest_mismatch"),
        ("evidence_sha256", "4" * 64, "evidence_receipt_digest_mismatch"),
        ("authority", "invented", "evidence_authority_unknown"),
    ),
)
def test_content_bound_evidence_rejects_identity_mutation(
    field: str,
    value: object,
    error_code: str,
) -> None:
    receipt = make_content_bound_evidence(
        claim_id="alien.lower_bound",
        subject_id="alien.filtered_tail",
        context_sha256="1" * 64,
        authority=EvidenceAuthority.ADAPTER_EXACT,
        scope_id="all_order",
        conclusion={"bound": "2"},
        evidence_sha256="2" * 64,
    )
    with pytest.raises(ContentBoundEvidenceError) as error:
        replay_content_bound_evidence(replace(receipt, **{field: value}))
    assert error.value.code == error_code


def test_nonformal_receipt_rejects_an_authority_binding() -> None:
    receipt = make_content_bound_evidence(
        claim_id="alien.lower_bound",
        subject_id="alien.filtered_tail",
        context_sha256="1" * 64,
        authority=EvidenceAuthority.ADAPTER_EXACT,
        scope_id="all_order",
        conclusion={"bound": "2"},
        evidence_sha256="2" * 64,
    )
    with pytest.raises(ContentBoundEvidenceError) as error:
        replay_content_bound_evidence(replace(
            receipt,
            authority_binding_json=json.dumps({"forged": True}),
        ))
    assert error.value.code == "unexpected_authority_binding"


def test_common_evidence_import_does_not_import_leanmill() -> None:
    code = """
import json, sys
import ztare.common.content_bound_evidence
print(json.dumps(sorted(
    name for name in sys.modules if name.startswith('ztare.leanmill')
)))
"""
    completed = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(completed.stdout) == []
