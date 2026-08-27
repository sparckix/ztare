"""Exact formal-leaf coverage over governed theorem receipts.

This compiler diagnoses whether a declared claim decomposition has complete
formal support.  It never constructs formal-kernel authority.  Receipt
authorization is delegated to the existing governed-ratification bridge, and
root promotion remains a later LeanMill ratification transition.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from enum import Enum
import json
from pathlib import Path
from typing import Any

from ztare.common.content_bound_evidence import (
    ContentBoundEvidenceReceipt,
    EvidenceAuthority,
)
from ztare.common.content_identity import content_sha256, require_sha256_digest
from ztare.leanmill.filtered_evidence_authority import (
    replay_content_bound_evidence_from_governed_ratification,
)


DECOMPOSITION_SCHEMA = "leanmill.formal_claim_decomposition.v1"
COVERAGE_CERTIFICATE_SCHEMA = "leanmill.formal_claim_coverage_certificate.v1"
FORMAL_PROPOSITION_IDENTITY_SCHEMA = (
    "leanmill.governed_formal_proposition_identity.v1"
)


class FormalClaimCoverageError(ValueError):
    """A typed identity or coverage failure in a formal claim DAG."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


class FormalPropositionIdentityKind(str, Enum):
    """Whether a proposition has a governed Lean elaboration context."""

    GOVERNED_LEAN_PROPOSITION = "governed_lean_proposition"
    ADAPTER_SEMANTIC = "adapter_semantic"


@dataclass(frozen=True)
class GovernedFormalPropositionIdentity:
    """The theorem context that fixes one elaborated Lean proposition."""

    schema: str
    target_id: str
    target_signature_sha256: str
    posed_source_sha256: str
    toolchain_identity_sha256: str
    identity_sha256: str

    def core_payload(self) -> dict[str, str]:
        return {
            "schema": self.schema,
            "target_id": self.target_id,
            "target_signature_sha256": self.target_signature_sha256,
            "posed_source_sha256": self.posed_source_sha256,
            "toolchain_identity_sha256": self.toolchain_identity_sha256,
        }

    def to_dict(self) -> dict[str, str]:
        return {
            **self.core_payload(),
            "identity_sha256": self.identity_sha256,
        }


@dataclass(frozen=True)
class FormalClaimNode:
    """One proposition and its required child propositions."""

    node_id: str
    proposition_sha256: str
    identity_kind: FormalPropositionIdentityKind
    lean_identity: GovernedFormalPropositionIdentity | None = None
    children: tuple[str, ...] = ()
    inference_proposition_sha256: str | None = None
    inference_identity_kind: FormalPropositionIdentityKind | None = None
    inference_lean_identity: GovernedFormalPropositionIdentity | None = None


@dataclass(frozen=True)
class FormalClaimDecomposition:
    """One content-bound finite decomposition rooted at a broad claim."""

    schema: str
    name: str
    root_node_id: str
    nodes: tuple[FormalClaimNode, ...]
    adapter_evidence_sha256: str
    decomposition_sha256: str

    def core_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "name": self.name,
            "root_node_id": self.root_node_id,
            "nodes": [
                {
                    "node_id": node.node_id,
                    "proposition_sha256": node.proposition_sha256,
                    "identity_kind": (
                        node.identity_kind.value
                        if isinstance(
                            node.identity_kind,
                            FormalPropositionIdentityKind,
                        )
                        else node.identity_kind
                    ),
                    "lean_identity": (
                        node.lean_identity.to_dict()
                        if node.lean_identity is not None
                        else None
                    ),
                    "children": list(node.children),
                    "inference_proposition_sha256": (
                        node.inference_proposition_sha256
                    ),
                    "inference_identity_kind": (
                        node.inference_identity_kind.value
                        if isinstance(
                            node.inference_identity_kind,
                            FormalPropositionIdentityKind,
                        )
                        else node.inference_identity_kind
                    ),
                    "inference_lean_identity": (
                        node.inference_lean_identity.to_dict()
                        if node.inference_lean_identity is not None
                        else None
                    ),
                }
                for node in sorted(self.nodes, key=lambda item: item.node_id)
            ],
            "adapter_evidence_sha256": self.adapter_evidence_sha256,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.core_payload(),
            "decomposition_sha256": self.decomposition_sha256,
        }


