import json
import hashlib

import pytest

from ztare.common.constraint_isomorphism import (
    build_signed_morphism_obligation_verdict,
    ConstraintFingerprint,
    ConstraintMorphism,
    ConstraintSignature,
    SurfacedIsomorphism,
    compose_constraint_morphisms,
    compose_transports,
    validate_typed_mapping,
)
from ztare.research_director.research_isomorphism import (
    _cand_key,
    build_signed_experiment_verdict,
    conjecture_between,
    debug_query_for_seam,
    prescribe_for_seam,
    record_disposition,
)
from ztare.common.constraint_isomorphism import SurfacedConjecture
from ztare.leanmill.formal_verification_provider import generate_keypair


def _morphism(
    source_name: str,
    source_component: str,
    target_name: str,
    target_component: str,
) -> ConstraintMorphism:
    return ConstraintMorphism(
        source_signature=ConstraintSignature(source_name, {source_component: "integer"}),
        target_signature=ConstraintSignature(target_name, {target_component: "integer"}),
        component_map={
            source_component: {
                "target": target_component,
                "source_type": "integer",
                "target_type": "integer",
                "transform": "identity rank encoding",
            }
        },
        preservation_obligations=[
            {
                "source": source_component,
                "target": target_component,
                "predicate": f"{target_component} preserves {source_component} cardinality",
                "status": "pending",
            }
        ],
        information_losses=[],
        target_discriminator={
            "measurement": f"measured {target_component}",
            "intervention": f"perturb {source_component} by one",
            "reject_if": f"{target_component} does not change",
        },
    )


def test_constraint_morphism_hash_is_canonical_and_pending_is_not_verified() -> None:
    first = _morphism("A", "width", "B", "rank")
    reordered = ConstraintMorphism.from_dict(
        json.loads(json.dumps(first.to_dict(), sort_keys=True))
    )

    assert first.content_hash() == reordered.content_hash()
    assert first.validate().valid is True
    assert first.validate().verified is False

    tampered = first.to_dict()
    tampered["target_discriminator"]["reject_if"] = "a different outcome appears"
    tampered_validation = ConstraintMorphism.from_dict(tampered).validate()
    assert tampered_validation.valid is False
    assert "content_hash:mismatch" in tampered_validation.errors


def test_morphism_authority_requires_signed_content_bound_verdict(tmp_path) -> None:
    receipt = tmp_path / "transport_receipt.json"
    receipt.write_text('{"measurement":"rank preserved"}', encoding="utf-8")
    morphism = _morphism("A", "width", "B", "rank")
    morphism.preservation_obligations[0].update(
        status="verified",
        receipt_ref=str(receipt),
        receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest(),
    )
    content_bound = morphism.validate()
    assert content_bound.valid is True
    assert content_bound.verified is False
    assert any("trusted_public_key_missing" in warning for warning in content_bound.warnings)

    private_key, public_key = generate_keypair()
    morphism.preservation_obligations[0]["provider_verdict"] = (
        build_signed_morphism_obligation_verdict(
            morphism,
            obligation_kind="preservation",
            obligation_index=0,
            private_key_pem=private_key,
            verifier_ref="test-morphism-verifier",
        )
    )
    assert morphism.validate(trusted_public_key_pem=public_key).verified is True
    serialized = ConstraintMorphism.from_dict(morphism.to_dict())
    assert serialized.validate(trusted_public_key_pem=public_key).verified is True

    receipt.unlink()
    portable = serialized.validate(trusted_public_key_pem=public_key)
    assert portable.valid is True
    assert portable.verified is True
    receipt.write_text('{"measurement":"rank preserved"}', encoding="utf-8")

    _, wrong_public_key = generate_keypair()
    wrong_authority = morphism.validate(trusted_public_key_pem=wrong_public_key)
    assert wrong_authority.valid is True
    assert wrong_authority.verified is False
    assert any("signature" in warning for warning in wrong_authority.warnings)

    receipt.write_text('{"measurement":"changed"}', encoding="utf-8")
    validation = morphism.validate()
    assert validation.verified is False
    assert any("receipt_binding" in error for error in validation.errors)


