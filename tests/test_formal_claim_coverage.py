from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ztare.common.content_bound_evidence import (
    RATIFIED_KERNEL_BINDING_SCHEMA,
    EvidenceAuthority,
    _make_ratified_kernel_evidence,
    make_content_bound_evidence,
)
from ztare.common.content_identity import content_sha256
from ztare.leanmill import formal_claim_coverage as coverage
from ztare.leanmill.formal_claim_coverage import (
    FormalClaimCoverageError,
    FormalClaimCoverageProblem,
    FormalClaimNode,
    FormalPropositionIdentityKind,
    GovernedFormalSupport,
    compile_formal_claim_coverage,
    governed_formal_proposition_identity_from_receipt,
    make_formal_claim_decomposition,
    replay_formal_claim_coverage_certificate,
)


LEAN = FormalPropositionIdentityKind.GOVERNED_LEAN_PROPOSITION
SEMANTIC = FormalPropositionIdentityKind.ADAPTER_SEMANTIC


def _digest(label: str) -> str:
    return content_sha256({"formal_claim_test": label})


def _formal_receipt(
    signature: str,
    target: str,
    *,
    evidence_tag: str = "primary",
    source_tag: str = "primary",
):
    core = {
        "schema": RATIFIED_KERNEL_BINDING_SCHEMA,
        "governed_record_sha256": _digest(
            f"record:{target}:{evidence_tag}"
        ),
        "target_id": target,
        "target_signature_sha256": signature,
        "source_sha256": _digest(f"source:{target}:{source_tag}"),
        "proof_sha256": _digest(f"proof:{target}:{evidence_tag}"),
        "goal_sha256": _digest(f"goal:{target}"),
        "toolchain_identity_sha256": _digest("toolchain"),
        "kernel_parity_record_sha256": _digest(
            f"parity:{target}:{evidence_tag}"
        ),
        "solver_validation_sha256": _digest(
            f"solver:{target}:{evidence_tag}"
        ),
        "governance_sha256": _digest(
            f"governance:{target}:{evidence_tag}"
        ),
        "axiom_allowlist_receipt_sha256": _digest(
            f"axioms:{target}:{evidence_tag}"
        ),
    }
    return _make_ratified_kernel_evidence(
        {**core, "binding_sha256": content_sha256(core)}
    )


def _support(
    signature: str,
    target: str,
    *,
    evidence_tag: str = "primary",
    source_tag: str = "primary",
) -> GovernedFormalSupport:
    return GovernedFormalSupport(
        receipt=_formal_receipt(
            signature,
            target,
            evidence_tag=evidence_tag,
            source_tag=source_tag,
        ),
        certificate_ledger="unused-certificates.jsonl",
        governed_record_sha256=_digest(
            f"record:{target}:{evidence_tag}"
        ),
        parity_ledger="unused-parity.jsonl",
        target=target,
        expected_signature=": True",
        posed_source="theorem test : True := by sorry",
        proof_text="by trivial",
        goal=": True",
        lean_root=Path("."),
    )


def _target(prefix: str, role: str) -> str:
    return f"{prefix}.{role}"


def _lean_identity(signature: str, target: str):
    return governed_formal_proposition_identity_from_receipt(
        _formal_receipt(signature, target)
    )


def _lean_node(
    *,
    node_id: str,
    signature: str,
    target: str,
) -> FormalClaimNode:
    identity = _lean_identity(signature, target)
    return FormalClaimNode(
        node_id=node_id,
        proposition_sha256=identity.identity_sha256,
        identity_kind=LEAN,
        lean_identity=identity,
    )


def _install_synthetic_replay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        coverage,
        "replay_content_bound_evidence_from_governed_ratification",
        lambda receipt, **_kwargs: receipt,
    )