@dataclass(frozen=True)
class GovernedFormalSupport:
    """One formal receipt plus every byte needed for governed replay."""

    receipt: ContentBoundEvidenceReceipt
    certificate_ledger: str | Path
    governed_record_sha256: str
    parity_ledger: str | Path
    target: str
    expected_signature: str
    posed_source: str
    proof_text: str
    goal: str
    lean_root: str | Path
    repo_root: str | Path | None = None
    expected_provider: str | None = None


@dataclass(frozen=True)
class FormalClaimCoverageProblem:
    """A formal claim DAG and the governed support offered for it."""

    decomposition: FormalClaimDecomposition
    supports: tuple[GovernedFormalSupport, ...]


@dataclass(frozen=True)
class FormalClaimCoverageCertificate:
    """The exact formalization coverage and residual of one claim DAG."""

    schema: str
    problem_name: str
    decomposition_sha256: str
    root_node_id: str
    root_identity_kind: str
    leaf_node_ids: tuple[str, ...]
    internal_node_ids: tuple[str, ...]
    formal_receipt_sha256s: tuple[str, ...]
    directly_ratified_node_ids: tuple[str, ...]
    supported_inference_node_ids: tuple[str, ...]
    bottom_up_covered_node_ids: tuple[str, ...]
    uncovered_leaf_node_ids: tuple[str, ...]
    uncovered_adapter_semantic_leaf_ids: tuple[str, ...]
    uncovered_inference_node_ids: tuple[str, ...]
    uncovered_adapter_semantic_inference_ids: tuple[str, ...]
    blocked_internal_nodes: tuple[tuple[str, tuple[str, ...]], ...]
    residual_obligations: tuple[tuple[str, str], ...]
    all_required_leaves_covered: bool
    all_inference_rules_covered: bool
    root_bottom_up_covered: bool
    root_directly_ratified: bool
    root_authority_promotion_eligible: bool
    formal_authority_issued: bool
    coverage_certificate_sha256: str

    def core_payload(self) -> dict[str, Any]:
        result = asdict(self)
        result.pop("coverage_certificate_sha256")
        for field in (
            "leaf_node_ids",
            "internal_node_ids",
            "formal_receipt_sha256s",
            "directly_ratified_node_ids",
            "supported_inference_node_ids",
            "bottom_up_covered_node_ids",
            "uncovered_leaf_node_ids",
            "uncovered_adapter_semantic_leaf_ids",
            "uncovered_inference_node_ids",
            "uncovered_adapter_semantic_inference_ids",
        ):
            result[field] = list(result[field])
        result["blocked_internal_nodes"] = [
            {"node_id": node_id, "missing_children": list(children)}
            for node_id, children in self.blocked_internal_nodes
        ]
        result["residual_obligations"] = [
            {"kind": kind, "identity": identity}
            for kind, identity in self.residual_obligations
        ]
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.core_payload(),
            "coverage_certificate_sha256": self.coverage_certificate_sha256,
        }


def _require_digest(value: Any, *, code: str, context: str) -> str:
    try:
        return require_sha256_digest(value, context=context)
    except ValueError as error:
        raise FormalClaimCoverageError(code, str(error)) from error


def replay_governed_formal_proposition_identity(
    identity: GovernedFormalPropositionIdentity,
) -> GovernedFormalPropositionIdentity:
    """Replay one target/source/toolchain-bound proposition identity."""

    if identity.schema != FORMAL_PROPOSITION_IDENTITY_SCHEMA:
        raise FormalClaimCoverageError(
            "formal_proposition_identity_schema_mismatch",
            "the governed formal proposition identity schema is unknown",
        )
    if not isinstance(identity.target_id, str) or not identity.target_id.strip():
        raise FormalClaimCoverageError(
            "formal_proposition_target_empty",
            "the governed formal proposition target must be nonempty",
        )
    for field, value in (
        ("target signature", identity.target_signature_sha256),
        ("posed source", identity.posed_source_sha256),
        ("toolchain", identity.toolchain_identity_sha256),
        ("identity", identity.identity_sha256),
    ):
        _require_digest(
            value,
            code="formal_proposition_identity_digest_malformed",
            context=f"governed formal proposition {field}",
        )
    if content_sha256(identity.core_payload()) != identity.identity_sha256:
        raise FormalClaimCoverageError(
            "formal_proposition_identity_digest_mismatch",
            "the governed formal proposition identity content changed",
        )
    return identity