def test_constraint_morphism_rejects_placeholder_and_declared_type_mismatch() -> None:
    bad = _morphism("A", "count", "B", "banana")
    bad.component_map["count"]["source_type"] = "boolean"

    validation = bad.validate()

    assert validation.valid is False
    assert any("target:uninformative" in error for error in validation.errors)


def test_legacy_typed_mapping_rejects_arbitrary_labels_and_mismatched_types() -> None:
    fp = ConstraintFingerprint(
        "projection with counted fibers",
        "",
        {"projection": "many_to_one", "fiber_count": 3},
    )
    good = SurfacedIsomorphism(
        "Fiber transport",
        "algebraic topology",
        "quotient fibers preserve cardinality",
        invariant_map={
            "projection": "quotient preimage",
            "fiber_count": "target cardinality",
        },
    )
    arbitrary = SurfacedIsomorphism(
        "Decorative",
        "unknown",
        "sounds similar",
        invariant_map={"projection": "banana", "fiber_count": "x"},
    )
    mismatched = SurfacedIsomorphism(
        "Ill typed",
        "unknown",
        "casts a count to a flag",
        invariant_map={
            "projection": "quotient preimage",
            "fiber_count": {
                "target": "acceptance flag",
                "source_type": "integer",
                "target_type": "boolean",
            },
        },
    )

    kept, rejected = validate_typed_mapping([good, arbitrary, mismatched], fp)

    assert [item.theorem for item in kept] == ["Fiber transport"]
    assert {item.theorem for item in rejected} == {"Decorative", "Ill typed"}


def test_checked_composition_joins_signatures_and_creates_fresh_obligations() -> None:
    first = _morphism("A", "width", "B", "rank")
    second = _morphism("B", "rank", "C", "dimension")

    composed = compose_constraint_morphisms(first, second)

    assert composed.component_map["width"]["target"] == "dimension"
    assert composed.component_map["width"]["via"] == "rank"
    assert composed.validate().valid is True
    assert composed.validate().verified is False
    assert composed.preservation_obligations[0]["status"] == "pending"
    assert composed.target_discriminator["upstream_morphism_hash"] == first.content_hash()


def test_checked_composition_rejects_an_incompatible_bridge_signature() -> None:
    first = _morphism("A", "width", "B", "rank")
    incompatible = _morphism("other B", "degree", "C", "dimension")

    with pytest.raises(ValueError, match="bridge signature mismatch"):
        compose_constraint_morphisms(first, incompatible)


def test_legacy_two_hop_remains_advisory_and_does_not_multiply_scores() -> None:
    fp = ConstraintFingerprint("seam", "", {"width": 3}, forbidden_domain="fluid PDE")
    first = SurfacedIsomorphism("Bridge", "spectral geometry", "rank bridge", enrichment=0.5)
    second = SurfacedIsomorphism("Target", "coding theory", "decoder", enrichment=0.4)

    out = compose_transports(fp, [first], lambda _fp, _n: [second])

    assert len(out) == 1
    assert out[0].enrichment is None
    assert out[0].transport_validation["status"] == "unverified_legacy_composition"


def test_prescribe_rejects_a_candidate_from_the_forbidden_home_field(monkeypatch) -> None:
    import ztare.common.constraint_isomorphism as ci

    monkeypatch.setattr(
        ci,
        "default_llm_query",
        lambda *_args, **_kwargs: [
            SurfacedIsomorphism("Fieldless result", "", "unknown provenance", "unknown map"),
            SurfacedIsomorphism("Home result", "fluid PDE", "home mechanism", "home map"),
            SurfacedIsomorphism("Distant result", "spectral geometry", "distant mechanism", "target map"),
        ],
    )

    result = prescribe_for_seam(
        "critical scaling obstruction",
        home_field="fluid PDE",
        model="gemini",
    )

    assert result["source_theorem"] == "Distant result"
    assert result["rejected_forbidden_count"] == 2


def test_debug_dispatch_injection_makes_no_hidden_provider_call(monkeypatch) -> None:
    import ztare.common.constraint_isomorphism as ci

    monkeypatch.setattr(
        ci,
        "_dispatch_text_with_receipt",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("live dispatch reached")),
    )
    text = '[{"theorem":"T","field":"F","mechanism":"M","mapping_hint":"H"}]'

    result = debug_query_for_seam(
        "constraint",
        dispatch=lambda *_args, **_kwargs: (text, {"transport": "test", "returncode": 0}),
    )

    assert result["parse_status"] == "parsed"
    assert result["candidate_count"] == 1