def _problem(
    supports: tuple[GovernedFormalSupport, ...] = (),
    *,
    leaf_b_kind: FormalPropositionIdentityKind = LEAN,
    inference_kind: FormalPropositionIdentityKind = LEAN,
    root_kind: FormalPropositionIdentityKind = LEAN,
    prefix: str = "test",
) -> FormalClaimCoverageProblem:
    root_signature = _digest(f"{prefix}:root")
    root_identity = _lean_identity(
        root_signature,
        _target(prefix, "root"),
    )
    inference_signature = _digest(f"{prefix}:inference")
    inference_identity = _lean_identity(
        inference_signature,
        _target(prefix, "inference"),
    )
    leaf_b_signature = _digest(f"{prefix}:leaf_b")
    leaf_b_identity = _lean_identity(
        leaf_b_signature,
        _target(prefix, "leaf_b"),
    )
    decomposition = make_formal_claim_decomposition(
        name=f"{prefix}-conjunction",
        root_node_id="root",
        nodes=(
            FormalClaimNode(
                node_id="root",
                proposition_sha256=(
                    root_identity.identity_sha256
                    if root_kind is LEAN
                    else root_signature
                ),
                identity_kind=root_kind,
                lean_identity=(root_identity if root_kind is LEAN else None),
                children=("leaf_a", "leaf_b"),
                inference_proposition_sha256=(
                    inference_identity.identity_sha256
                    if inference_kind is LEAN
                    else inference_signature
                ),
                inference_identity_kind=inference_kind,
                inference_lean_identity=(
                    inference_identity if inference_kind is LEAN else None
                ),
            ),
            _lean_node(
                node_id="leaf_a",
                signature=_digest(f"{prefix}:leaf_a"),
                target=_target(prefix, "leaf_a"),
            ),
            FormalClaimNode(
                node_id="leaf_b",
                proposition_sha256=(
                    leaf_b_identity.identity_sha256
                    if leaf_b_kind is LEAN
                    else leaf_b_signature
                ),
                identity_kind=leaf_b_kind,
                lean_identity=(
                    leaf_b_identity if leaf_b_kind is LEAN else None
                ),
            ),
        ),
        adapter_evidence_sha256=_digest(f"{prefix}:adapter"),
    )
    return FormalClaimCoverageProblem(
        decomposition=decomposition,
        supports=supports,
    )