def make_governed_formal_proposition_identity(
    *,
    target_id: str,
    target_signature_sha256: str,
    posed_source_sha256: str,
    toolchain_identity_sha256: str,
) -> GovernedFormalPropositionIdentity:
    """Construct one canonical elaborated-proposition identity."""

    provisional = GovernedFormalPropositionIdentity(
        schema=FORMAL_PROPOSITION_IDENTITY_SCHEMA,
        target_id=target_id,
        target_signature_sha256=target_signature_sha256,
        posed_source_sha256=posed_source_sha256,
        toolchain_identity_sha256=toolchain_identity_sha256,
        identity_sha256="0" * 64,
    )
    identity = replace(
        provisional,
        identity_sha256=content_sha256(provisional.core_payload()),
    )
    return replay_governed_formal_proposition_identity(identity)


def governed_formal_proposition_identity_from_receipt(
    receipt: ContentBoundEvidenceReceipt,
) -> GovernedFormalPropositionIdentity:
    """Project identity only; authority is still replayed during coverage."""

    if (
        receipt.authority is not EvidenceAuthority.FORMAL_KERNEL
        or receipt.authority_binding_json is None
    ):
        raise FormalClaimCoverageError(
            "formal_proposition_receipt_authority_wrong",
            "only a formal-kernel receipt carries a formal proposition identity",
        )
    try:
        binding = json.loads(receipt.authority_binding_json)
    except (TypeError, json.JSONDecodeError) as error:
        raise FormalClaimCoverageError(
            "formal_proposition_receipt_binding_malformed",
            "the formal receipt binding is not valid JSON",
        ) from error
    if not isinstance(binding, dict):
        raise FormalClaimCoverageError(
            "formal_proposition_receipt_binding_malformed",
            "the formal receipt binding must be a JSON object",
        )
    return make_governed_formal_proposition_identity(
        target_id=str(binding.get("target_id") or ""),
        target_signature_sha256=str(
            binding.get("target_signature_sha256") or ""
        ),
        posed_source_sha256=str(binding.get("source_sha256") or ""),
        toolchain_identity_sha256=str(
            binding.get("toolchain_identity_sha256") or ""
        ),
    )