def test_survived_disposition_requires_candidate_bound_experiment_receipt(tmp_path) -> None:
    ledger = tmp_path / "candidates.jsonl"
    dictionary = tmp_path / "dictionary.jsonl"
    conjecture = SurfacedConjecture(
        mother_structure="shared counter",
        lowerings={"left": {"left_count": "shared count"}, "right": {"right_count": "shared count"}},
        novel_predictions={
            "left": ["left count changes within 3 steps"],
            "right": ["right count changes within 3 steps"],
        },
        kill_conditions={
            "left": ["refute if left count stays fixed for 3 steps"],
            "right": ["refute if right count stays fixed for 3 steps"],
        },
    )
    conjecture_between(
        {"constraint_class": "left", "left_count": 1},
        {"constraint_class": "right", "right_count": 1},
        query=lambda *_args: [conjecture],
        ledger=ledger,
    )
    row = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
    key = _cand_key(row)

    with pytest.raises(ValueError, match="experiment_receipt"):
        record_disposition(key, "survived", ledger=ledger, dictionary=dictionary)
    with pytest.raises(ValueError, match="does not bind"):
        record_disposition(
            key,
            "survived",
            ledger=ledger,
            dictionary=dictionary,
            experiment_receipt={
                "receipt_id": "r1",
                "experiment_id": "e1",
                "evidence_ref": "evidence.json",
                "candidate_hash": "0" * 64,
                "status": "verified",
            },
        )
    evidence = tmp_path / "evidence.json"
    evidence.write_text('{"outcome":"survived"}', encoding="utf-8")
    with pytest.raises(ValueError, match="evidence_sha256"):
        record_disposition(
            key,
            "survived",
            ledger=ledger,
            dictionary=dictionary,
            experiment_receipt={
                "receipt_id": "r2",
                "experiment_id": "e2",
                "evidence_ref": str(evidence),
                "evidence_sha256": "0" * 64,
                "candidate_hash": row["candidate_hash"],
                "status": "verified",
            },
        )

    valid_local_receipt = {
        "receipt_id": "r3",
        "experiment_id": "e3",
        "intervention_id": "i3",
        "evidence_ref": str(evidence),
        "evidence_sha256": hashlib.sha256(evidence.read_bytes()).hexdigest(),
        "candidate_hash": row["candidate_hash"],
        "status": "verified",
        "outcome": "survived",
    }
    with pytest.raises(ValueError, match="trusted_public_key_pem"):
        record_disposition(
            key,
            "survived",
            ledger=ledger,
            dictionary=dictionary,
            experiment_receipt=valid_local_receipt,
        )

    private_key, public_key = generate_keypair()
    with pytest.raises(ValueError, match="signed experiment_verdict"):
        record_disposition(
            key,
            "survived",
            ledger=ledger,
            dictionary=dictionary,
            experiment_receipt=valid_local_receipt,
            trusted_public_key_pem=public_key,
        )
    signed_receipt = dict(valid_local_receipt)
    signed_receipt["experiment_verdict"] = build_signed_experiment_verdict(
        row,
        signed_receipt,
        private_key_pem=private_key,
        verifier_ref="test-experiment-verifier",
    )
    rebound_receipt = dict(signed_receipt, experiment_id="different-experiment")
    with pytest.raises(ValueError, match="signed experiment verdict failed"):
        record_disposition(
            key,
            "survived",
            ledger=ledger,
            dictionary=dictionary,
            experiment_receipt=rebound_receipt,
            trusted_public_key_pem=public_key,
        )
    _, wrong_public_key = generate_keypair()
    with pytest.raises(ValueError, match="signature"):
        record_disposition(
            key,
            "survived",
            ledger=ledger,
            dictionary=dictionary,
            experiment_receipt=signed_receipt,
            trusted_public_key_pem=wrong_public_key,
        )

    assert not dictionary.exists()
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    assert all("disposition_for" not in item for item in rows)