def test_partial_leaf_coverage_reports_exact_frontier(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_synthetic_replay(monkeypatch)
    problem = _problem((
        _support(_digest("test:leaf_a"), _target("test", "leaf_a")),
    ))
    result = compile_formal_claim_coverage(problem)

    assert result.directly_ratified_node_ids == ("leaf_a",)
    assert result.bottom_up_covered_node_ids == ("leaf_a",)
    assert result.uncovered_leaf_node_ids == ("leaf_b",)
    assert result.uncovered_inference_node_ids == ("root",)
    assert result.blocked_internal_nodes == (("root", ("leaf_b",)),)
    assert result.residual_obligations == (
        ("lean_leaf_receipt", "leaf_b"),
        ("inference_rule_receipt", "root"),
        ("direct_root_receipt", "root"),
    )
    assert result.root_authority_promotion_eligible is False
    assert result.formal_authority_issued is False
    assert replay_formal_claim_coverage_certificate(result, problem) == result


def test_direct_root_receipt_cannot_bypass_leaf_or_inference_debt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_synthetic_replay(monkeypatch)
    result = compile_formal_claim_coverage(
        _problem((
            _support(_digest("test:root"), _target("test", "root")),
        ))
    )

    assert result.root_directly_ratified is True
    assert result.root_bottom_up_covered is False
    assert result.uncovered_leaf_node_ids == ("leaf_a", "leaf_b")
    assert result.uncovered_inference_node_ids == ("root",)
    assert result.root_authority_promotion_eligible is False


def test_complete_exact_coverage_is_eligible_but_issues_no_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_synthetic_replay(monkeypatch)
    supports = tuple(
        _support(signature, target)
        for role in ("leaf_a", "leaf_b", "inference", "root")
        for signature, target in ((
            _digest(f"test:{role}"),
            _target("test", role),
        ),)
    )
    result = compile_formal_claim_coverage(_problem(supports))

    assert result.all_required_leaves_covered is True
    assert result.all_inference_rules_covered is True
    assert result.root_bottom_up_covered is True
    assert result.root_directly_ratified is True
    assert result.root_authority_promotion_eligible is True
    assert result.residual_obligations == ()
    assert result.formal_authority_issued is False


def test_adapter_semantic_leaf_and_inference_remain_explicit_residuals(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_synthetic_replay(monkeypatch)
    problem = _problem(leaf_b_kind=SEMANTIC, inference_kind=SEMANTIC)
    result = compile_formal_claim_coverage(problem)

    assert result.uncovered_adapter_semantic_leaf_ids == ("leaf_b",)
    assert result.uncovered_adapter_semantic_inference_ids == ("root",)
    assert result.residual_obligations == (
        ("lean_leaf_receipt", "leaf_a"),
        ("adapter_semantic_leaf", "leaf_b"),
        ("adapter_semantic_inference", "root"),
        ("direct_root_receipt", "root"),
    )

    for signature, target in (
        (_digest("test:leaf_b"), "Semantic.leaf"),
        (_digest("test:inference"), "Semantic.inference"),
    ):
        crossed = replace(problem, supports=(_support(signature, target),))
        with pytest.raises(FormalClaimCoverageError) as error:
            compile_formal_claim_coverage(crossed)
        assert error.value.code == "formal_claim_support_extra"


def test_adapter_semantic_root_requires_formalization_not_a_receipt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_synthetic_replay(monkeypatch)
    result = compile_formal_claim_coverage(_problem(root_kind=SEMANTIC))

    assert result.root_identity_kind == "adapter_semantic"
    assert result.residual_obligations[-1] == (
        "direct_root_formalization",
        "root",
    )


def test_compiler_transfers_to_an_alien_vocabulary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_synthetic_replay(monkeypatch)
    prefix = "alien-valuation"
    supports = tuple(
        _support(
            _digest(f"{prefix}:{role}"),
            _target(prefix, role),
        )
        for role in ("leaf_a", "leaf_b", "inference", "root")
    )
    result = compile_formal_claim_coverage(
        _problem(supports, prefix=prefix)
    )

    assert result.root_authority_promotion_eligible is True
    assert "puiseux" not in str(result.to_dict()).lower()


def test_duplicate_extra_and_nonformal_support_are_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_synthetic_replay(monkeypatch)
    support = _support(
        _digest("test:leaf_a"),
        _target("test", "leaf_a"),
    )
    with pytest.raises(FormalClaimCoverageError) as duplicate:
        compile_formal_claim_coverage(_problem((support, support)))
    assert duplicate.value.code == "formal_claim_support_duplicate"

    same_identity = _support(
        _digest("test:leaf_a"),
        _target("test", "leaf_a"),
        evidence_tag="second-proof",
    )
    with pytest.raises(FormalClaimCoverageError) as identity_duplicate:
        compile_formal_claim_coverage(_problem((support, same_identity)))
    assert (
        identity_duplicate.value.code
        == "formal_claim_support_identity_duplicate"
    )

    with pytest.raises(FormalClaimCoverageError) as extra:
        compile_formal_claim_coverage(
            _problem((_support(_digest("extra"), "test.extra"),))
        )
    assert extra.value.code == "formal_claim_support_extra"

    ordinary = make_content_bound_evidence(
        claim_id="finite_check",
        subject_id="Test.leafA",
        context_sha256=_digest("ordinary-context"),
        authority=EvidenceAuthority.FINITE_EXPERIMENT,
        scope_id="finite_prefix",
        conclusion={"checked": True},
        evidence_sha256=_digest("ordinary-evidence"),
    )
    nonformal = replace(support, receipt=ordinary)
    with pytest.raises(FormalClaimCoverageError) as wrong_authority:
        compile_formal_claim_coverage(_problem((nonformal,)))
    assert wrong_authority.value.code == "formal_claim_support_authority_wrong"


def test_cross_context_replay_failure_is_preserved_as_typed_debt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        coverage,
        "replay_content_bound_evidence_from_governed_ratification",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            ValueError("crossed context")
        ),
    )
    with pytest.raises(FormalClaimCoverageError) as error:
        compile_formal_claim_coverage(
            _problem((
                _support(
                    _digest("test:leaf_a"),
                    _target("test", "leaf_a"),
                ),
            ))
        )
    assert error.value.code == "formal_claim_support_replay_failed"


@pytest.mark.parametrize(
    ("target", "source_tag"),
    (
        ("alien.leaf_a", "primary"),
        (_target("test", "leaf_a"), "alien-import-context"),
    ),
)
def test_same_printed_signature_cannot_cross_target_or_source_context(
    monkeypatch: pytest.MonkeyPatch,
    target: str,
    source_tag: str,
) -> None:
    _install_synthetic_replay(monkeypatch)
    alien = _support(
        _digest("test:leaf_a"),
        target,
        source_tag=source_tag,
    )

    with pytest.raises(FormalClaimCoverageError) as error:
        compile_formal_claim_coverage(_problem((alien,)))
    assert error.value.code == "formal_claim_support_extra"