def _validate_graph(
    decomposition: FormalClaimDecomposition,
) -> tuple[dict[str, FormalClaimNode], tuple[str, ...]]:
    if decomposition.schema != DECOMPOSITION_SCHEMA:
        raise FormalClaimCoverageError(
            "formal_claim_schema_mismatch",
            "the formal claim decomposition schema is not recognized",
        )
    if not isinstance(decomposition.name, str) or not decomposition.name.strip():
        raise FormalClaimCoverageError(
            "formal_claim_name_empty",
            "the formal claim decomposition name must be nonempty",
        )
    if not decomposition.nodes:
        raise FormalClaimCoverageError(
            "formal_claim_nodes_empty",
            "the formal claim decomposition needs at least one node",
        )
    _require_digest(
        decomposition.adapter_evidence_sha256,
        code="formal_claim_adapter_digest_malformed",
        context="formal claim adapter evidence",
    )
    _require_digest(
        decomposition.decomposition_sha256,
        code="formal_claim_decomposition_digest_malformed",
        context="formal claim decomposition",
    )
    nodes: dict[str, FormalClaimNode] = {}
    proposition_identities: dict[
        tuple[FormalPropositionIdentityKind, str], str
    ] = {}
    for node in decomposition.nodes:
        if not isinstance(node.node_id, str) or not node.node_id.strip():
            raise FormalClaimCoverageError(
                "formal_claim_node_id_empty",
                "every formal claim node needs a nonempty identity",
            )
        if node.node_id in nodes:
            raise FormalClaimCoverageError(
                "formal_claim_node_duplicate",
                f"formal claim node {node.node_id!r} occurs more than once",
            )
        if not isinstance(node.identity_kind, FormalPropositionIdentityKind):
            raise FormalClaimCoverageError(
                "formal_claim_identity_kind_unknown",
                f"formal claim node {node.node_id!r} has an unknown identity kind",
            )
        _require_digest(
            node.proposition_sha256,
            code="formal_claim_proposition_digest_malformed",
            context=f"formal claim proposition {node.node_id}",
        )
        if (
            node.identity_kind
            is FormalPropositionIdentityKind.GOVERNED_LEAN_PROPOSITION
        ):
            if node.lean_identity is None:
                raise FormalClaimCoverageError(
                    "formal_claim_lean_identity_missing",
                    f"formal claim node {node.node_id!r} lacks its governed "
                    "Lean proposition identity",
                )
            lean_identity = replay_governed_formal_proposition_identity(
                node.lean_identity
            )
            if node.proposition_sha256 != lean_identity.identity_sha256:
                raise FormalClaimCoverageError(
                    "formal_claim_lean_identity_mismatch",
                    f"formal claim node {node.node_id!r} crossed its governed "
                    "Lean proposition identity",
                )
        elif node.lean_identity is not None:
            raise FormalClaimCoverageError(
                "formal_claim_semantic_has_lean_identity",
                f"semantic formal claim node {node.node_id!r} carries a Lean "
                "proposition identity",
            )
        proposition_key = (node.identity_kind, node.proposition_sha256)
        previous_role = proposition_identities.setdefault(
            proposition_key,
            f"proposition:{node.node_id}",
        )
        if previous_role != f"proposition:{node.node_id}":
            raise FormalClaimCoverageError(
                (
                    "formal_claim_lean_identity_duplicate"
                    if node.identity_kind
                    is FormalPropositionIdentityKind.GOVERNED_LEAN_PROPOSITION
                    else "formal_claim_semantic_identity_duplicate"
                ),
                "one proposition identity occurs in multiple claim roles",
            )
        if len(set(node.children)) != len(node.children):
            raise FormalClaimCoverageError(
                "formal_claim_child_duplicate",
                f"formal claim node {node.node_id!r} repeats a child",
            )
        if node.children:
            _require_digest(
                node.inference_proposition_sha256,
                code="formal_claim_inference_digest_malformed",
                context=f"formal claim inference {node.node_id}",
            )
            if not isinstance(
                node.inference_identity_kind,
                FormalPropositionIdentityKind,
            ):
                raise FormalClaimCoverageError(
                    "formal_claim_inference_identity_kind_unknown",
                    f"formal claim inference {node.node_id!r} has an "
                    "unknown identity kind",
                )
            if (
                node.inference_identity_kind
                is FormalPropositionIdentityKind.GOVERNED_LEAN_PROPOSITION
            ):
                if node.inference_lean_identity is None:
                    raise FormalClaimCoverageError(
                        "formal_claim_inference_lean_identity_missing",
                        f"formal claim inference {node.node_id!r} lacks its "
                        "governed Lean proposition identity",
                    )
                inference_identity = (
                    replay_governed_formal_proposition_identity(
                        node.inference_lean_identity
                    )
                )
                if node.inference_proposition_sha256 != (
                    inference_identity.identity_sha256
                ):
                    raise FormalClaimCoverageError(
                        "formal_claim_inference_lean_identity_mismatch",
                        f"formal claim inference {node.node_id!r} crossed its "
                        "governed Lean proposition identity",
                    )
            elif node.inference_lean_identity is not None:
                raise FormalClaimCoverageError(
                    "formal_claim_semantic_inference_has_lean_identity",
                    f"semantic inference {node.node_id!r} carries a Lean "
                    "proposition identity",
                )
            inference_key = (
                node.inference_identity_kind,
                str(node.inference_proposition_sha256),
            )
            previous_role = proposition_identities.setdefault(
                inference_key,
                f"inference:{node.node_id}",
            )
            if previous_role != f"inference:{node.node_id}":
                raise FormalClaimCoverageError(
                    (
                        "formal_claim_lean_identity_duplicate"
                        if node.inference_identity_kind
                        is FormalPropositionIdentityKind.GOVERNED_LEAN_PROPOSITION
                        else "formal_claim_semantic_identity_duplicate"
                    ),
                    "one proposition identity occurs in multiple claim roles",
                )
        elif (
            node.inference_proposition_sha256 is not None
            or node.inference_identity_kind is not None
            or node.inference_lean_identity is not None
        ):
            raise FormalClaimCoverageError(
                "formal_claim_leaf_has_inference",
                f"formal claim leaf {node.node_id!r} carries an inference rule",
            )
        nodes[node.node_id] = node
    if decomposition.root_node_id not in nodes:
        raise FormalClaimCoverageError(
            "formal_claim_root_missing",
            "the formal claim root is absent from the node set",
        )
    for node in nodes.values():
        for child in node.children:
            if child not in nodes:
                raise FormalClaimCoverageError(
                    "formal_claim_child_missing",
                    f"formal claim child {child!r} is absent",
                )
            if child == node.node_id:
                raise FormalClaimCoverageError(
                    "formal_claim_cycle",
                    f"formal claim node {node.node_id!r} is its own child",
                )

    visiting: set[str] = set()
    visited: set[str] = set()
    order: list[str] = []

    def visit(node_id: str) -> None:
        if node_id in visiting:
            raise FormalClaimCoverageError(
                "formal_claim_cycle",
                "the formal claim decomposition contains a cycle",
            )
        if node_id in visited:
            return
        visiting.add(node_id)
        for child_id in nodes[node_id].children:
            visit(child_id)
        visiting.remove(node_id)
        visited.add(node_id)
        order.append(node_id)

    visit(decomposition.root_node_id)
    if visited != set(nodes):
        unreachable = sorted(set(nodes) - visited)
        raise FormalClaimCoverageError(
            "formal_claim_node_unreachable",
            f"formal claim nodes are unreachable from the root: {unreachable}",
        )
    if content_sha256(decomposition.core_payload()) != (
        decomposition.decomposition_sha256
    ):
        raise FormalClaimCoverageError(
            "formal_claim_decomposition_digest_mismatch",
            "the formal claim decomposition content does not replay",
        )
    return nodes, tuple(order)


