#!/usr/bin/env python3
"""Measure exact formal coverage of the critical Puiseux terminal.

The adapter replays the existing Puiseux certificates and the governed
arithmetic theorem receipt.  Remaining mathematical propositions retain
adapter-semantic identity, so this script cannot promote the terminal to
formal-kernel authority.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
SRC_ROOT = REPO / "src"
JACOBIAN = REPO / (
    "research_areas/pre_registrations/"
    "axiompack_jacobian_field_parametric_20260720"
)
for path in (str(SRC_ROOT), str(JACOBIAN)):
    if path not in sys.path:
        sys.path.insert(0, path)

from gauge_pure_contact_zero_witt_puiseux_obstruction import (  # noqa: E402
    run as puiseux_run,
)
from ztare.common.content_identity import content_sha256  # noqa: E402
from ztare.leanmill.filtered_evidence_authority import (  # noqa: E402
    make_content_bound_evidence_from_governed_ratification,
)
from ztare.leanmill.formal_claim_coverage import (  # noqa: E402
    FormalClaimCoverageProblem,
    FormalClaimNode,
    FormalPropositionIdentityKind,
    GovernedFormalPropositionIdentity,
    GovernedFormalSupport,
    compile_formal_claim_coverage,
    governed_formal_proposition_identity_from_receipt,
    make_formal_claim_decomposition,
    replay_formal_claim_coverage_certificate,
)
from ztare.leanmill.governed_ratification import (  # noqa: E402
    normalized_target_signature,
)
from ztare.leanmill.lean_source import (  # noqa: E402
    open_decl_for_ratification,
)
from ztare.leanmill.solver.closed_artifact import (  # noqa: E402
    closure_toolchain_identity,
)


LEAN_ROOT = REPO / "ztare_proofs"
CERTIFICATE_LEDGER = (
    REPO / "analytics/public/queries/adhoc_closure_certificates.jsonl"
)
PARITY_LEDGER = REPO / "analytics/public/queries/kernel_parity.jsonl"
ARITHMETIC_TARGET = (
    "AxiomPackJacobianCriticalPuiseuxArithmetic."
    "critical_puiseux_arithmetic_terminal_certificate"
)
ARITHMETIC_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "AxiomPackJacobianCriticalPuiseuxArithmetic.lean"
)
ARITHMETIC_RECORD_SHA256 = (
    "6caf168f5d071956f6f0d8a3567296c7984bcae13b3b682afb62381fa8c12699"
)
EXPECTED_ARITHMETIC_RECEIPT_SHA256 = (
    "dc3c205e70124f469a5fd5421873568c0dce822e4b4233fdddc0a3db55e0eeb0"
)
MECHANISM_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "AxiomPackJacobianCriticalPuiseuxMechanism.lean"
)
COEFFICIENT_TARGET = (
    "AxiomPackJacobianCriticalPuiseuxMechanism."
    "fractional_coefficient_forces_nonintegral_multiplicity"
)
COEFFICIENT_RECORD_SHA256 = (
    "a634915d075e94c0428889f33dc07ee73ee96270afd065d7cd2831dbc287dd6c"
)
EXPECTED_COEFFICIENT_RECEIPT_SHA256 = (
    "87382db51f823468f0c46d85d83d5bffdef24b0cf3fa372b6197ce066e63b9fb"
)
TWO_FLOW_INTERVAL_TARGET = (
    "AxiomPackJacobianCriticalPuiseuxMechanism."
    "two_flow_transition_exponent_interval"
)
TWO_FLOW_INTERVAL_RECORD_SHA256 = (
    "fe4c2bc04778c7e8a6b1dec1a64f16b619293ff87dfb224e9981ef121c87384f"
)
EXPECTED_TWO_FLOW_INTERVAL_RECEIPT_SHA256 = (
    "a81b12695b53f9d367404b945e04bf6d378ff07311b1f33e6a7555049fdf648a"
)
GERM_SOURCE = (
    LEAN_ROOT
    / "ZtareProofs"
    / "AxiomPackJacobianCriticalPuiseuxGermArithmetic.lean"
)
GERM_SUPPORT_SPECS = (
    (
        "discriminant_factorization",
        (
            "AxiomPackJacobianCriticalPuiseuxGermArithmetic."
            "discriminant_factorization"
        ),
        "3a53defd2a04afb350284a42f1b546555052016fd4278c22d2892b3967b88a27",
        "3ded1d209f499225a8efbfc7b6ea06cc6c52847f16530f6a89a658f2f1b6bb23",
    ),
    (
        "radical_numerator_simple_zero",
        (
            "AxiomPackJacobianCriticalPuiseuxGermArithmetic."
            "radical_numerator_simple_zero"
        ),
        "80013b6ea38fc8dd4c6065bc8a29b503b583509d5d8123b7f73c36e5d50e3883",
        "4466cbbe4df7e108cb00538752061d43c612a9ff035a8e6c37b44394d04569a7",
    ),
    (
        "radical_denominator_at_branch_nonzero",
        (
            "AxiomPackJacobianCriticalPuiseuxGermArithmetic."
            "radical_denominator_at_branch_nonzero"
        ),
        "200a02cc74d82fc9249d024167647df4b92ff10e18bacfb980c372e787364c1d",
        "7805bfcdc3d7eab508aca839aee6fc157080b2c10c0952af42e9c3ff8ae03a07",
    ),
    (
        "radical_simple_zero_scale_exact",
        (
            "AxiomPackJacobianCriticalPuiseuxGermArithmetic."
            "radical_simple_zero_scale_exact"
        ),
        "35dfc7a5250f950269181742170b3e6e404b7ffc63dede4a93eed64604cbb136",
        "291a64cb3be111b370fe13d3176306e992e2d7bc786ad66f71ebd9b822f4a6b9",
    ),
)
EXPECTED_SINGLE_FLOW_SHA256 = (
    "6c3a97ebae223d4c0dbf6762d1399d242ea951459d3e7ae44255be2575931926"
)
EXPECTED_TWO_FLOW_SHA256 = (
    "190c7ff996246b663dc6ab94435aaea81fa8f8e4c009188badac06ec88bc963c"
)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _semantic_identity(
    *,
    role: str,
    statement: str,
    evidence_sha256s: tuple[str, ...],
) -> str:
    return content_sha256({
        "schema": "axiompack.formal_residual_semantic_proposition.v1",
        "role": role,
        "statement": statement,
        "evidence_sha256s": list(evidence_sha256s),
    })


def _governed_support(
    *,
    source_path: Path,
    target: str,
    record_sha256: str,
    expected_receipt_sha256: str,
) -> tuple[GovernedFormalSupport, GovernedFormalPropositionIdentity]:
    source = source_path.read_text(encoding="utf-8")
    posed, proof = open_decl_for_ratification(source, target)
    signature = normalized_target_signature(source, target)
    arguments: dict[str, Any] = {
        "certificate_ledger": CERTIFICATE_LEDGER,
        "governed_record_sha256": record_sha256,
        "parity_ledger": PARITY_LEDGER,
        "target": target,
        "expected_signature": signature,
        "posed_source": posed,
        "proof_text": proof,
        "goal": signature,
        "lean_root": LEAN_ROOT,
        "expected_provider": "existing_artifact",
    }
    receipt = make_content_bound_evidence_from_governed_ratification(
        **arguments
    )
    assert receipt.receipt_sha256 == expected_receipt_sha256
    support = GovernedFormalSupport(
        receipt=receipt,
        certificate_ledger=CERTIFICATE_LEDGER,
        governed_record_sha256=record_sha256,
        parity_ledger=PARITY_LEDGER,
        target=target,
        expected_signature=signature,
        posed_source=posed,
        proof_text=proof,
        goal=signature,
        lean_root=LEAN_ROOT,
        expected_provider="existing_artifact",
    )
    formal_identity = governed_formal_proposition_identity_from_receipt(
        receipt
    )
    return support, formal_identity


def run(verification_rows: int = 8) -> dict[str, object]:
    """Compile the exact formalization residual of the Puiseux terminal."""

    # Resolve and cache the authority environment before the symbolic replay.
    # The replay is CPU-heavy but cannot mutate the Lean toolchain identity.
    toolchain = closure_toolchain_identity(LEAN_ROOT)
    if toolchain.get("complete") is not True:
        raise RuntimeError("current Lean toolchain identity is incomplete")
    puiseux = puiseux_run(verification_rows)
    single = puiseux["filtered_obstruction_compiler"]
    two_flow = puiseux["filtered_two_flow_obstruction_compiler"]
    single_digest = str(single["puiseux_flow_certificate_sha256"])
    two_flow_digest = str(two_flow["two_flow_puiseux_certificate_sha256"])
    assert single_digest == EXPECTED_SINGLE_FLOW_SHA256
    assert two_flow_digest == EXPECTED_TWO_FLOW_SHA256

    adapter_sha256 = content_sha256(puiseux)
    script_sha256 = _file_sha256(
        JACOBIAN / "gauge_pure_contact_zero_witt_puiseux_obstruction.py"
    )
    arithmetic_support, arithmetic_identity = _governed_support(
        source_path=ARITHMETIC_SOURCE,
        target=ARITHMETIC_TARGET,
        record_sha256=ARITHMETIC_RECORD_SHA256,
        expected_receipt_sha256=EXPECTED_ARITHMETIC_RECEIPT_SHA256,
    )
    coefficient_support, coefficient_identity = _governed_support(
        source_path=MECHANISM_SOURCE,
        target=COEFFICIENT_TARGET,
        record_sha256=COEFFICIENT_RECORD_SHA256,
        expected_receipt_sha256=EXPECTED_COEFFICIENT_RECEIPT_SHA256,
    )
    interval_support, interval_identity = _governed_support(
        source_path=MECHANISM_SOURCE,
        target=TWO_FLOW_INTERVAL_TARGET,
        record_sha256=TWO_FLOW_INTERVAL_RECORD_SHA256,
        expected_receipt_sha256=(
            EXPECTED_TWO_FLOW_INTERVAL_RECEIPT_SHA256
        ),
    )
    germ_support_rows = tuple(
        (
            role,
            *_governed_support(
                source_path=GERM_SOURCE,
                target=target,
                record_sha256=record_sha256,
                expected_receipt_sha256=receipt_sha256,
            ),
        )
        for role, target, record_sha256, receipt_sha256 in GERM_SUPPORT_SPECS
    )
    germ_identities = {
        role: identity
        for role, _support, identity in germ_support_rows
    }
    selected_germ = _semantic_identity(
        role="selected_algebraic_germ_expansion",
        statement=(
            "On the selected branch u=x+2 at x=-2, the inverse radial "
            "holonomy has nonzero regular coefficient and first nonintegral "
            "term (1120*sqrt(6)/34347)*u^(5/2)."
        ),
        evidence_sha256s=(adapter_sha256, script_sha256),
    )
    selected_germ_series = _semantic_identity(
        role="selected_algebraic_germ_series_passage",
        statement=(
            "The governed discriminant and radical scales, on the selected "
            "square-root branch, pass through the exact radial logarithmic "
            "derivative and integration to a nonzero endpoint u^(5/2) term."
        ),
        evidence_sha256s=(adapter_sha256, script_sha256),
    )
    selected_germ_inference = _semantic_identity(
        role="selected_algebraic_germ_inference",
        statement=(
            "The exact discriminant factor, radical simple zero, denominator "
            "nonvanishing, quotient scale, and selected series passage imply "
            "the declared critical algebraic-germ expansion."
        ),
        evidence_sha256s=(adapter_sha256, script_sha256),
    )
    julia_identity = _semantic_identity(
        role="julia_formal_flow_identity",
        statement=(
            "Every polynomial autonomous generator whose time-one germ is "
            "the selected holonomy satisfies f(F)=F'*f as an all-order "
            "formal-germ identity."
        ),
        evidence_sha256s=(
            adapter_sha256,
            str(single["proof_contract_sha256"]),
        ),
    )
    two_flow_structural = _semantic_identity(
        role="degree_independent_two_flow_structural_alternative",
        statement=(
            "Every factorization by two polynomial autonomous flows tangent "
            "to the identity is analytic on the finite route, reaches equal "
            "degrees on the through-infinity route, or reduces to one "
            "polynomial flow in the proportional case."
        ),
        evidence_sha256s=(
            adapter_sha256,
            str(two_flow["proof_contract_sha256"]),
        ),
    )
    single_flow_statement = _semantic_identity(
        role="single_polynomial_flow_obstruction",
        statement=(
            "The selected critical inverse radial holonomy is not the "
            "time-one germ of a polynomial autonomous generator."
        ),
        evidence_sha256s=(single_digest,),
    )
    single_flow_inference = _semantic_identity(
        role="single_polynomial_flow_inference",
        statement=(
            "The selected germ, nonzero coefficient arithmetic, universal "
            "coefficient cancellation, and Julia identity exclude one "
            "polynomial autonomous generator."
        ),
        evidence_sha256s=(single_digest,),
    )
    root_statement = _semantic_identity(
        role="critical_two_sided_puiseux_terminal",
        statement=(
            "The selected critical inverse radial holonomy is neither one "
            "polynomial autonomous flow nor a composition of two polynomial "
            "autonomous flows tangent to the identity."
        ),
        evidence_sha256s=(single_digest, two_flow_digest),
    )
    terminal_inference = _semantic_identity(
        role="critical_puiseux_terminal_inference",
        statement=(
            "The selected germ expansion, nonzero-coefficient arithmetic, "
            "Julia identity, and exhaustive two-flow alternative imply the "
            "critical two-sided terminal exclusion."
        ),
        evidence_sha256s=(single_digest, two_flow_digest),
    )
    semantic = FormalPropositionIdentityKind.ADAPTER_SEMANTIC
    lean = FormalPropositionIdentityKind.LEAN_TARGET_SIGNATURE
    decomposition = make_formal_claim_decomposition(
        name="axiompack-jacobian-critical-puiseux-terminal",
        root_node_id="critical_terminal_excluded",
        nodes=(
            FormalClaimNode(
                node_id="critical_terminal_excluded",
                proposition_sha256=root_statement,
                identity_kind=semantic,
                children=(
                    "selected_algebraic_germ_expansion",
                    "single_polynomial_flow_obstruction",
                    "two_flow_structural_alternative",
                    "two_flow_exponent_interval",
                ),
                inference_proposition_sha256=terminal_inference,
                inference_identity_kind=semantic,
            ),
            FormalClaimNode(
                node_id="selected_algebraic_germ_expansion",
                proposition_sha256=selected_germ,
                identity_kind=semantic,
                children=(
                    "discriminant_factorization",
                    "radical_numerator_simple_zero",
                    "radical_denominator_at_branch_nonzero",
                    "radical_simple_zero_scale_exact",
                    "selected_algebraic_germ_series_passage",
                ),
                inference_proposition_sha256=selected_germ_inference,
                inference_identity_kind=semantic,
            ),
            *tuple(
                FormalClaimNode(
                    node_id=role,
                    proposition_sha256=identity.identity_sha256,
                    identity_kind=lean,
                    lean_identity=identity,
                )
                for role, identity in sorted(germ_identities.items())
            ),
            FormalClaimNode(
                node_id="selected_algebraic_germ_series_passage",
                proposition_sha256=selected_germ_series,
                identity_kind=semantic,
            ),
            FormalClaimNode(
                node_id="critical_arithmetic",
                proposition_sha256=arithmetic_identity.identity_sha256,
                identity_kind=lean,
                lean_identity=arithmetic_identity,
            ),
            FormalClaimNode(
                node_id="coefficient_cancellation_mechanism",
                proposition_sha256=coefficient_identity.identity_sha256,
                identity_kind=lean,
                lean_identity=coefficient_identity,
            ),
            FormalClaimNode(
                node_id="julia_formal_flow_identity",
                proposition_sha256=julia_identity,
                identity_kind=semantic,
            ),
            FormalClaimNode(
                node_id="single_polynomial_flow_obstruction",
                proposition_sha256=single_flow_statement,
                identity_kind=semantic,
                children=(
                    "selected_algebraic_germ_expansion",
                    "critical_arithmetic",
                    "coefficient_cancellation_mechanism",
                    "julia_formal_flow_identity",
                ),
                inference_proposition_sha256=single_flow_inference,
                inference_identity_kind=semantic,
            ),
            FormalClaimNode(
                node_id="two_flow_structural_alternative",
                proposition_sha256=two_flow_structural,
                identity_kind=semantic,
            ),
            FormalClaimNode(
                node_id="two_flow_exponent_interval",
                proposition_sha256=interval_identity.identity_sha256,
                identity_kind=lean,
                lean_identity=interval_identity,
            ),
        ),
        adapter_evidence_sha256=adapter_sha256,
    )
    problem = FormalClaimCoverageProblem(
        decomposition=decomposition,
        supports=(
            arithmetic_support,
            coefficient_support,
            interval_support,
            *(support for _role, support, _identity in germ_support_rows),
        ),
    )
    coverage = compile_formal_claim_coverage(problem)
    assert replay_formal_claim_coverage_certificate(coverage, problem) == (
        coverage
    )
    assert coverage.directly_ratified_node_ids == (
        "coefficient_cancellation_mechanism",
        "critical_arithmetic",
        "discriminant_factorization",
        "radical_denominator_at_branch_nonzero",
        "radical_numerator_simple_zero",
        "radical_simple_zero_scale_exact",
        "two_flow_exponent_interval",
    )
    assert coverage.uncovered_adapter_semantic_leaf_ids == (
        "julia_formal_flow_identity",
        "selected_algebraic_germ_series_passage",
        "two_flow_structural_alternative",
    )
    assert coverage.uncovered_adapter_semantic_inference_ids == (
        "critical_terminal_excluded",
        "selected_algebraic_germ_expansion",
        "single_polynomial_flow_obstruction",
    )
    assert coverage.root_authority_promotion_eligible is False
    assert coverage.formal_authority_issued is False

    core: dict[str, object] = {
        "schema": "axiompack.jacobian_critical_puiseux_formal_coverage.v1",
        "existing_semantic_digests": {
            "single_flow": single_digest,
            "two_flow": two_flow_digest,
        },
        "governed_formal_supports": [
            {
                "role": role,
                "target": support.target,
                "record_sha256": support.governed_record_sha256,
                "receipt_sha256": support.receipt.receipt_sha256,
                "target_signature_sha256": (
                    identity.target_signature_sha256
                ),
                "formal_proposition_identity_sha256": (
                    identity.identity_sha256
                ),
            }
            for role, support, identity in (
                (
                    "critical_arithmetic",
                    arithmetic_support,
                    arithmetic_identity,
                ),
                (
                    "coefficient_cancellation_mechanism",
                    coefficient_support,
                    coefficient_identity,
                ),
                (
                    "two_flow_exponent_interval",
                    interval_support,
                    interval_identity,
                ),
                *germ_support_rows,
            )
        ],
        "decomposition": decomposition.to_dict(),
        "coverage": coverage.to_dict(),
        "finite_julia_check_is_formal_leaf": False,
        "enclosing_authority_upgraded": False,
        "claim_boundary": (
            "Seven arithmetic/mechanism leaves have governed formal support. "
            "The selected square-root-series passage, all-order Julia identity, "
            "structural two-flow alternative, three composition inferences, "
            "and direct terminal theorem remain explicit formalization "
            "obligations."
        ),
    }
    return {
        **core,
        "formal_coverage_envelope_sha256": content_sha256(core),
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