def test_graph_cycles_unreachable_nodes_and_tampering_are_rejected() -> None:
    root_identity = _lean_identity(_digest("graph:root"), "graph.root")
    inference_identity = _lean_identity(
        _digest("graph:inference"),
        "graph.inference",
    )
    root = FormalClaimNode(
        node_id="root",
        proposition_sha256=root_identity.identity_sha256,
        identity_kind=LEAN,
        lean_identity=root_identity,
        children=("child",),
        inference_proposition_sha256=(
            inference_identity.identity_sha256
        ),
        inference_identity_kind=LEAN,
        inference_lean_identity=inference_identity,
    )
    child = _lean_node(
        node_id="child",
        signature=_digest("graph:child"),
        target="graph.child",
    )
    valid = make_formal_claim_decomposition(
        name="graph-attacks",
        root_node_id="root",
        nodes=(root, child),
        adapter_evidence_sha256=_digest("graph:adapter"),
    )

    crossed = replace(valid, decomposition_sha256="f" * 64)
    with pytest.raises(FormalClaimCoverageError) as digest_error:
        coverage.replay_formal_claim_decomposition(crossed)
    assert digest_error.value.code == "formal_claim_decomposition_digest_mismatch"

    unreachable = _lean_node(
        node_id="orphan",
        signature=_digest("graph:orphan"),
        target="graph.orphan",
    )
    provisional = replace(valid, nodes=(root, child, unreachable))
    provisional = replace(
        provisional,
        decomposition_sha256=content_sha256(provisional.core_payload()),
    )
    with pytest.raises(FormalClaimCoverageError) as unreachable_error:
        coverage.replay_formal_claim_decomposition(provisional)
    assert unreachable_error.value.code == "formal_claim_node_unreachable"

    child_inference_identity = _lean_identity(
        _digest("graph:child-inference"),
        "graph.childInference",
    )
    cyclic_child = replace(
        child,
        children=("root",),
        inference_proposition_sha256=(
            child_inference_identity.identity_sha256
        ),
        inference_identity_kind=LEAN,
        inference_lean_identity=child_inference_identity,
    )
    cyclic = replace(valid, nodes=(root, cyclic_child))
    cyclic = replace(
        cyclic,
        decomposition_sha256=content_sha256(cyclic.core_payload()),
    )
    with pytest.raises(FormalClaimCoverageError) as cycle_error:
        coverage.replay_formal_claim_decomposition(cyclic)
    assert cycle_error.value.code == "formal_claim_cycle"


def test_graph_rejects_duplicate_formal_and_semantic_identities() -> None:
    shared = _digest("identity:shared")
    root_identity = _lean_identity(_digest("identity:root"), "identity.root")
    shared_identity = _lean_identity(shared, "identity.shared")
    root = FormalClaimNode(
        node_id="root",
        proposition_sha256=root_identity.identity_sha256,
        identity_kind=LEAN,
        lean_identity=root_identity,
        children=("child",),
        inference_proposition_sha256=shared_identity.identity_sha256,
        inference_identity_kind=LEAN,
        inference_lean_identity=shared_identity,
    )
    formal_child = FormalClaimNode(
        node_id="child",
        proposition_sha256=shared_identity.identity_sha256,
        identity_kind=LEAN,
        lean_identity=shared_identity,
    )
    with pytest.raises(FormalClaimCoverageError) as formal_error:
        make_formal_claim_decomposition(
            name="formal-identity-collision",
            root_node_id="root",
            nodes=(root, formal_child),
            adapter_evidence_sha256=_digest("identity:adapter"),
        )
    assert formal_error.value.code == "formal_claim_lean_identity_duplicate"

    semantic_root = replace(
        root,
        inference_proposition_sha256=_digest("identity:inference"),
        inference_identity_kind=SEMANTIC,
        inference_lean_identity=None,
    )
    semantic_children = (
        FormalClaimNode("child", shared, SEMANTIC),
        FormalClaimNode("other", shared, SEMANTIC),
    )
    semantic_root = replace(
        semantic_root,
        children=("child", "other"),
    )
    with pytest.raises(FormalClaimCoverageError) as semantic_error:
        make_formal_claim_decomposition(
            name="semantic-identity-collision",
            root_node_id="root",
            nodes=(semantic_root, *semantic_children),
            adapter_evidence_sha256=_digest("identity:adapter"),
        )
    assert (
        semantic_error.value.code
        == "formal_claim_semantic_identity_duplicate"
    )


def test_coverage_certificate_tampering_does_not_replay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_synthetic_replay(monkeypatch)
    problem = _problem()
    certificate = compile_formal_claim_coverage(problem)
    crossed = replace(certificate, formal_authority_issued=True)

    with pytest.raises(FormalClaimCoverageError) as error:
        replay_formal_claim_coverage_certificate(crossed, problem)
    assert error.value.code == "formal_claim_coverage_certificate_mismatch"