def replay_formal_claim_decomposition(
    decomposition: FormalClaimDecomposition,
) -> FormalClaimDecomposition:
    """Replay the complete identity and graph structure of one claim DAG."""

    _validate_graph(decomposition)
    return decomposition


def make_formal_claim_decomposition(
    *,
    name: str,
    root_node_id: str,
    nodes: tuple[FormalClaimNode, ...],
    adapter_evidence_sha256: str,
) -> FormalClaimDecomposition:
    """Create one canonical formal claim decomposition."""

    provisional = FormalClaimDecomposition(
        schema=DECOMPOSITION_SCHEMA,
        name=name,
        root_node_id=root_node_id,
        nodes=nodes,
        adapter_evidence_sha256=adapter_evidence_sha256,
        decomposition_sha256="0" * 64,
    )
    decomposition = replace(
        provisional,
        decomposition_sha256=content_sha256(provisional.core_payload()),
    )
    return replay_formal_claim_decomposition(decomposition)


def _replay_support(
    support: GovernedFormalSupport,
) -> ContentBoundEvidenceReceipt:
    try:
        receipt = replay_content_bound_evidence_from_governed_ratification(
            support.receipt,
            certificate_ledger=support.certificate_ledger,
            governed_record_sha256=support.governed_record_sha256,
            parity_ledger=support.parity_ledger,
            target=support.target,
            expected_signature=support.expected_signature,
            posed_source=support.posed_source,
            proof_text=support.proof_text,
            goal=support.goal,
            lean_root=support.lean_root,
            repo_root=support.repo_root,
            expected_provider=support.expected_provider,
        )
    except ValueError as error:
        raise FormalClaimCoverageError(
            "formal_claim_support_replay_failed",
            str(error),
        ) from error
    if receipt.authority is not EvidenceAuthority.FORMAL_KERNEL:
        raise FormalClaimCoverageError(
            "formal_claim_support_authority_wrong",
            "formal claim coverage accepts only governed formal-kernel receipts",
        )
    return receipt


def compile_formal_claim_coverage(
    problem: FormalClaimCoverageProblem,
) -> FormalClaimCoverageCertificate:
    """Compute exact governed coverage and the remaining formal frontier."""

    decomposition = replay_formal_claim_decomposition(problem.decomposition)
    nodes, order = _validate_graph(decomposition)
    receipts = tuple(_replay_support(support) for support in problem.supports)
    receipt_sha256s = tuple(receipt.receipt_sha256 for receipt in receipts)
    if len(set(receipt_sha256s)) != len(receipt_sha256s):
        raise FormalClaimCoverageError(
            "formal_claim_support_duplicate",
            "one formal receipt occurs more than once",
        )
    identity_to_receipt: dict[str, ContentBoundEvidenceReceipt] = {}
    for receipt in receipts:
        formal_identity = governed_formal_proposition_identity_from_receipt(
            receipt
        )
        identity_sha256 = formal_identity.identity_sha256
        if identity_sha256 in identity_to_receipt:
            raise FormalClaimCoverageError(
                "formal_claim_support_identity_duplicate",
                "multiple formal receipts claim the same proposition identity",
            )
        identity_to_receipt[identity_sha256] = receipt

    proposition_roles = {
        node.proposition_sha256: node.node_id
        for node in nodes.values()
        if node.identity_kind
        is FormalPropositionIdentityKind.GOVERNED_LEAN_PROPOSITION
    }
    inference_roles = {
        str(node.inference_proposition_sha256): node.node_id
        for node in nodes.values()
        if (
            node.inference_proposition_sha256 is not None
            and node.inference_identity_kind
            is FormalPropositionIdentityKind.GOVERNED_LEAN_PROPOSITION
        )
    }
    allowed_identities = set(proposition_roles) | set(inference_roles)
    extra_identities = sorted(set(identity_to_receipt) - allowed_identities)
    if extra_identities:
        raise FormalClaimCoverageError(
            "formal_claim_support_extra",
            "formal support does not belong to the declared claim decomposition",
        )

    directly_ratified = {
        node_id
        for identity, node_id in proposition_roles.items()
        if identity in identity_to_receipt
    }
    supported_inferences = {
        node_id
        for identity, node_id in inference_roles.items()
        if identity in identity_to_receipt
    }
    bottom_up: set[str] = set()
    blocked: list[tuple[str, tuple[str, ...]]] = []
    for node_id in order:
        node = nodes[node_id]
        if not node.children:
            if node_id in directly_ratified:
                bottom_up.add(node_id)
            continue
        missing_children = tuple(
            child for child in node.children if child not in bottom_up
        )
        if node_id in supported_inferences and not missing_children:
            bottom_up.add(node_id)
        else:
            blocked.append((node_id, missing_children))

    leaves = tuple(sorted(
        node_id for node_id, node in nodes.items() if not node.children
    ))
    internal = tuple(sorted(set(nodes) - set(leaves)))
    uncovered_leaves = tuple(sorted(set(leaves) - directly_ratified))
    uncovered_semantic = tuple(
        node_id
        for node_id in uncovered_leaves
        if nodes[node_id].identity_kind
        is FormalPropositionIdentityKind.ADAPTER_SEMANTIC
    )
    uncovered_inferences = tuple(
        sorted(set(internal) - supported_inferences)
    )
    uncovered_semantic_inferences = tuple(
        node_id
        for node_id in uncovered_inferences
        if nodes[node_id].inference_identity_kind
        is FormalPropositionIdentityKind.ADAPTER_SEMANTIC
    )
    root = decomposition.root_node_id
    root_bottom_up = root in bottom_up
    root_direct = root in directly_ratified
    all_leaves = not uncovered_leaves
    all_rules = not uncovered_inferences
    eligible = all_leaves and all_rules and root_bottom_up and root_direct
    residual: list[tuple[str, str]] = [
        (
            "adapter_semantic_leaf"
            if node_id in uncovered_semantic
            else "lean_leaf_receipt",
            node_id,
        )
        for node_id in uncovered_leaves
    ]
    residual.extend(
        (
            "adapter_semantic_inference"
            if node_id in uncovered_semantic_inferences
            else "inference_rule_receipt",
            node_id,
        )
        for node_id in uncovered_inferences
    )
    if not root_direct:
        residual.append((
            "direct_root_formalization"
            if nodes[root].identity_kind
            is FormalPropositionIdentityKind.ADAPTER_SEMANTIC
            else "direct_root_receipt",
            root,
        ))

    core = {
        "schema": COVERAGE_CERTIFICATE_SCHEMA,
        "problem_name": decomposition.name,
        "decomposition_sha256": decomposition.decomposition_sha256,
        "root_node_id": root,
        "root_identity_kind": nodes[root].identity_kind.value,
        "leaf_node_ids": list(leaves),
        "internal_node_ids": list(internal),
        "formal_receipt_sha256s": sorted(receipt_sha256s),
        "directly_ratified_node_ids": sorted(directly_ratified),
        "supported_inference_node_ids": sorted(supported_inferences),
        "bottom_up_covered_node_ids": sorted(bottom_up),
        "uncovered_leaf_node_ids": list(uncovered_leaves),
        "uncovered_adapter_semantic_leaf_ids": list(uncovered_semantic),
        "uncovered_inference_node_ids": list(uncovered_inferences),
        "uncovered_adapter_semantic_inference_ids": list(
            uncovered_semantic_inferences
        ),
        "blocked_internal_nodes": [
            {"node_id": node_id, "missing_children": list(children)}
            for node_id, children in sorted(blocked)
        ],
        "residual_obligations": [
            {"kind": kind, "identity": identity}
            for kind, identity in residual
        ],
        "all_required_leaves_covered": all_leaves,
        "all_inference_rules_covered": all_rules,
        "root_bottom_up_covered": root_bottom_up,
        "root_directly_ratified": root_direct,
        "root_authority_promotion_eligible": eligible,
        "formal_authority_issued": False,
    }
    return FormalClaimCoverageCertificate(
        schema=COVERAGE_CERTIFICATE_SCHEMA,
        problem_name=decomposition.name,
        decomposition_sha256=decomposition.decomposition_sha256,
        root_node_id=root,
        root_identity_kind=nodes[root].identity_kind.value,
        leaf_node_ids=leaves,
        internal_node_ids=internal,
        formal_receipt_sha256s=tuple(sorted(receipt_sha256s)),
        directly_ratified_node_ids=tuple(sorted(directly_ratified)),
        supported_inference_node_ids=tuple(sorted(supported_inferences)),
        bottom_up_covered_node_ids=tuple(sorted(bottom_up)),
        uncovered_leaf_node_ids=uncovered_leaves,
        uncovered_adapter_semantic_leaf_ids=uncovered_semantic,
        uncovered_inference_node_ids=uncovered_inferences,
        uncovered_adapter_semantic_inference_ids=(
            uncovered_semantic_inferences
        ),
        blocked_internal_nodes=tuple(sorted(blocked)),
        residual_obligations=tuple(residual),
        all_required_leaves_covered=all_leaves,
        all_inference_rules_covered=all_rules,
        root_bottom_up_covered=root_bottom_up,
        root_directly_ratified=root_direct,
        root_authority_promotion_eligible=eligible,
        formal_authority_issued=False,
        coverage_certificate_sha256=content_sha256(core),
    )


def replay_formal_claim_coverage_certificate(
    certificate: FormalClaimCoverageCertificate,
    problem: FormalClaimCoverageProblem,
) -> FormalClaimCoverageCertificate:
    """Replay a certificate against its exact DAG and governed supports."""

    expected = compile_formal_claim_coverage(problem)
    if certificate != expected:
        raise FormalClaimCoverageError(
            "formal_claim_coverage_certificate_mismatch",
            "the formal claim coverage certificate does not replay",
        )
    if content_sha256(certificate.core_payload()) != (
        certificate.coverage_certificate_sha256
    ):
        raise FormalClaimCoverageError(
            "formal_claim_coverage_certificate_digest_mismatch",
            "the formal claim coverage certificate content digest changed",
        )
    return certificate


__all__ = [
    "COVERAGE_CERTIFICATE_SCHEMA",
    "DECOMPOSITION_SCHEMA",
    "FORMAL_PROPOSITION_IDENTITY_SCHEMA",
    "FormalClaimCoverageCertificate",
    "FormalClaimCoverageError",
    "FormalClaimCoverageProblem",
    "FormalClaimDecomposition",
    "FormalClaimNode",
    "FormalPropositionIdentityKind",
    "GovernedFormalPropositionIdentity",
    "GovernedFormalSupport",
    "compile_formal_claim_coverage",
    "governed_formal_proposition_identity_from_receipt",
    "make_formal_claim_decomposition",
    "make_governed_formal_proposition_identity",
    "replay_governed_formal_proposition_identity",
    "replay_formal_claim_coverage_certificate",
    "replay_formal_claim_decomposition",
]
